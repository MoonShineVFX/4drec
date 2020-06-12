import threading
import time


class Repeater(threading.Thread):
    """重複執行器

    每隔一段時間執行給予的函式

    Args:
        func: 要執行的函式
        interval: 間隔(秒)
        autostart: 是否自動執行

    """

    def __init__(self, func, interval, autostart=False):
        super().__init__()
        self._func = func  # 執行的函式
        self._interval = interval  # 間隔(秒)

        self._running = True

        if autostart:
            self.start()

    def run(self):
        while self._running:
            self._func()
            time.sleep(self._interval)

    def stop(self, block=False):
        """停止運作

        Args:
            block: 是否中斷線程

        """
        self._running = False
        if block:
            self.join()
