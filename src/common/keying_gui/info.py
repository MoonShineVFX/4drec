from PyQt5.Qt import QLabel, QWidget, QVBoxLayout

from .state import state


class ImageInfo(QWidget):
    def __init__(self):
        super().__init__()
        self._label = QLabel('info')
        self._setup_ui()

        state.on_changed('hover_color', self._update)

    def _setup_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(self._label)

        self.setLayout(layout)

    def _update(self):
        color = state.get('hover_color')
        rgb = color.getRgb()
        hsv = color.getHsv()
        self._label.setText(
            'RGB: ' +
            ', '.join(str(c) for c in rgb[:-1]) +
            '\nHSV: ' +
            ', '.join(str(c) for c in hsv[:-1])
        )
