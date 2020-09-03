from threading import Thread, Condition
import time


class FPScounter(Thread):
    def __init__(self, on_tick):
        super().__init__()
        self._lock = Condition()
        self._on_tick = on_tick
        self._count = 0
        self.start()

    def tick(self):
        self._lock.acquire()
        self._count += 1
        self._lock.release()

    def run(self):
        while True:
            t = time.perf_counter()
            self._lock.acquire()
            this_count = self._count
            self._count = 0
            self._lock.release()
            self._on_tick(this_count)
            time.sleep(1 - (time.perf_counter() - t))
