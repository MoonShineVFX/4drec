from queue import Queue
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed

from .package import RigPackage, ResolvePackage


def load_geometry(job_id, cali_id, frame):
    # check rig or 4df
    if frame is None:
        package = RigPackage(job_id, cali_id)
    else:
        package = ResolvePackage(job_id, frame)

    result = package.load()

    # no files
    if result is None:
        return None

    return package


def export_geometry(load_path, filename, frame, export_path):
    from common.fourd_frame import FourdFrameManager

    fourd_frame = FourdFrameManager.load(load_path)

    # with open(f'{export_path}/obj/{filename}_{frame:04d}.obj', 'w') as f:
    #     f.write(fourd_frame.get_obj_data())

    with open(f'{export_path}/geo/{filename}_{frame:04d}.4dh', 'wb') as f:
        f.write(fourd_frame.get_houdini_data())

    with open(f'{export_path}/texture/{filename}_{frame:04d}.jpg', 'wb') as f:
        f.write(fourd_frame.get_texture_data(raw=True))


class MultiExecutor(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self._queue = Queue()
        self._manager = manager
        self.start()

    def cache_all(self, tasks):
        future_list = []
        with ProcessPoolExecutor() as executor:
            for job_id, cali_id, f in tasks:
                future = executor.submit(
                    load_geometry, job_id, cali_id, f
                )
                future_list.append(future)

            for future in as_completed(future_list):
                package = future.result()
                if package is not None:
                    self._manager.save_package(package)
                self._manager.send_ui(None)

    def export_all(self, tasks):
        from utility.setting import setting
        import os
        import re
        from pathlib import Path

        folder_name, job_id, frames, export_path = tasks
        load_path = (
            f'{setting.submit_job_path}{job_id}/export/'
        )
        offset_frame = frames[0] - 1

        folder_name = re.sub(r'[^\w\d-]', '_', folder_name)
        export_path = Path(f'{export_path}/{folder_name}/')
        # (export_path / 'obj').mkdir(parents=True, exist_ok=True)
        (export_path / 'geo').mkdir(parents=True, exist_ok=True)
        (export_path / 'texture').mkdir(parents=True, exist_ok=True)

        with ProcessPoolExecutor() as executor:
            future_list = []
            for f in frames:
                offset_f = f - offset_frame
                file_path = f'{load_path}{f:06d}.4df'

                if not os.path.isfile(file_path):
                    self._manager.ui_tick_export()
                    continue

                future = executor.submit(
                    export_geometry,
                    file_path,
                    folder_name,
                    offset_f,
                    str(export_path)
                )
                future_list.append(future)

            for _ in as_completed(future_list):
                self._manager.ui_tick_export()

    def run(self):
        while True:
            task_type, tasks = self._queue.get()

            if task_type == 'cache_all':
                self.cache_all(tasks)
            elif task_type == 'export_all':
                self.export_all(tasks)

    def add_task(self, task_type, tasks):
        self._queue.put((task_type, tasks))
