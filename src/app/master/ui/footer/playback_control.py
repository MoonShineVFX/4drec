from PyQt5.Qt import (
    Qt, QLabel, QThread, pyqtSignal, QPainterPath,
    QSlider, QRect, QPainter, QSize, QVBoxLayout, QColor, QBrush
)
from threading import Condition
from functools import partial
import math
from time import perf_counter

from utility.setting import setting
from utility.define import CameraCacheType, BodyMode, TaskState

from master.ui.state import state, EntityBinder, get_real_frame, step_pace
from master.ui.custom_widgets import LayoutWidget, make_layout, ToolButton


class PlaybackControl(QVBoxLayout):
    def __init__(self):
        super().__init__()
        self._player = None
        self._entity = None
        self._playback_bar = None
        self._setup_ui()
        state.on_changed('current_slider_value', self._on_slider_value_changed)
        state.on_changed('closeup_camera', self._on_slider_value_changed)

        state.on_changed('body_mode', self._on_entity_changed)
        state.on_changed('current_shot', self._on_entity_changed)
        state.on_changed('current_job', self._on_entity_changed)

        state.on_changed('key', self._on_key_pressed)

    def _on_entity_changed(self):
        self._stop_function()

        body_mode = state.get('body_mode')
        if body_mode is BodyMode.LIVEVIEW:
            self._entity = None
            return
        else:
            job = state.get('current_job')
            if job is not None:
                self._entity = job
            else:
                shot = state.get('current_shot')
                self._entity = shot

        self._playback_bar.on_entity_changed(self._entity)
        if self._entity is not None and self._entity.state != 0:
            self._on_slider_value_changed()

    def _setup_ui(self):
        self.setAlignment(Qt.AlignCenter)
        self.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)

        self._playback_bar = PlaybackBar()
        self.addWidget(self._playback_bar)

        layout = make_layout(alignment=Qt.AlignCenter, spacing=60)
        for source in ('clipleft', 'previous', 'play', 'next', 'clipright'):
            button = PlaybackButton(source)
            button.clicked.connect(partial(self._on_click, source))

            layout.addWidget(button)

        self.addLayout(layout)

    def _on_slider_value_changed(self):
        if self._entity is None or not self.isEnabled():
            return

        slider_value = state.get('current_slider_value')
        real_frame = get_real_frame(slider_value)

        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            closeup_camera = state.get('closeup_camera')
            state.cast(
                'camera', 'request_shot_image', self._entity.get_id(),
                real_frame, closeup_camera=closeup_camera, delay=True
            )
        elif body_mode is BodyMode.MODEL:
            job = state.get('current_job')
            if job is None:
                return

            state.cast(
                'resolve', 'request_geometry',
                self._entity, real_frame
            )

        self._playback_bar.on_slider_value_changed(slider_value)

    def _stop_function(self):
        if state.get('playing'):
            state.set('playing', False)

        if state.get('Crop'):
            state.set('Crop', False)
            state.set('crop_range', [None, None])

    def _on_click(self, source):
        if source == 'previous':
            step_pace(forward=False)
        elif source == 'play':
            if state.get('playing'):
                state.set('playing', False)
                self._player = None
            else:
                self._player = ShotPlayer(
                    lambda: step_pace(stop=False)
                )
                state.set('playing', True)
        elif source == 'next':
            step_pace(forward=True)
        elif source == 'clipleft':
            crop_range = state.get('crop_range')
            current_slider_value = state.get('current_slider_value')
            if crop_range[1] and current_slider_value > crop_range[1]:
                return
            else:
                crop_range[0] = current_slider_value
                state.set('crop_range', crop_range)
        elif source == 'clipright':
            crop_range = state.get('crop_range')
            current_slider_value = state.get('current_slider_value')
            if crop_range[0] and current_slider_value < crop_range[0]:
                return
            else:
                crop_range[1] = current_slider_value
                state.set('crop_range', crop_range)

    def _on_key_pressed(self):
        if self.parentWidget() is None:
            return

        key = state.get('key')
        if key == Qt.Key_Space:
            self._on_click('play')


