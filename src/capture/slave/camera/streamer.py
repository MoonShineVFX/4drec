import queue
import numpy as np
import cv2
import shutil
import subprocess

from utility.mix_thread import MixThread
from utility.setting import setting


class CameraStreamer(MixThread):
    def __init__(self, camera_id):
        super().__init__()
        self._queue = queue.Queue()

        self._stream_path = setting.get_stream_path(camera_id)
        if self._stream_path.exists():
            try:
                shutil.rmtree(str(self._stream_path))
            except Exception as e:
                print(e)
        self._stream_path.mkdir(parents=True, exist_ok=True)
        self._process_list = []

        self._initial_ffmpeg()

        self.start()

    def _initial_ffmpeg(self):
        command_input = [
            setting.get_ffmpeg_exe(),
            '-hide_banner', '-loglevel', 'error',
            '-y',
            '-f', 'rawvideo',
            '-s', setting.get_resolution(cmd_arg=True),
            '-pix_fmt', 'bgr24',
            '-r', str(setting.frame_rate),
            '-i', '-',
            '-an',
        ]
        cwd_path = str(self._stream_path)

        for set_name, scale_width in setting.get_dash_sets().items():
            (self._stream_path / set_name).mkdir(parents=True, exist_ok=True)
            command_output = setting.get_dash_params(set_name, scale_width)
            self._process_list.append(subprocess.Popen(
                command_input + command_output,
                stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=cwd_path
            ))

        if setting.is_include_jpg():
            set_name = 'jpg'
            (self._stream_path / set_name).mkdir(parents=True, exist_ok=True)
            command_output = setting.get_jpg_params(set_name)
            self._process_list.append(
                subprocess.Popen(
                    command_input + command_output,
                    stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    cwd=cwd_path
                )
            )

    def _run(self):
        while True:
            image_buffer = self._queue.get()

            if image_buffer is None:
                break

            im = np.frombuffer(image_buffer, dtype=np.uint8)
            im = im.reshape(setting.get_resolution())
            im = cv2.cvtColor(im, cv2.COLOR_BAYER_RG2RGB)
            im = cv2.rotate(im, cv2.ROTATE_180)

            for process in self._process_list:
                process.stdin.buffer.write(im.tobytes())

        for process in self._process_list:
            process.stdin.close()
            process.wait()

        del self

    def stop(self):
        while not self._queue.empty():
            self._queue.get()
        self.add_buffer(None)

    def add_buffer(self, image_buffer):
        self._queue.put(image_buffer)
