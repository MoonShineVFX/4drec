from PyQt5.Qt import (
    QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, Qt
)

from common.keying import KeyingImage

from .image_viewer import ImageViewer
from .info import ImageInfo
from .effect_list import EffectList
from .state import state


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.show()

        state.set('keying_image', KeyingImage(r"C:\Users\moonshine\Desktop\19471994_002473.jpg"))

    def _setup_ui(self):
        self.setMinimumSize(1572, 1000)

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
        self.setFixedWidth(200)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(ImageInfo())
        layout.addWidget(EffectList())

        self.setLayout(layout)
