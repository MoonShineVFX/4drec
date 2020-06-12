from PyQt5.Qt import (
    Qt, QSize, QHBoxLayout
)

from master.ui.custom_widgets import ToolButton
from master.ui.state import state


class SupportButtonGroup(QHBoxLayout):
    _checkable_list = [
        'Serial', 'Calibrate', 'Focus', 'Rig', 'Wireframe', 'Crop'
    ]

    def __init__(self, button_texts):
        super().__init__()
        self._button_texts = button_texts
        self.buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setAlignment(Qt.AlignRight)
        self.setSpacing(16)

        for text in self._button_texts:
            checkable = text in self._checkable_list
            button = SupportButton(text, checkable)
            self.buttons[text] = button
            self.addWidget(button)


class SupportButton(ToolButton):
    def __init__(self, text, checkable=False):
        super().__init__(text, checkable)
        self.setFocusPolicy(Qt.NoFocus)
        self._text = text
        self.clicked.connect(self._on_click)
        if checkable:
            state.on_changed(text, self._update_check)

    def sizeHint(self):
        return QSize(76, 70)

    def _update_check(self):
        is_check = state.get(self._text)
        if is_check != self.isChecked():
            self.setChecked(is_check)

    def _on_click(self):
        if self.isCheckable():
            state.set(self._text, self.isChecked())
