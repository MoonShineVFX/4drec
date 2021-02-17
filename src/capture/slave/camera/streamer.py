import queue
import numpy as np
import cv2
from vidgear.gears import StreamGear
from pathlib import Path

from utility.mix_thread import MixThread
from utility.setting import setting


class CameraStreamer(MixThread):
    _WIDTH = setting.camera_resolution[0]
    _HEIGHT = setting.camera_resolution[1]
    _PARAMS = {
        '-input_framerate': 30,
        '-vcodec': 'libx264', # h264_nvenc
        'custom_ffmpeg': 'Q:\\app\\ffmpeg'
    }
    _STREAM_ROOT_PATH = 'Q:/stream_test'

    def __init__(self, camera_id):
        super().__init__()
        self._queue = queue.Queue()

        stream_path = Path(self._STREAM_ROOT_PATH) / camera_id
        stream_path.mkdir(parents=True, exist_ok=True)

        self._streamer = StreamGear(
            output=str(stream_path / 'main.mpd'),
            **self._PARAMS
        )

        self.start()

    def _run(self):
        while True:
            image_buffer = self._queue.get()

            if image_buffer is None:
                break

            im = np.frombuffer(image_buffer, dtype=np.uint8)
            im = im.reshape((self._HEIGHT, self._WIDTH))
            im = cv2.cvtColor(im, cv2.COLOR_BAYER_RG2RGB)
            im = cv2.rotate(im, cv2.ROTATE_180)

            self._streamer.stream(im)

        self._streamer.terminate()

    def stop(self):
        self.add_buffer(None)

    def add_buffer(self, image_buffer):
        self._queue.put(image_buffer)
