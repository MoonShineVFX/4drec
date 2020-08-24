from PyQt5.Qt import QLabel, Qt

from master.ui.state import state


class SecondScreenView(QLabel):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        state.on_changed('closeup_camera', self._toggle_pixmap)
        state.on_changed('pixmap_closeup', self._set_pixmap)

    def _setup_ui(self):
        self.setStyleSheet('background-color: black;')
        self.setFixedSize(1920, 1080)
        self.setAlignment(Qt.AlignCenter)
        self.setWindowTitle('Preview')
        self._clear()

    def _set_pixmap(self):
        if self.isVisible():
            pixmap = state.get('pixmap_closeup')
            if pixmap is None:
                return
            self.setPixmap(
                pixmap.scaled(
                    self.width(),
                    self.height(),
                    Qt.KeepAspectRatio
                )
            )

    def _toggle_pixmap(self):
        closeup_camera = state.get('closeup_camera')
        if closeup_camera is None:
            self._clear()

    def _clear(self):
        self.clear()
        self.setText('4DREC preview')