class ShotPlayer(QThread):

    tick = pyqtSignal()

    def __init__(self, callback):
        super().__init__()
        self._playing = False
        self._current_loaded = 0
        self._threashold = None
        self._sleep_time = 1 / setting.frame_rate
        self._cond = Condition()
        self._prepare()
        self.tick.connect(callback)
        state.on_changed('playing', self._toggle)
        self.start()

    def run(self):
        self._playing = True
        while self._playing:
            self.tick.emit()
            start = perf_counter()
            self._cond.acquire()
            self._cond.wait()
            self._cond.release()
            duration = perf_counter() - start
            if duration < self._sleep_time:
                self.msleep(int((self._sleep_time - duration) * 1000))

    def _prepare(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            self._threashold = len(setting.cameras)
            for camera_id in setting.cameras:
                state.on_changed(f'pixmap_{camera_id}', self._loaded)
            if state.get('closeup_camera'):
                state.on_changed('pixmap_closeup', self._loaded)
                self._threashold += 1
        elif body_mode is BodyMode.MODEL:
            self._threashold = 1
            state.on_changed('opengl_data', self._loaded)

    def _notify(self):
        self._cond.acquire()
        self._cond.notify()
        self._cond.release()
        self._current_loaded = 0

    def _loaded(self):
        self._current_loaded += 1
        if self._current_loaded == self._threashold:
            self._notify()

    def _toggle(self):
        if not state.get('playing'):
            self._playing = False
            self._notify()


class PlaybackBar(LayoutWidget):
    _default = '''
    QLabel {
        font-size: 20px;
    }
    '''

    def __init__(self):
        super().__init__(
            alignment=Qt.AlignCenter, spacing=16, margin=(32, 0, 32, 0)
        )
        self._labels = []
        self._slider = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(self._default)

        for i in range(2):
            label = QLabel()
            label.setMinimumWidth(80)
            if i == 0:
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            elif i == 1:
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._labels.append(label)

        self._slider = PlaybackSlider()
        self._slider.valueChanged.connect(self._on_slider_changed)

        self.layout().addWidget(self._labels[0])
        self.layout().addWidget(self._slider)
        self.layout().addWidget(self._labels[1])

    def on_entity_changed(self, entity):
        if entity is None:
            return

        current_slider_value = state.get('current_slider_value')
        current_real_frame = get_real_frame(current_slider_value)

        if entity.has_prop('frame_range'):
            if entity.state < 1:
                return

            sf, ef = entity.frame_range
            frames = [f for f in range(sf, ef + 1)]

            state.set('offset_frame', sf)
        elif entity.has_prop('frames'):
            frames = entity.frames
            frames.sort()

        if current_real_frame in frames:
            current_slider_value = frames.index(current_real_frame)
        else:
            current_slider_value = 0

        offset_frame = state.get('offset_frame')
        frames = [f - offset_frame for f in frames]
        state.set('frames', frames)

        max_slider_value = len(frames) - 1
        self._slider.setMaximum(max_slider_value)

        state.set('current_slider_value', current_slider_value)

        self._labels[0].setText(str(frames[0]))
        self._labels[1].setText(str(frames[-1]))

        self.on_slider_value_changed(current_slider_value)
        self._slider.on_entity_changed(entity)

    def on_slider_value_changed(self, frame):
        if self._slider.value() != frame:
            self._slider.setValue(frame)

    def _on_slider_changed(self, value):
        if state.get('current_slider_value') != value:
            state.set('current_slider_value', value)


class PlaybackSlider(QSlider, EntityBinder):
    _default = '''
    PlaybackSlider {
        height: 60px
    }
    PlaybackSlider::add-page, PlaybackSlider::sub-page {
      background: none;
    }
    PlaybackSlider::handle {
      margin: -4px 0px -8px 0px;
    }
    '''
    _deadline_color = {
        TaskState.QUEUED: QColor('#a3a3a3'),
        TaskState.SUSPENDED: QColor('#212121'),
        TaskState.RENDERING: QColor('#057907'),
        TaskState.COMPLETED: QColor('#055679'),
        TaskState.FAILED: QColor('#791e05'),
        TaskState.PENDDING: QColor('#795c05')
    }
    _crop_size = (8, 8, 10)
    _bar_height = 10
    _handle_width = 8

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self._cache_progress = None
        self._tasks = {}
        self._crop_path = None
        self._crop_brush = None
        self._setup_ui()
        state.on_changed('crop_range', self._update)
        state.on_changed('Crop', self._update)

    def _update(self):
        if not state.get('caching') and self.isVisible():
            self.update()

    def _setup_ui(self):
        self.setStyleSheet(self._default)

        cw, ch, _ = self._crop_size
        path = QPainterPath()
        path.moveTo(0, ch)
        path.lineTo(cw / 2, 0)
        path.lineTo(cw, ch)
        path.lineTo(0, ch)
        self._crop_path = path
        self._crop_brush = QBrush(self.palette().light().color())

    def on_entity_changed(self, entity):
        self.bind_entity(entity, self._update_progress, modify=False)
        self._update_progress()

    def _update_progress(self):
        progress = self._entity.get_cache_progress()
        if progress != self._cache_progress:
            if isinstance(progress, tuple):
                offset_tasks = {}
                offset_frame = state.get('offset_frame')
                for k, v in progress[1].items():
                    offset_tasks[k - offset_frame] = v
                self._tasks = offset_tasks

            self._cache_progress = progress
            self._update()

    def paintEvent(self, evt):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        hw = self._handle_width
        w -= hw

        h = self.height()

        if self.maximum() == 0:
            tw = 0
        else:
            tw = w / self.maximum()

        hh = self._bar_height

        painter.translate(hw / 2, 0)
        painter.fillRect(
            QRect(0, (h - hh) / 2, w, hh),
            self.palette().dark().color()
        )

        shot = state.get('current_shot')
        job = state.get('current_job')
        body_mode = state.get('body_mode')
        if shot is not None and body_mode is BodyMode.PLAYBACK:
            progress = self._cache_progress
            t_color = self.palette().midlight().color()
            c_color = QColor('#DB2A71')
            sf, ef = shot.frame_range

            closeup_camera = state.get('closeup_camera')
            progress_thumb = progress[CameraCacheType.THUMBNAIL]
            progress_origin = progress[CameraCacheType.ORIGINAL]
            is_closeup = closeup_camera and closeup_camera in progress_origin

            i = 0
            for f in range(sf, ef + 1):
                if f in progress_thumb:
                    alpha = progress_thumb[f]
                    if alpha > 1.0:
                        alpha = 1.0
                    t_color.setAlphaF(float(alpha))
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2, math.ceil(tw), hh),
                        t_color
                    )

                if is_closeup and f in progress_origin[closeup_camera]:
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2 - 2, math.ceil(tw), 2),
                        c_color
                    )

                i += 1
        elif job is not None and body_mode is BodyMode.MODEL:
            progress, tasks = self._cache_progress

            t_color = self.palette().midlight().color()

            i = 0
            for f in job.frames:
                if f in progress:
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2, math.ceil(tw), hh),
                        t_color
                    )
                elif f in tasks:
                    task_state = tasks[f]
                    painter.fillRect(
                        QRect(i * tw, (h - hh) / 2, math.ceil(tw), hh),
                        self._deadline_color[task_state]
                    )

                i += 1

        if state.get('Crop'):
            cw, ch, oh = self._crop_size
            sc, ec = state.get('crop_range')

            if sc is not None and ec is not None:
                painter.fillRect(
                    tw * sc, h - ch - oh,
                    tw * (ec - sc), ch / 2,
                    self.palette().base().color()
                )
            if sc is not None:
                painter.fillPath(
                    self._crop_path.translated(tw * sc - cw / 2, h - ch - oh),
                    self._crop_brush
                )
            if ec is not None:
                painter.fillPath(
                    self._crop_path.translated(tw * ec - cw / 2, h - ch - oh),
                    self._crop_brush
                )

        painter.translate(-hw / 2, 0)
        super().paintEvent(evt)

        frames = state.get('frames')
        fm = painter.fontMetrics()
        text = str(frames[self.value()])
        width = fm.width(text)
        x = self.value() * tw - width / 2 + hw / 2
        x_max_width = self.width() - width

        if x < 0:
            x = 0
        elif x > x_max_width:
            x = x_max_width

        painter.drawText(
            x, 0, width, 20,
            Qt.AlignCenter,
            text
        )


class PlaybackButton(ToolButton):
    def __init__(self, source):
        super().__init__(source=source)
        if source == 'play':
            state.on_changed('playing', self._update_source)
        elif source.startswith('clip'):
            self.setVisible(False)
            state.on_changed('Crop', self._update_crop_visible)

    def sizeHint(self):
        return QSize(26, 26)

    def _update_source(self):
        if state.get('playing'):
            self.change_source('pause')
        else:
            self.change_source('play')

    def _update_crop_visible(self):
        crop = state.get('Crop')
        self.setVisible(crop)
