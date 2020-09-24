from queue import Queue
import threading
import cv2
import numpy as np
import lz4framed
from PyQt5.Qt import QPixmap, QImage

from utility.setting import setting
from utility.message import message_manager
from common.jpeg_coder import jpeg_coder
from utility.define import (
    UIEventType, MessageType, CameraLibraryTask, CameraCacheType
)
from utility.delay_executor import DelayExecutor

from master.streaming import server
from master.ui import ui
from master.projects import project_manager


class CameraLibrary(threading.Thread):
    """相機快取圖庫

    當 slave 傳圖片過來時，會在這邊轉成 UI 可用的 pixmap
    如果不是相機預覽，會將圖片存到 self._cache 建立快取來加速播放
    圖片因為有不同的參數，存放方式以參數產生獨立的 key 來識別
    同時也處理圖片請求，如果 self._cache 沒有的圖也會向 slave 索取

    """

    def __init__(self):
        super().__init__()
        self._queue = Queue()  # 圖片佇列
        self._cache = {}  # 快取
        self._delay = DelayExecutor()
        self._encoder = CameraPixmapEncoder(self)

        # 初始化即自動執行
        self.start()

    def run(self):
        while True:
            task_type, payload = self._queue.get()

            if task_type is CameraLibraryTask.IMPORT:
                self._import_pixmap(payload)
            elif task_type is CameraLibraryTask.REQUEST:
                target_pixmap = self._get_pixmap_from_cache(payload)

                # 看快取裡面是否已經有，有的話直接傳給 UI
                if target_pixmap:
                    self.send_ui(target_pixmap)
                # 沒有的話，向 slave 發送請求
                elif payload.is_delay():
                    self._delay.execute(lambda: self._slave_request(payload))
                else:
                    self._slave_request(payload)

    def _get_pixmap_from_cache(self, camera_pixmap):
        try:
            pixmap = (
                self._cache[camera_pixmap.shot_id]
                [camera_pixmap.get_cache_type()]
                [camera_pixmap.frame]
            )
            return pixmap
        except KeyError:
            return None

    def _import_pixmap(self, camera_pixmap):
        """將 camera_pixmap 存進快取

        Args:
            camera_pixmap: CameraPixmap

        """
        if camera_pixmap.shot_id not in self._cache:
            self._cache[camera_pixmap.shot_id] = {
                CameraCacheType.ORIGINAL: {},
                CameraCacheType.THUMBNAIL: {}
            }

        target_cache = (
            self._cache[camera_pixmap.shot_id]
            [camera_pixmap.get_cache_type()]
        )

        if camera_pixmap.frame in target_cache:
            if target_cache[camera_pixmap.frame] is not None:
                return

        target_cache[camera_pixmap.frame] = camera_pixmap
        camera_pixmap.save_cache()

        shot = project_manager.get_shot(camera_pixmap.shot_id)
        shot.update_cache_progress(camera_pixmap)

    def _slave_request(self, camera_pixmap):
        """向 slave 索取指定圖像

        藉由 camera_pixmap 的資料去向 slave 索取圖像

        Args:
            camera_pixmap: CameraPixmap

        """
        message_manager.send_message(
            MessageType.GET_SHOT_IMAGE,
            camera_pixmap.get_parms()
        )

    def add_task(self, task_type, payload):
        self._queue.put((task_type, payload))

    def send_ui(self, camera_pixmap, save=False):
        """將 camera_pixmap 傳送給 UI

        Args:
            camera_pixmap: CameraPixmap

        """
        if camera_pixmap.is_state():
            ui.dispatch_event(
                UIEventType.CAMERA_STATE,
                camera_pixmap.to_state()
            )
        else:
            ui.dispatch_event(
                UIEventType.CAMERA_PIXMAP,
                camera_pixmap.to_payload(
                    ui.get_state('Focus'),
                    ui.get_state('caching'),
                    save
                )
            )

            # 如果是 shot 圖像便存起來
            if save and camera_pixmap.is_shot():
                self.add_task(
                    CameraLibraryTask.IMPORT,
                    camera_pixmap
                )

    def on_image_received(self, message, direct=False):
        """收到圖像的回調"""
        if not direct:
            pixmap = CameraPixmap(*message.unpack())
        else:
            pixmap = CameraPixmap(message)
        self._encoder.add_task(pixmap)

    def on_image_requested(
        self, camera_id, shot_id, frame, quality, scale_length, delay
    ):
        """UI 顯示圖像的請求

        收到請求後，會回傳一組該參數的識別 key
        等圖像產生發送 UI 事件後，可以拿 key 去對應需要的容器

        Args:
            camera_id: 相機 ID
            shot_id: shot ID
            frame: 影格
            quality: 轉檔品質
            scale_length: 最長邊長度

        """
        parms = {
            'camera_id': camera_id,
            'shot_id': shot_id,
            'frame': frame,
            'quality': quality,
            'scale_length': scale_length,
            'delay': delay
        }

        camera_pixmap = CameraPixmap(parms)
        self.add_task(CameraLibraryTask.REQUEST, camera_pixmap)


