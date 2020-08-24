import sys
import os
import lz4framed
import threading
from queue import Queue
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import struct

from utility.setting import setting
from utility.define import UIEventType
from utility.delay_executor import DelayExecutor
from utility.jpeg_coder import jpeg_coder

from master.ui import ui
from master.projects import project_manager


def build_camera_pos_list():
    with open('source/ui/camera.json') as f:
        clist = json.load(f)
    return np.array(clist, np.float32)


class ResolveManager(threading.Thread):
    def __init__(self):
        super().__init__()

        self._queue = Queue()
        self._cache = {}
        self._delay = DelayExecutor()
        self._multi_executor = MultiExecutor(self)

        # 綁定 UI
        ui.dispatch_event(
            UIEventType.UI_CONNECT,
            {
                'resolve': self
            }
        )

        self.start()

    def run(self):
        while True:
            package = self._queue.get()
            self._handle_package(package)

    def _handle_package(self, package):
        size = package.load()
        if size is None:
            self._send_ui(None)
            return

        job_id, frame = package.get_meta()
        if job_id not in self._cache:
            self._cache[job_id] = {}

        self._cache[job_id][frame] = package

        if frame is not None:
            job = project_manager.get_job(job_id)
            job.update_cache_progress(frame, size)

        self._send_ui(package)

    def _send_ui(self, package):
        if package is None:
            payload = None
        else:
            payload = package.to_payload()
        ui.dispatch_event(
            UIEventType.RESOLVE_GEOMETRY,
            payload
        )

    def _add_task(self, package):
        self._queue.put(package)

    def cache_whole_job(self):
        job = project_manager.current_job
        self._multi_executor.add_task(job)

    def request_geometry(
        self, job, frame, is_direct=False, is_delay=True
    ):
        job_id = job.get_id()
        cali_id = job.get_cali_id()

        if job_id in self._cache and frame in self._cache[job_id]:
            self._send_ui(self._cache[job_id][frame])
        elif frame is None:
            package = RigPackage(job_id, cali_id)
            self._add_task(package)
        else:
            package = ResolvePackage(job_id, frame)
            if is_direct:
                self._add_task(package)
            elif is_delay:
                self._delay.execute(
                    lambda: self._add_task(package)
                )
            else:
                self._add_task(package)


class MultiExecutor(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self._manager = manager
        self._queue = Queue()
        self.start()

    def run(self):
        while True:
            job = self._queue.get()

            with ThreadPoolExecutor() as executor:
                for f in job.frames:
                    future = executor.submit(
                        lambda: self._manager.request_geometry(
                            job, f, is_direct=True
                        )
                    )
                    future.result()

    def add_task(self, shot):
        self._queue.put(shot)


class ResolvePackage():
    _format = 'II'
    _header_size = struct.calcsize(_format)

    def __init__(self, job_id, frame):
        self._geo_data = None
        self._tex_data = None
        self._job_id = job_id
        self._frame = frame

    def get_meta(self):
        return self._job_id, self._frame

    def load(self):
        # open file
        load_path = (
            f'{setting.submit_job_path}{self._job_id}/export/'
        )

        file_path = f'{load_path}{self._frame:06d}.4dr'
        if not os.path.isfile(file_path):
            return None

        with open(file_path, 'rb') as f:
            data = f.read()

        geo_size, tex_size = struct.unpack(
            self._format, data[:self._header_size]
        )
        seek = self._header_size

        # load geo
        buffer = lz4framed.decompress(data[seek:seek + geo_size])
        arr = np.frombuffer(buffer, dtype=np.float32)
        seek += geo_size
        arr = arr.reshape(-1, 5)

        self._geo_data = [arr[:, :3], arr[:, 3:]]

        # load texture
        self._tex_data = jpeg_coder.decode(data[seek:seek + tex_size])

        return sys.getsizeof(self._geo_data) + sys.getsizeof(self._tex_data)

    def to_payload(self):
        return len(self._geo_data[0]), self._geo_data, self._tex_data


class RigPackage(ResolvePackage):
    _camera_pos_list = build_camera_pos_list()

    def __init__(self, job_id, cali_id):
        super().__init__(job_id, None)
        self._cali_id = cali_id

    def load(self):
        file = (
            f'{setting.submit_cali_path}{self._cali_id}/calibrated.sfm'
        )

        if not os.path.isfile(file):
            return None

        total_camera_pos_list = []

        with open(file) as f:
            sfm_data = json.load(f)

        for pose in sfm_data['poses']:
            transform = pose['pose']['transform']
            m = np.array([float(r) for r in transform['rotation']], np.float32)
            m = m.reshape(3, 3)

            p = np.array([float(c) for c in transform['center']], np.float32)

            this_list = self._camera_pos_list.copy()
            this_list = this_list.dot(m)
            this_list += p

            total_camera_pos_list.append(this_list)

        pos_list = np.concatenate(total_camera_pos_list, axis=0)
        self._geo_data = (pos_list, [])

        return sys.getsizeof(self._geo_data)
