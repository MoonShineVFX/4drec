from PyQt5.Qt import (
    QPainter, QGraphicsView, QImage, QPixmap,
    QGraphicsScene, QGraphicsPixmapItem, QFrame,
    Qt, QRectF, QWidget, QVBoxLayout, QColor
)
import cv2

from .state import state
from common.keying import ImagePayload


class ImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        self._core = ImageViewerCore()

        state.on_changed('keying_image', self._update_keying_image)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._core)
        self.setLayout(layout)

    def _update_keying_image(self):
        image = state.get('keying_image')
        if image is None:
            return
        original = image.get_image(ImagePayload.ORIGINAL)
        pixmap = self._convert_pixmap(original)
        self._core.set_map(pixmap)

    def _convert_pixmap(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        height, width, _ = image.shape
        q_image = QImage(
            image.data,
            width,
            height,
            3 * width,
            QImage.Format_RGB888
        )
        return QPixmap.fromImage(q_image)


class ImageViewerCore(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._zoom = 0
        self._image = KeyingImageItem()
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
        self._image.setPixmap(pixmap)
        self._fit_map()

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


class KeyingImageItem(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__()
        self.setAcceptHoverEvents(True)

    def hoverMoveEvent(self, event):
        pos = event.pos()
        color = self.pixmap().toImage().pixel(pos.x(), pos.y())
        color = QColor(color)
        state.set('hover_color', color)