class CameraPixmapEncoder(threading.Thread):
    def __init__(self, library):
        super().__init__()
        self._queue = Queue()
        self._library = library

        # 初始化即自動執行
        self.start()

    def add_task(self, pixmap):
        if pixmap.is_live_view():
            while not self._queue.empty():
                self._queue.get()
        self._queue.put(pixmap)

    def run(self):
        while True:
            pixmap = self._queue.get()

            # 斷線產生 buf 會是 None 的情況不進行轉換
            pixmap.decode()

            # 傳給 UI
            self._library.send_ui(pixmap, save=True)


class CameraPixmap():
    """相機 UI 圖像

    UI 的 Pixmap 包裝，額外增加了 parms 的資訊

    Args:
        parms: 圖像資訊 {camera_id, shot_id, frame, quality, scale_length}

    """

    _ow = setting.camera_resolution[0]
    _oh = setting.camera_resolution[1]
    _kernel = np.ones((5, 5), np.uint8)

    def __init__(self, parms, buf=None, pixmap=None):
        self._buf = buf
        self._pixmap = pixmap  # QPixmap
        self._parms = parms  # 圖像資訊
        self._cache = None

    def __getattr__(self, prop):
        if prop in self._parms:
            return self._parms[prop]
        else:
            raise KeyError(f'No {prop} in parms')

    def is_wait_cache(self):
        return self._wait_cache

    def is_delay(self):
        return 'delay' in self._parms and self._parms['delay']

    def is_live_view(self):
        """是否是即時預覽的圖像"""
        return 'shot_id' not in self._parms

    def is_shot(self):
        return 'shot_id' in self._parms

    def is_original(self):
        return (
            'scale_length' in self._parms and
            self._parms['scale_length'] is None
        )

    def is_converted(self):
        return self._pixmap is not None

    def is_cache(self):
        return self._cache is not None

    def is_state(self):
        return 'state' in self._parms

    def to_payload(self, focus, caching, save):
        pixmap = self.convert_to_pixmap(focus, save) if not caching else None
        return (
            self._parms['camera_id'],
            pixmap,
            self.is_live_view()
        )

    def to_state(self):
        return (self._parms['camera_id'], self._parms['state'])

    def get_cache_type(self):
        if self.is_original():
            return CameraCacheType.ORIGINAL
        else:
            return CameraCacheType.THUMBNAIL

    def get_parms(self):
        """取得圖像參數"""
        return self._parms

    def get_size(self):
        if self._cache is None:
            return 0

        return len(self._cache)

    def get_buf(self):
        return self._buf

    def get(self):
        """取得 QPixmap"""
        return self._pixmap

    def decode(self):
        if self._buf is None:
            return

        # 解碼 JPEG 成 cv2 跟正確顏色
        im = jpeg_coder.decode(self._buf)
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        self._buf = im
        self._shape = self._buf.shape
        self._type = self._buf.dtype

    def save_cache(self):
        if self._buf is None:
            return
        self._cache = lz4framed.compress(self._buf)
        self._buf = None

    def convert_to_pixmap(self, focus=False, save=False):
        """做一系列圖像轉換至 pixmap

        二進制JPEG > cv2 > QImage > QPixmap

        """
        if self._buf is None:
            if not self.is_cache():
                return None
            buf = lz4framed.decompress(self._cache)
            buf = np.frombuffer(buf, self._type)
            buf.shape = self._shape
        else:
            buf = np.copy(self._buf)

        _height, _width, _ = buf.shape

        if (
            self.is_live_view() and
            _width == self._ow
        ):
            if focus:
                sim = cv2.resize(buf, (int(_width / 2), int(_height / 2)))
                edges = cv2.Canny(sim, 280, 380)
                edges = cv2.dilate(edges, self._kernel)
                edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                edges *= np.array((1, 0, 0), np.uint8)
                edges = cv2.resize(edges, (_width, _height))
                buf = np.bitwise_or(buf, edges)
            tm = cv2.resize(buf, (int(_width / 2), int(_height / 2)))
            tm = cv2.cvtColor(tm, cv2.COLOR_RGB2BGR)
            server.set_buffer(tm)

        # 轉成 QImage
        q_image = QImage(
            buf.data,
            _width,
            _height,
            3 * _width,
            QImage.Format_RGB888
        )

        # 轉成 QPixmap
        if not save:
            self._buf = None
        return QPixmap.fromImage(q_image)
