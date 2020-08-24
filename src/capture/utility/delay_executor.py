from threading import Thread
from queue import Queue
import time


class DelayExecutor(Thread):
    def __init__(self, interval=0.05):
        super().__init__()
        self._queue = Queue()
        self._interval = interval

        self.start()

    def run(self):
        while True:
            func = self._queue.get()
            while not self._queue.empty():
                func = self._queue.get()

            time.sleep(self._interval)

            if self._queue.empty():
                func()

    def execute(self, func):
        self._queue.put(func)
