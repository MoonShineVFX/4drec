"""圖形介面

採用 Qt 的主介面
藉由 UIEvent 來跟外部溝通

"""

import threading
import sys
from PyQt5.Qt import QApplication, QIcon

from utility.logger import log
from utility.define import UIEventType

from .theme import apply_theme
from .main import MainWindow


class MasterUI(threading.Thread):
    """主介面控制

    將介面分離主執行緒來執行
    屬性皆取自 MainUI

    """

    def __init__(self, lock):
        super().__init__()
        self._lock = lock

        # 直接開始執行
        self.start()

    def __getattr__(self, prop):
        if self._main is None:
            raise AttributeError("Main UI isn't initialized")
        return getattr(self._main, prop)

    def run(self):
        """執行 Qt"""
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon('source/icon/ico.svg'))
        apply_theme(app)
        log.info('Initialize UI')
        main_window = MainWindow()
        self._main = main_window
        # self._main.show()

        self._lock.acquire()
        self._lock.notify()
        self._lock.release()

        app.exec_()

    def show(self):
        self._main.dispatch_event(UIEventType.UI_SHOW)


lock = threading.Condition()
ui = MasterUI(lock)  # 單一實例
lock.acquire()
lock.wait()
lock.release()
