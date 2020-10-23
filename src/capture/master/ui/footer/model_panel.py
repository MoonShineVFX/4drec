from PyQt5.Qt import Qt, QFileDialog

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.dialog import (
    CacheProgressDialog, ExportProgressDialog, ScreenshotProgressDialog
)
from master.ui.popup import popup
from master.ui.state import state

from .support_button import SupportButtonGroup


class ModelPanel(LayoutWidget):
    def __init__(self, playback_control):
        super().__init__(spacing=12)
        self._playback_control = playback_control
        self.buttons = None
        self._setup_ui()

        state.on_changed('key', self._on_key_pressed)

    def _setup_ui(self):
        self.buttons = SupportButtonGroup(
            ('Cache', 'Rig', 'Wireframe', 'Loop', 'Screenshot')
        )
        self.buttons.buttons['Cache'].clicked.connect(self._on_cache)
        self.buttons.buttons['Screenshot'].clicked.connect(
            self._on_take_screenshot
        )

        self.layout().addLayout(
            self.buttons
        )

        button = PushButton(
            '  EXPORT', 'export', size=(180, 60)
        )
        button.clicked.connect(self._export_model)

        self.addWidget(button)

    def showEvent(self, event):
        self.layout().insertLayout(1, self._playback_control)

    def hideEvent(self, event):
        self.layout().removeItem(self._playback_control)

    def _on_cache(self):
        popup(dialog=CacheProgressDialog)

    def _on_take_screenshot(self):
        if state.get('playing'):
            state.set('playing', False)
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if directory is not None and directory != '':
            popup(dialog=ScreenshotProgressDialog, dialog_args=(directory,))

    def _on_key_pressed(self):
        if self.isHidden():
            return

        key = state.get('key')
        if key == Qt.Key_W:
            self.buttons.buttons['Wireframe'].animateClick()
        elif key == Qt.Key_R:
            self.buttons.buttons['Rig'].animateClick()
        elif key == Qt.Key_C:
            self.buttons.buttons['Cache'].animateClick()

    def _export_model(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if directory is not None and directory != '':
            popup(dialog=ExportProgressDialog, dialog_args=(directory,))
