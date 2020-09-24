from PyQt5.Qt import QLabel, QWidget, Qt

from utility.define import BodyMode
from utility.fps_counter import FPScounter

from master.ui.state import state, get_real_frame

from .opengl_core import OpenGLCore


class ModelView(QWidget):
    _offset_parm_value = 0.1

    def __init__(self):
        super().__init__()

        self._interface = ModelInterface()
        self._core = OpenGLCore(self, self._interface)
        self._interface.setParent(self)
        self._cache = {}

        self._fps_counter = FPScounter(self._interface.update_fps)

        state.on_changed('opengl_data', self._update_geo)
        state.on_changed('Rig', self._update_rig)
        state.on_changed('Wireframe', self._update_shader)
        state.on_changed('key', self._on_key_pressed)

        state.on_changed('current_job', self._get_rig_geo)
        state.on_changed('body_mode', self._get_rig_geo)

    def resizeEvent(self, event):
        self._core.setFixedSize(event.size())

    def _update_shader(self):
        self._core.toggle_wireframe(state.get('Wireframe'))

    def _update_rig(self):
        self._core.toggle_rig(state.get('Rig'))

    def _update_geo(self):
        if state.get('caching'):
            return
        self._core.set_geo(state.get('opengl_data'))
        self._fps_counter.tick()

    def _on_key_pressed(self):
        key = state.get('key')
        if key == Qt.Key_Z:
            self._core.reset_camera_transform()
        elif key == Qt.Key_Q:
            self._core.offset_model_shader('gamma', -self._offset_parm_value)
        elif key == Qt.Key_E:
            self._core.offset_model_shader('gamma', self._offset_parm_value)
        elif key == Qt.Key_A:
            self._core.offset_model_shader('saturate', -self._offset_parm_value)
        elif key == Qt.Key_D:
            self._core.offset_model_shader('saturate', self._offset_parm_value)
        elif key == Qt.Key_S:
            self._core.offset_model_shader('exposure', self._offset_parm_value)
        elif key == Qt.Key_X:
            self._core.offset_model_shader('exposure', -self._offset_parm_value)

    def _get_rig_geo(self):
        job = state.get('current_job')
        body_mode = state.get('body_mode')
        if job is None or body_mode is not BodyMode.MODEL:
            return

        state.cast(
            'resolve', 'request_geometry', job, None
        )


class ModelInterface(QLabel):
    _default = '''
        font-size: 13;
        color: palette(window-text);
        min-width: 200px;
        min-height: 330px;
    '''

    def __init__(self):
        super().__init__()
        self._vertex_count = 0
        self._shader_parms = OpenGLCore._default_shader_parms.copy()
        self._real_frame = -1
        self._fps = 0

        self._setup_ui()
        state.on_changed('current_slider_value', self._update_real_frame)

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.move(24, 16)
        self.setAlignment(Qt.AlignTop)

    def update_vertex_count(self, data):
        self._vertex_count = data
        self._update()

    def update_parm(self, parm_name, value):
        self._shader_parms[parm_name] = value
        self._update()

    def update_sat(self, value):
        self._saturate = value
        self._update()

    def update_fps(self, fps):
        self._fps = fps
        self._update()

    def _update_real_frame(self):
        slider_value = state.get('current_slider_value')
        self._real_frame = get_real_frame(slider_value)
        self._update()

    def _update(self):
        text = (
            f'Vertices:  {self._vertex_count}\n' +
            f'Real Frame:  {self._real_frame}\n' +
            '\n'.join([f'{k}: {v:.2f}' for k, v in self._shader_parms.items()]) +
            '\n\n' +
            '[Q/E]  Gamma Offset\n' +
            '[A/D]  Saturate Offset\n' +
            '[S/X]  Exposure Offset\n' +
            '[W]  Toggle Wireframe\n' +
            '[C]  Cache All Frames\n' +
            '[Z]  Reset Camera'
        )

        if state.get('playing'):
            text += f'\n\nfps: {self._fps}'

        self.setText(text)
