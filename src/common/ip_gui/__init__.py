import sys
import traceback
from PyQt5.Qt import QApplication
from PyQt5 import QtCore

from .main import MainWindow


def start_gui():
    def excepthook(type_, value, traceback_):
        traceback.print_exception(type_, value, traceback_)
        QtCore.qFatal('')

    sys.excepthook = excepthook

    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())

