import queue

from utility.mix_thread import MixThread
from utility.message import message_manager
from utility.define import MessageType

from .shot import CameraShotFileDumper


class CameraRecorder(MixThread):
    """相機錄製器

    根據 shot 資訊建立 CameraShotFileDumper
    並監控 self._queue 將圖像給 CameraShotFileDumper
    錄製結束時會回傳錄製報告

    Args:
        shot_meta: Shot 資訊

    """

    def __init__(self, shot_meta, log):
        super().__init__()
        self._log = log
        self._shot_meta = shot_meta  # Shot 資訊
        self._queue = queue.Queue()  # 任務佇列
        self._file = None  # 將資料給 thread 做
        self._count = 0

        self.start()

    def _run(self):
        # 負責錄製檔案寫入
        self._file = CameraShotFileDumper(self._shot_meta.get_path(), self._log)

        while True:
            frame, camera_image = self._queue.get()

            # 偵測是否是終止事件 (None, None)
            if camera_image is None:
                self._stop_record()
                break

            self._file.dump(frame, camera_image)

    def _stop(self):
        """停止錄製，利用餵 None tuple 的方式終止運作"""
        self.add_task(None, None)

    def _stop_record(self):
        """停止運作，將錄製做收尾，並整理錄製報告傳給 master"""
        report = self._file.get_report()
        self._file.close()

        report.update({
            'camera_id': self._shot_meta.camera_id,
            'shot_id': self._shot_meta.shot_id
        })

        message_manager.send_message(
            MessageType.RECORD_REPORT,
            report
        )

    def get_record_frames(self):
        """取得錄製的影格陣列"""
        if self._file:
            return self._file.get_frames()
        else:
            return []

    def add_task(self, current_frame, camera_image):
        """將圖像放入錄製佇列

        將圖像放到錄製佇列給 recorder 寫入到硬碟

        Args:
            current_frame: 目前擷取的格數
            camera_image: CameraImage

        """
        if self._shot_meta.is_cali:
            current_frame = 0
            if self._count >= 1 and camera_image is not None:
                return
        self._queue.put((current_frame, camera_image))
        self._count += 1
