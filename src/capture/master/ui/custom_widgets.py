from PyQt5.Qt import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QStyleOption, QStyle,
    QPainter, Qt, QStackedLayout, QPushButton, QIcon, QSize, QAbstractButton,
    QFont, QFrame, QLabel, QToolTip
)

from master.ui.resource import icons


def make_split_line(vertical=False):
    line = QFrame()

    if vertical:
        line.setFrameShape(QFrame.VLine)
    else:
        line.setFrameShape(QFrame.HLine)

    return line


def move_center(widget):
    widget.layout().invalidate()
    widget.layout().activate()

    parent = widget.parentWidget()
    center = parent.geometry().center()

    widget.setGeometry(
        center.x() - widget.width() / 2,
        center.y() - widget.height() / 2,
        widget.width(), widget.height()
    )


def make_layout(
    horizon=True, grid=False, margin=(0, 0, 0, 0),
    spacing=0, alignment=None, stack=False
):
    if stack:
        layout = QStackedLayout()
    elif grid:
        layout = QGridLayout()
    else:
        if horizon:
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()

    if not isinstance(margin, tuple):
        margin = (margin, margin, margin, margin)

    layout.setContentsMargins(*margin)

    layout.setSpacing(spacing)

    if alignment is not None:
        layout.setAlignment(alignment)

    return layout


class LayoutWidget(QWidget):
    def __init__(
        self, parent=None, horizon=True, grid=False, margin=(0, 0, 0, 0),
        spacing=0, alignment=None, stack=False
    ):
        super().__init__(parent)
        self.setLayout(
            make_layout(horizon, grid, margin, spacing, alignment, stack)
        )
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

    def addWidget(self, widget, *args, **kwargs):
        self.layout().addWidget(widget, *args, **kwargs)

    def addLayout(self, layout):
        self.layout().addLayout(layout)

    def addItem(self, item):
        self.layout().addItem(item)

    def _clear(self):
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().deleteLater()


class PushButton(QPushButton):
    _default = '''
    QPushButton {
        font-size: 20px;
        color: palette(bright-text);
    }
    QPushButton:disabled {
        color: palette(window-text);
    }
    '''

    def __init__(self, text, icon, size):
        super().__init__(text)
        self._size = size
        self._icon = icon
        self._setup_ui()

    def _setup_ui(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(self._default)
        self.setIcon(QIcon(icons.get(self._icon)))
        self.setIconSize(QSize(32, 32))

    def sizeHint(self):
        return QSize(*self._size)


class ToolButton(QAbstractButton):
    def __init__(
        self, text=None, checkable=False,
        spacing=12, margin=(0, 0, 0, 0), source=None
    ):
        super().__init__()
        self._icon = None
        self._hover_icon = None
        self._text = text
        self._source = source
        self._hover = False
        self._spacing = spacing
        self._margin = margin
        self.setCheckable(checkable)
        self._setup_ui()

    def _setup_ui(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setContentsMargins(*self._margin)
        self._update()

    def _update(self):
        if self._source is None:
            source = self._text.lower()
        else:
            source = self._source
        self._icon = icons.get(source)
        self._hover_icon = icons.get(source + '_hl')

    def change_source(self, source):
        self._source = source
        self._update()
        self.update()

    def enterEvent(self, event):
        self._hover = True

    def leaveEvent(self, event):
        self._hover = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.isDown():
            painter.translate(1, 1)

        font = QFont()
        font.setPixelSize(14)
        painter.setFont(font)
        if self._hover or self.isChecked():
            color = self.palette().highlight().color()
            icon = self._hover_icon
        else:
            color = self.palette().text().color()
            icon = self._icon
        painter.setPen(color)

        icon_size = self._icon.size()

        if self._text:
            text_size = painter.fontMetrics().size(0, self._text)
            label_height = (
                text_size.height() + self._spacing + icon_size.height()
            )
        else:
            label_height = icon_size.height()

        center = self.contentsRect().center()

        painter.drawPixmap(
            center.x() - icon_size.width() / 2,
            center.y() - label_height / 2,
            icon
        )

        if self._text:
            painter.drawText(
                center.x() - text_size.width() / 2,
                center.y() - label_height / 2,
                text_size.width(), label_height,
                Qt.AlignBottom | Qt.AlignVCenter,
                self._text
            )


class ElideLabel(QLabel):
    def __init__(self):
        super().__init__()
        self._original_text = ''
        self._set_text = False
        self._max_width = -1

    def setText(self, p_str):
        self._original_text = p_str
        self._set_text = True
        self.elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._set_text:
            self._max_width = self.width()
            self._set_text = False
        self.elide()

    def elide(self):
        if not self._set_text:
            metrics = self.fontMetrics()
            elide_text = metrics.elidedText(
                self._original_text, Qt.ElideMiddle, self._max_width
            )
            if elide_text != self._original_text:
                self.setToolTip(self._original_text)
            else:
                self.setToolTip('')
        else:
            elide_text = self._original_text
        super().setText(elide_text)