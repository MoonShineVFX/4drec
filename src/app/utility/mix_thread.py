from utility.setting import setting

if setting.is_master():
    from PyQt5.QtCore import QThread
    thread = QThread
else:
    from threading import Thread as TThread
    thread = TThread


class MixThread(thread):
    """自製執行緒

    根據 master 和 slave 的不同採用 QThread 或 Thread
    並有預設的 running 步驟，免去重複性的屬性宣告

    """

    def __init__(self):
        super().__init__()
        self._running = False  # 是否正在運行

    def run(self):
        self._running = True
        self._pre_run()
        self._run()
        self._after_run()
        self._running = False

    def stop(self):
        self._stop()
        if self._running:
            self._running = False
        self._after_stop()

    def _stop(self):
        pass

    def _after_stop(self):
        pass

    def _pre_run(self):
        pass

    def _run(self):
        pass

    def _after_run(self):
        pass

    def is_running(self):
        return self._running
