from PyQt5.Qt import (
    QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, Qt
)

from common.image_processor import ImageProcessor

from .image_viewer import ImageViewer
from .info import ImageInfo
from .process_list import ProcessList
from .state import state
from .utility import update_process


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.show()

        state.set('image_processor', ImageProcessor())
        update_process()

    def _setup_ui(self):
        self.setMinimumSize(1672, 1000)

        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(ImageViewer())
        layout.addWidget(SideMenu())

        widget.setLayout(layout)

        self.setCentralWidget(widget)


class SideMenu(QWidget):
    def __init__(self):
        super().__init__()

        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(300)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(ImageInfo())
        layout.addWidget(ProcessList())

        self.setLayout(layout)
