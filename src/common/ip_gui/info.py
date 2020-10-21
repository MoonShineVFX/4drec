from PyQt5.Qt import QLabel, QWidget, QVBoxLayout, QColor

from .state import state


class ImageInfo(QWidget):
    def __init__(self):
        super().__init__()
        self._label = QLabel()
        self._setup_ui()

        state.on_changed('hover_color', self._update_color)
        state.set('hover_color', QColor())

    def _setup_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(self._label)

        self.setLayout(layout)

    def _update_color(self):
        color = state.get('hover_color')
        rgb = color.getRgb()
        hsv = color.getHsv()
        self._label.setText(
            'RGB: ' +
            ', '.join(str(c) for c in rgb[:-1]) +
            '\nHSV: ' +
            ', '.join(str(c) for c in hsv[:-1])
        )
