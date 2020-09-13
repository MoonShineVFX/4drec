import math
from PyQt5.Qt import (
    QLabel, Qt, QSizePolicy, QPainter,
    QPen, QRect, QWidget, QPixmap
)

from utility.setting import setting

from master.ui.custom_widgets import LayoutWidget
from master.ui.state import state
from master.ui.resource import icons

from .camera_inspector import CameraInspector


class CameraViewLayout(LayoutWidget):
    def __init__(self):
        super().__init__(stack=True)
        self._camera_views = []
        self._inspector = None
        self._is_recording = False
        self._setup_ui()

        state.on_changed('recording', self._toggle_recording)
        state.on_changed('closeup_camera', self._update)
        state.on_changed('key', self._on_key_pressed)

    def _setup_ui(self):
        self._generate_camera_views()
        counts = int(len(self._camera_views) / 2)

        self._inspector = CameraInspector()

        page_overview_widgets = [CameraViewGrid(self._camera_views)]
        page_inspector_widgets = [
            CameraViewGrid(self._camera_views[:counts], half=True),
            self._inspector,
            CameraViewGrid(self._camera_views[counts:], half=True)
        ]

        for widgets in (page_overview_widgets, page_inspector_widgets):
            self.addWidget(CameraPage(widgets))

        self._update()

    def _update(self):
        closeup_camera = state.get('closeup_camera')
        inspector_serial = self._inspector.get_serial()
        self._inspector.change_camera(closeup_camera)

        if closeup_camera is None:
            self.layout().setCurrentIndex(0)
        elif closeup_camera is not None and inspector_serial is None:
            self.layout().setCurrentIndex(1)

    def _generate_camera_views(self):
        set_resize_leader = True
        for camera_id in setting.get_working_camera_ids():
            camera_number = setting.get_camera_number_by_id(camera_id)

            camera_view = CameraView(
                camera_number, camera_id,
                resize_leader=set_resize_leader
            )

            if set_resize_leader:
                set_resize_leader = False

            self._camera_views.append(camera_view)

    def _toggle_recording(self):
        self._is_recording = state.get('recording')
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            if state.get('closeup_camera') is not None:
                state.set('closeup_camera', None)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._is_recording:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 4))
            painter.drawRect(QRect(2, 2, self.width() - 4, self.height() - 4))

    def _on_key_pressed(self):
        if not self.isVisible():
            return
        key = state.get('key')
        if key == Qt.Key_Up:
            self._change_closeup(-1)
        elif key == Qt.Key_Down:
            self._change_closeup(1)
        elif key == Qt.Key_Escape:
            closeup_camera = state.get('closeup_camera')
            if closeup_camera is not None:
                state.set('closeup_camera', None)

    def _change_closeup(self, step):
        closeup_camera = state.get('closeup_camera')
        if closeup_camera is None:
            return

        camera_ids = setting.get_working_camera_ids()
        idx = camera_ids.index(closeup_camera)
        idx += step

        if idx >= len(camera_ids):
            idx = 0
        elif idx < 0:
            idx = len(camera_ids) - 1

        state.set('closeup_camera', camera_ids[idx])


class CameraPage(LayoutWidget):
    def __init__(self, widgets):
        super().__init__()
        self._widgets = widgets
        self._setup_ui()

    def _setup_ui(self):
        for widget in self._widgets:
            self.addWidget(widget)

        if len(self._widgets) > 1:
            self.layout().setStretch(1, 1)


class CameraViewGrid(LayoutWidget):
    def __init__(self, camera_views, half=False):
        super().__init__(grid=True, margin=8, spacing=8)
        self._camera_views = camera_views
        self._is_half = half
        self._setup_ui()

    def _setup_ui(self):
        for i in range(self.layout().columnCount()):
            self.layout().setColumnStretch(i, 1)
        for i in range(self.layout().rowCount()):
            self.layout().setRowStretch(i, 1)

    def showEvent(self, event):
        if not self._is_half:
            self._insert_camera_views(6)
        else:
            self._insert_camera_views(2)
        self._setup_ui()

    def hideEvent(self, event):
        for camera_view in self._camera_views:
            self.layout().removeWidget(camera_view)

    def _insert_camera_views(self, column):
        for i, camera_view in enumerate(self._camera_views):
            x = i % column
            y = math.floor(i / column)
            self.addWidget(camera_view, y, x)
            i += 1


