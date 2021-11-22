from threading import Thread, Event
from glob import glob
import os
import time

from utility.setting import setting


CAMERA_COUNT = len(setting.get_working_camera_ids())
STREAM_PATH = str(setting.get_stream_path()).replace('Q:\\', 'D:\\storage\\')


class JPEGTrimmer(Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = Event()

        self.start()

    def _trim_jpg(self):
        for i in range(CAMERA_COUNT):
            jpg_file_list = glob(f'{STREAM_PATH}\\{i + 1}\\jpg\\*.jpg')
            jpg_to_delete = len(jpg_file_list) - 3000
            if jpg_to_delete <= 0:
                continue

            for jpg_file in jpg_file_list:
                os.remove(jpg_file)
                jpg_to_delete -= 1
                if jpg_to_delete <= 0:
                    break

    def run(self):
        while not self.is_stop():
            self._trim_jpg()
            time.sleep(5)

    def stop(self):
        self._stop_event.set()

    def is_stop(self):
        return self._stop_event.is_set()