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
        self._queue = Queue()
        self._manager = manager
        self.start()

    def run(self):
        while True:
            tasks = self._queue.get()

            future_list = []
            with ProcessPoolExecutor() as executor:
                for job_id, cali_id, f in tasks:
                    future = executor.submit(
                        load_geometry, job_id, cali_id, f
                    )
                    future_list.append(future)

                for future in as_completed(future_list):
                    package = future.result()
                    self._manager.save_package(package)
                    self._manager.send_ui(None)

    def add_task(self, task):
        self._queue.put(task)
