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


class MultiExecutor(threading.Thread):
    def __init__(self, manager):
        super().__init__()
        self._manager = manager
        self._queue = Queue()
        self.start()

    def run(self):
        while True:
            job = self._queue.get()
            job_id = job.get_id()
            cali_id = job.get_cali_id()

            with ProcessPoolExecutor() as executor:
                tasks = []
                for f in job.frames:
                    if self._manager.has_cache(job_id, f):
                        self._manager.send_ui(None)
                        continue
                    future = executor.submit(
                        load_geometry, job_id, cali_id, f
                    )
                    tasks.append(future)

                for future in as_completed(tasks):
                    package = future.result()
                    if package is not None:
                        self._manager.save_package(package)
                    self._manager.send_ui(None)

    def add_task(self, shot):
        self._queue.put(shot)
