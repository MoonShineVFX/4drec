from threading import Condition
import queue
import os

from utility.setting import setting
from utility.message import message_manager
from utility.mix_thread import MixThread
from utility.define import MessageType

from .shot import CameraShotFileLoader


class CameraLiveViewer(MixThread):
    """相機即時預覽編碼器

    等待 self._buffer 佇列，一有緩衝便將其轉碼送出

    Args:
        camera_id: 所屬的 Camera ID

    """

    def __init__(self, camera_id):
        super().__init__()
        self._camera_id = camera_id  # 相機序號
        self._encode_parms = {
            'quality': setting.jpeg.live_view.quality,
            'scale_length': setting.jpeg.live_view.scale_length
        }  # 預設編碼設定
        self._buffer = None  # 緩衝佇列
        self._cond = Condition()  # 緩衝鎖，以防衝突

        # 初始化即自動執行
        self.start()

    def _run(self):
        while self._running:
            camera_image = self._get_buffer()

            if camera_image is None:
                break

            encoded_data = camera_image.convert_jpeg(
                **self._encode_parms
            )

            message_manager.send_message(
                MessageType.LIVE_VIEW_IMAGE,
                {'camera_id': self._camera_id},
                encoded_data
            )

    def apply_encode_parms(self, parms):
        """編碼設定

        Args:
            parms: {
                quality: JPEG品質
                scale_length: 最長邊長度
            }

        """
        self._encode_parms.update(parms)

    def set_buffer(self, camera_image):
        """設定圖像緩衝

        緩衝永遠只有一張，新的會取代舊的

        Args:
            camera_image: CameraImage

        """
        self._cond.acquire()
        self._buffer = camera_image
        self._cond.notify()
        self._cond.release()

    def _get_buffer(self):
        """取得即時預覽佇列的圖像

        當佇列為空時，會持續等待到有圖像，拿取後將佇列清空

        """
        self._cond.acquire()
        if self._buffer is None:
            self._cond.wait()

        camera_image = self._buffer
        self._buffer = None

        self._cond.release()
        return camera_image

    def _after_stop(self):
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        self.join()


class CameraShotLoader(MixThread):
    """Shot 讀取器

    監控 self._queue 去讀取特定的圖像
    會看要讀取的圖像資訊去切換 self._file 的 CameraShotFileLoader

    """

    def __init__(self, log):
        super().__init__()
        self._log = log
        self._file = None  # CameraShotFileLoader
        self._queue = queue.Queue()  # 任務佇列

        self.start()

    def _run(self):
        while self._running:
            shot_meta = self._queue.get()

            if shot_meta is None:
                break

            shot_path = shot_meta.get_path()
            if shot_path is None:
                continue

            # 如果 self._file 是空的或者不是所需的檔案路徑，取代掉
            if not (
                self._file is not None and
                self._file.get_path() == shot_path
            ):
                if isinstance(self._file, CameraShotFileLoader):
                    self._file.close()
                self._file = CameraShotFileLoader(shot_path, self._log)

            camera_image = self._file.load(shot_meta.frame)
            if camera_image is None:
                continue

            message_manager.send_message(
                MessageType.SHOT_IMAGE,
                shot_meta.get_parms(),
                camera_image.convert_jpeg(
                    shot_meta.quality,
                    shot_meta.scale_length
                )
            )

    def add_task(self, shot_meta):
        """將讀取圖像資訊放到佇列

        Args:
            shot_meta: CameraShotMeta 物件

        """
        self._queue.put(shot_meta)

    def on_shot_will_remove(self, remove_shot_file_path):
        """當有 Shot 刪除時

        檢查要刪除的 Shot 自己的 self._file 是否開啟
        如果有開啟就關閉以便刪除

        """
        if (
            self._file is not None and
            self._file.get_path() == remove_shot_file_path
        ):
            self._file.close()
            self._file = None

    def _after_stop(self):
        self.add_task(None)
        self.join()


class CameraShotSubmitter(MixThread):
    """Shot 發佈器

    監控 self._queue 去讀取特定的 Shot
    將 Shot 轉換出需要範圍的圖像並發佈到解算伺服器

    """

    def __init__(self, log):
        super().__init__()
        self._queue = queue.Queue()  # 任務佇列
        self._log = log

        # 自動執行
        self.start()

    def _run(self):
        while self._running:
            shot_id, job_name, frames, shot_file_paths = self._queue.get()

            if shot_id is None:
                break

            self._log.info(
                'Submit shot: '
                f'{shot_id} ({frames[0]}-{frames[-1]} [{len(frames)}])'
            )

            # 創建資料夾
            submit_image_path = f'{setting.submit_shot_path}{shot_id}/'
            os.makedirs(submit_image_path, exist_ok=True)
            self._log.debug(f'Save to {submit_image_path}')

            # 取出圖像
            for camera_id, shot_file_path in shot_file_paths.items():
                file_loader = CameraShotFileLoader(shot_file_path)

                # 進度定義
                current_count = 0
                total_count = len(frames)

                for frame in frames:
                    camera_image = file_loader.load(frame)

                    if camera_image is not None:
                        image_path = (
                            f'{submit_image_path}{camera_id}_{frame:06d}.jpg'
                        )

                        # 檢查是否有存在的檔案並大小差不多
                        is_exist = False
                        if os.path.isfile(image_path):
                            exist_size = os.stat(image_path).st_size

                            # 大小超過閥值，略過
                            if exist_size > setting.bypass_exist_size:
                                is_exist = True

                        # 轉檔與儲存
                        if not is_exist:
                            jpg_data = camera_image.convert_jpeg(
                                setting.jpeg.submit.quality
                            )
                            with open(image_path, 'wb') as f:
                                f.write(jpg_data)

                    else:
                        self._log.error(f'{camera_id} missing frame {frame}')

                    # 進度整理
                    current_count += 1

                    # 傳送進度報告
                    message_manager.send_message(
                        MessageType.SUBMIT_REPORT,
                        {
                            'camera_id': camera_id,
                            'shot_id': shot_id,
                            'job_name': job_name,
                            'progress': (current_count, total_count)
                        }
                    )

    def add_task(self, task):
        """將要發佈的 Shot 資訊放到佇列

        Args:
            task: (shot_id, frame_range, shot_file_paths)

        """
        self._queue.put(task)

    def _after_stop(self):
        self.add_task((None, None, None))
        self.join()
