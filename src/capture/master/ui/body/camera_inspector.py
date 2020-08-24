from PyQt5.Qt import (
    QPainter, QPen, QBrush, QGraphicsView, QFont,
    QGraphicsScene, QGraphicsPixmapItem, QFrame,
    Qt, QRectF, QLabel, QHBoxLayout, QPixmap
)

from utility.setting import setting

from master.ui.custom_widgets import LayoutWidget
from master.ui.state import state


class CameraInspector(LayoutWidget):
    def __init__(self):
        super().__init__(horizon=False, alignment=Qt.AlignCenter)
        self._serial = None
        self._core = None

        state.on_changed('pixmap_closeup', self._update_pixmap)
        state.on_changed('Calibrate', self._toggle_overlay)
        state.on_changed('current_shot', self._update_shot)

        self._setup_ui()

    def _setup_ui(self):
        self._core = CameraInspectorCore()
        self.addWidget(self._core)

    def _update_pixmap(self):
        if state.get('caching'):
            return
        pixmap = state.get('pixmap_closeup')
        self._core.set_map(pixmap)

    def _update_shot(self):
        state.set('pixmap_closeup', None)

    def get_serial(self):
        return self._serial

    def change_camera(self, serial):
        self._serial = serial
        self._core.change_camera(self._serial)

    def _toggle_overlay(self):
        toggle = state.get('Calibrate')
        self._core.toggle_overlay(toggle)


class CameraInspectorInfo(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self._serial = None
        self._number = None
        self._zoom_ratio = 1
        self._text_label = None

        self._setup_ui()

    def _setup_ui(self):
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.setContentsMargins(0, 8, 0, 0)
        self.setSpacing(0)

        self._text_label = QLabel()
        self._text_label.setStyleSheet('color: palette(bright-text)')
        self.addWidget(self._text_label)
        self._update()

    def _update(self):
        self._text_label.setText(
            f'Camera: {self._number}        '
            f'Serial: {self._serial}        '
            f'Zoom: {self._zoom_ratio:.2f}x'
        )

    def update_info(self, serial=None, zoom=None):
        if serial is not None:
            self._serial = serial
            self._number = setting.get_camera_number_by_id(self._serial)

        if zoom is not None:
            self._zoom_ratio = zoom

        self._update()


class CameraInspectorCore(QGraphicsView):
    _w = setting.camera_resolution[0]
    _h = setting.camera_resolution[1]

    def __init__(self):
        super().__init__()
        self._zoom = 0
        self._scene = None
        self._image = None
        self._last_rect = None
        self._info = None
        self._require_fit_map = False
        self._disconnect_map = None
        self._loading_map = None

        self._setup_ui()

    def _generate_loading_map(self):
        text = 'Loading...'
        pixmap = QPixmap(self._w, self._h)
        pixmap.fill(self.palette().dark().color())
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = QFont()
        font.setPixelSize(60)
        painter.setFont(font)
        painter.setPen(self.palette().text().color())
        text_size = painter.fontMetrics().size(0, text)
        painter.drawText(
            (self._w - text_size.width()) / 2,
            (self._h - text_size.height()) / 2,
            text_size.width(), text_size.height(),
            Qt.AlignCenter,
            text
        )
        painter.end()
        return pixmap

    def _setup_ui(self):
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._loading_map = self._generate_loading_map()

        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(QBrush(self.palette().dark().color()))

        self._image = QGraphicsPixmapItem()
        self._scene.addItem(self._image)

        # hud
        hud_color = self.palette().highlight().color().lighter(150)
        self._overlay = self._scene.addEllipse(
            QRectF(),
            QPen(hud_color, 4),
            QBrush(Qt.NoBrush)
        )
        self._crosshair = self._scene.addEllipse(
            QRectF(),
            QPen(hud_color, 2),
            QBrush(Qt.NoBrush)
        )

        rect = QRectF(0, 0, self._w, self._h)
        cx = rect.center().x()
        cy = rect.center().y()
        r = min(rect.width(), rect.height()) * 0.7
        self._overlay.setRect(
            QRectF(cx - r / 2, cy - r / 2, r, r)
        )
        rc = min(rect.width(), rect.height()) * 0.05
        self._crosshair.setRect(
            QRectF(cx - rc / 2, cy - rc / 2, rc, rc)
        )

        self._overlay.setVisible(False)
        self._crosshair.setVisible(False)

        # scene
        self.setScene(self._scene)

        self._info = CameraInspectorInfo()
        self.setLayout(self._info)

    def toggle_overlay(self, toggle):
        self._overlay.setVisible(toggle)
        self._crosshair.setVisible(toggle)

    def change_camera(self, serial):
        self._info.update_info(serial=serial)
        self.set_map(self._loading_map)
        self._require_fit_map = True

    def set_map(self, pixmap):
        if pixmap and pixmap.width() == self._w:
            self._image.setPixmap(pixmap)
            if self._require_fit_map:
                self._fit_map()
                self._require_fit_map = False
        else:
            self._image.setPixmap(self._loading_map)
            if self._zoom != 0:
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

        self._info.update_info(zoom=self.transform().m11())

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

        self._info.update_info(zoom=self.transform().m11())

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
