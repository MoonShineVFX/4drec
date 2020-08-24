import numpy as np
import struct
import io
import os

from utility.logger import log
from utility.setting import setting

from .image import CameraImage


class CameraShotFileCore():
    """shot 檔案管理核心

    shot 檔案會有一個圖像檔案 4dr 跟一個資訊檔案 4dm
    4dr 是所有圖像連續寫入的檔案
    4dm 會記錄每一個影格在 4dr 的位置
    4dm 的影格格式是: (圖像大小, 寬, 高)

    Args:
        shot_file_path: shot 檔案位置
        file_handle: 檔案開啟方式

    """

    binary_format = '>IIII'
    binary_size = struct.calcsize(binary_format)
    image_ext = '.4dr'
    meta_ext = '.4dm'

    def __init__(self, shot_file_path, file_handle):
        self._shot_file_path = shot_file_path

        # 圖像 file object
        self._image_file = open(
            self._shot_file_path + self.image_ext, file_handle, buffering=0
        )

        # 影格資訊 file object
        self._meta_file = open(
            self._shot_file_path + self.meta_ext, file_handle, buffering=0
        )

    def close(self):
        """關閉檔案"""
        self._close()
        self._image_file.close()
        self._meta_file.close()

    def _close(self):
        pass

    def get_path(self):
        """取得 shot 檔案位置"""
        return self._shot_file_path


class CameraShotFileLoader(CameraShotFileCore):
    """ shot 檔案讀取器

    根據影格資訊讀取圖像
    初始化時會先將資訊全部讀出來整理到 self._frames
    之後再用 load 去讀取圖像

    Args:
        shot_file_path: shot 檔案位置

    """

    def __init__(self, shot_file_path, log):
        super().__init__(shot_file_path, 'rb')
        self._log = log
        self._log.info(f'File read: {self._shot_file_path}')
        self._frames = {}  # {影格號碼: (圖像在檔案的位置, 圖像大小, 寬, 高)}

        # 先取得資訊
        self._load_metadata()

    def _load_metadata(self):
        """讀取影格資訊檔案整理出所有影格資訊"""
        file_cursor = 0

        while True:
            # 讀取特定 size
            raw_meta = self._meta_file.read(self.binary_size)

            # 如果讀取的長度錯誤的話即中斷，可能是檔案儲存到一半
            if len(raw_meta) < self.binary_size:
                break

            # 取得資訊，file_cursor 就是檔案游標位置，不斷增加
            frame, image_size, w, h = struct.unpack(
                self.binary_format,
                raw_meta
            )
            self._frames[frame] = (file_cursor, image_size, w, h)
            file_cursor += image_size

        frames = list(self._frames.keys())
        self._log.info('{} frames loaded ({}/{})'.format(
            len(self._frames),
            frames[0],
            frames[-1]
        ))

    def load(self, frame):
        """讀取圖像

        讀取特定影格的圖像，回傳 CameraImage
        讀取方式是藉由影格資訊去找到該區段在檔案的位置
        只讀該片段轉成假 file 檔去讀出來

        Args:
            frame: 想讀取的影格數

        """
        if frame not in self._frames:
            self._log.error(
                f"Can't find frame {frame} in {self._shot_file_path}"
            )
            return None

        # 取得資訊
        file_cursor, image_size, w, h = self._frames[frame]

        # 讀取片段
        self._image_file.seek(file_cursor)
        image_bytes = self._image_file.read(image_size)
        f = io.BytesIO(image_bytes)

        # 讀取圖像
        data = np.load(f, allow_pickle=False, fix_imports=False)

        return CameraImage(data, w, h)


class CameraShotFileDumper(CameraShotFileCore):
    """ shot 檔案寫入器

    將檔案寫入到硬碟，並同時產生影格資訊檔
    另外會記錄寫入的編號，在結束寫入時產生報告，以查看有沒有遺失的影格

    Args:
        shot_file_path: shot 檔案位置

    """

    def __init__(self, shot_file_path, log):
        super().__init__(shot_file_path, 'wb')
        self._log = log
        self._log.info(f'File write: {self._shot_file_path}')
        self._frames = []  # 寫入的影格編號陣列

    def dump(self, frame, camera_image):
        """寫入

        將圖像寫入到硬碟

        Args:
            frame: 影格編號
            camera_image: CameraImage

        """
        # 藉由 tell() 去算出檔案大小
        start_cursor = self._image_file.tell()
        camera_image.write(self._image_file)
        image_size = self._image_file.tell() - start_cursor

        # 包裝 binary
        meta = struct.pack(
            self.binary_format, frame, image_size, *camera_image.get_size()
        )
        self._meta_file.write(meta)

        # 加入影格
        self._frames.append(frame)

    def _close(self):
        """關閉時的運行，做一個 log 回報"""
        self._log.info('File saved with {} frames ({}/{}): {}'.format(
            len(self._frames),
            self._frames[0],
            self._frames[-1],
            self._shot_file_path
        ))

    def get_frames(self):
        """取得寫入的影格編號陣列"""
        return self._frames

    def get_report(self):
        """取得寫入報告"""
        # 算出遺失格數
        all_frames = [f for f in range(self._frames[0], self._frames[-1])]
        missing_frames = list(i for i in all_frames if i not in self._frames)

        return {
            'missing_frames': missing_frames,
            'frame_range': (self._frames[0], self._frames[-1]),
            'size': self._image_file.tell()
        }


class CameraShotMeta():
    """shot 資訊

    Args:
        parms: {camera_id, shot_id, frame, quality, scale_length}
        get_shot_file_path: connector 的取得路徑函式

    """

    def __init__(self, parms, get_shot_file_path):
        self._parms = parms  # 參數儲存
        # shot 檔案路徑
        self._shot_file_path = get_shot_file_path(self._parms['shot_id'])

    def __getattr__(self, prop):
        return self._parms[prop]

    def get_path(self):
        """取得 shot 檔案路徑"""
        return self._shot_file_path

    def get_parms(self):
        """返回所有 parms 參數"""
        return self._parms