class CameraView(LayoutWidget):
    def __init__(self, camera_number, camera_id, resize_leader=False):
        super().__init__(horizon=False, alignment=Qt.AlignCenter)
        self._camera_number = camera_number
        self._camera_id = camera_id
        self._image = None
        self._info = None
        self._inspect = False
        self._resize_leader = resize_leader
        self._setup_ui()

        state.on_changed('closeup_camera', self._update_inspect)
        state.on_changed(f'pixmap_{self._camera_id}', self._update_pixmap)
        state.on_changed('body_mode', lambda: self._image.set_map(None))

    def _update_inspect(self):
        closeup_camera = state.get('closeup_camera')
        self._inspect = self._camera_id == closeup_camera
        self._image.set_inspect(self._inspect)

    def _update_pixmap(self):
        if not self._inspect and not state.get('caching'):
            pixmap = state.get(f'pixmap_{self._camera_id}')
            self._image.set_map(pixmap)

    def _setup_ui(self):
        self.setMinimumSize(120, 100)

        self._image = CameraImage(self._resize_leader)
        self.addWidget(self._image)

        self._info = CameraViewInfo(self._camera_number, self._camera_id)
        self.addWidget(self._info)

        self.layout().setStretch(0, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._inspect:
                state.set('closeup_camera', self._camera_id)
            event.accept()
        event.ignore()


class CameraImage(QWidget):
    _aspect_ratio = (
        setting.camera_resolution[1] / setting.camera_resolution[0]
    )

    def __init__(self, resize_leader):
        super().__init__()
        self._pixmap = None
        self._paint_rect = QRect(
            0, 0, self.width(), self.height()
        )

        self._hover = False
        self._inspect = False
        self._resize_leader = resize_leader

        self._setup_ui()

    def set_map(self, pixmap):
        if isinstance(pixmap, QPixmap):
            self._pixmap = pixmap
            self.update()

    def _setup_ui(self):
        self.setAttribute(Qt.WA_Hover, True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self._inspect_map = icons.get('inspect')
        self._pixmap = icons.get('connect_none')

    def set_inspect(self, inspect):
        if self._inspect != inspect:
            self._inspect = inspect
            self.update()

    def resizeEvent(self, event):
        # TODO inspect condition has some bug to find out. aspect not work as i want
        if self.width() > self.height():
            width = self.height() / self._aspect_ratio
            width_margin = (self.width() - width) / 2
            self._paint_rect = QRect(
                width_margin, 0,
                width, self.height()
            )
        else:
            height = self.width() * self._aspect_ratio
            height_margin = (self.height() - height) / 2
            self._paint_rect = QRect(
                0, height_margin,
                self.width(), height
            )

        if (
            self._resize_leader and
            self.isVisible()
        ):
            value = self._paint_rect.width()
            if value > 0:
                state.set(
                    'live_view_size',
                    value
                )

    def enterEvent(self, event):
        if not self._inspect:
            self._hover = True
            self.setCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self._hover = False
        self.unsetCursor()

    def paintEvent(self, event):
        painter = QPainter(self)

        if self._inspect:
            painter.drawPixmap(
                (self.width() - self._inspect_map.width()) / 2,
                (self.height() - self._inspect_map.height()) / 2,
                self._inspect_map
            )
            return

        if self._pixmap.width() > 50:
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(
                self._paint_rect, self._pixmap
            )
        else:
            painter.drawPixmap(
                (self.width() - self._pixmap.width()) / 2,
                (self.height() - self._pixmap.height()) / 2,
                self._pixmap
            )

        if self._hover:
            painter.setPen(QPen(self.palette().highlight().color(), 2))
            painter.drawRect(self._paint_rect)


class CameraViewInfo(LayoutWidget):
    def __init__(self, camera_number, camera_id):
        super().__init__(stack=True)
        self._camera_number = camera_number
        self._camera_id = camera_id
        self._number_text = self._make_number_text()
        state.on_changed('Serial', self._update)
        self._setup_ui()

    def _make_number_text(self):
        position_id = setting.get_position_id_by_number(self._camera_number)
        return f'{position_id} ({self._camera_number:02d})'

    def _setup_ui(self):
        for text, icon in ((self._number_text, 'camera'), (self._camera_id, 'tag')):
            layout = LayoutWidget(spacing=8, alignment=Qt.AlignCenter)
            icon_label = QLabel()
            icon_label.setPixmap(icons.get(icon))
            text_label = QLabel(text)

            layout.addWidget(icon_label)
            layout.addWidget(text_label)

            self.addWidget(layout)

        self._update()

    def _update(self):
        serial = state.get('Serial')
        if serial:
            self.layout().setCurrentIndex(1)
        else:
            self.layout().setCurrentIndex(0)
