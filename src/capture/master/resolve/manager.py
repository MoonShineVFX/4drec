import threading
from queue import Queue

from utility.define import UIEventType
from utility.delay_executor import DelayExecutor

from master.ui import ui
from master.projects import project_manager

from .package import ResolvePackage, RigPackage
from .multi_executor import MultiExecutor


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
        result = package.load()
        if result is None:
            self.send_ui(None)
            return

        self.save_package(package)
        self.send_ui(package)

    def send_ui(self, package):
        payload = None
        if package is not None:
            payload = package.to_payload()
        ui.dispatch_event(
            UIEventType.RESOLVE_GEOMETRY,
            payload
        )

    def _add_task(self, package):
        self._queue.put(package)

    def save_package(self, package):
        job_id, frame = package.get_meta()
        if job_id not in self._cache:
            self._cache[job_id] = {}

        self._cache[job_id][frame] = package

        if frame is not None:
            job = project_manager.get_job(job_id)
            job.update_cache_progress(frame, package.get_cache_size())

    def cache_whole_job(self):
        job = project_manager.current_job
        job_id = job.get_id()
        cali_id = job.get_cali_id()
        
        tasks = []
        for f in job.frames:
            if self.has_cache(job_id, f):
                self.send_ui(None)
                continue
            tasks.append((job_id, cali_id, f))
        
        self._multi_executor.add_task(tasks)

    def has_cache(self, job_id, frame):
        return job_id in self._cache and frame in self._cache[job_id]

    def request_geometry(
        self, job, frame, is_delay=True
    ):
        job_id = job.get_id()
        cali_id = job.get_cali_id()

        # get already cached
        if self.has_cache(job_id, frame):
            package = self._cache[job_id][frame]
            self.send_ui(package)

        # load rig data
        elif frame is None:
            package = RigPackage(job_id, cali_id)
            self._add_task(package)
        # load frame 4df
        else:
            package = ResolvePackage(job_id, frame)
            if is_delay:
                self._delay.execute(
                    lambda: self._add_task(package)
                )
            else:
                self._add_task(package)
