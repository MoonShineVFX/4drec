from PyQt5.Qt import (
    QPainter, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QFrame,
    Qt, QRectF, QWidget, QVBoxLayout, QColor
)

from .state import state
from .utility import convert_pixmap_from_cvimage


class ImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        self._core = ImageViewerCore()

        state.on_changed('image_processor', self._update)
        state.on_changed('update_process', self._update)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._core)
        self.setLayout(layout)

    def _update(self):
        image = state.get('image_processor')
        if image is None:
            return
        result = image.get_image()
        if result is None:
            return
        pixmap = convert_pixmap_from_cvimage(result)
        self._core.set_map(pixmap)


class ImageViewerCore(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._zoom = 0
        self._image = ResultImageItem()
        self._last_rect = None

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet('background:transparent;')
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setScene(QGraphicsScene(self))
        self.scene().addItem(self._image)

    def set_map(self, pixmap):
        fit = 0
        if self._image.pixmap().isNull():
            fit = 1
        elif self._image.pixmap().rect() != pixmap.rect():
            fit = 2
        self._image.setPixmap(pixmap)

        if fit == 1:
            self._fit_map()
        elif fit == 2:
            self._match_zoom()

    def _match_zoom(self):
        lw = self.sceneRect().width()
        vs = self.verticalScrollBar()
        hs = self.horizontalScrollBar()
        vsf = vs.value() / vs.maximum()
        hsf = hs.value() / hs.maximum()

        self.setSceneRect(QRectF(self._image.pixmap().rect()))

        cw = self.sceneRect().width()
        factor = lw / cw
        self.scale(factor, factor)

        vs.setValue(int(vs.maximum() * vsf))
        hs.setValue(int(hs.maximum() * hsf))

    def _fit_map(self):
        self.setDragMode(QGraphicsView.NoDrag)
        rect = QRectF(self._image.pixmap().rect())
        self.setSceneRect(rect)

        # 取得目前 scale，歸回 scale 1
        m = self.transform().mapRect(QRectF(0, 0, 1, 1))
        self.scale(1 / m.width(), 1 / m.height())

        # 縮放成適合圖像大小
        scenerect = self.transform().mapRect(rect)
        factor = min(
            self.width() / scenerect.width(),
            self.height() / scenerect.height()
        )
        self.scale(factor, factor)

        self._zoom = 0

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            factor = 1.25
            self._zoom += 1
        else:
            factor = 0.8
            self._zoom -= 1

        if self._zoom > 0:
            self.scale(factor, factor)
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif self._zoom == 0:
            self._fit_map()
        else:
            self._zoom = 0

    def resizeEvent(self, event):
        if not self.isVisible():
            return

        if self._zoom == 0:
            if not self._image.pixmap().isNull():
                self._fit_map()
        elif self._last_rect is not None:
            la = self._last_rect.center()
            c = self.rect().center()
            self.translate(c.x() - la.x(), c.y() - la.y())

        self._last_rect = self.rect()


class ResultImageItem(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__()
        self.setAcceptHoverEvents(True)

    def hoverMoveEvent(self, event):
        pos = event.pos()
        color = self.pixmap().toImage().pixel(pos.x(), pos.y())
        color = QColor(color)
        state.set('hover_color', color)
