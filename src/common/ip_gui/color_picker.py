from PyQt5.Qt import(
    QPixmap, QToolButton, QColorDialog, QIcon, pyqtSignal, QColor
)


class ColorPicker(QToolButton):
    valueChanged = pyqtSignal(object)

    def __init__(self, default_color):
        super().__init__()
        self._set_color(QColor(*default_color))
        self.clicked.connect(self._pick_color)

    def _pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self._set_color(color)

    def _set_color(self, color):
        pixmap = QPixmap(self.iconSize())
        pixmap.fill(color)
        self.setIcon(QIcon(pixmap))
        self.valueChanged.emit(color.getRgb())
