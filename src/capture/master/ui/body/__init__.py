from PyQt5.Qt import QStackedLayout

from utility.define import BodyMode

from master.ui.state import state

from .model_view import ModelView
from .camera_view import CameraViewLayout


class Body(QStackedLayout):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        state.on_changed('body_mode', self._update)
        state.on_changed('trigger', self._update)
        state.on_changed('live_view_size', self._update)
        state.on_changed('closeup_camera', self._update)

    def _update(self):
        body_mode = state.get('body_mode')

        if body_mode is BodyMode.MODEL:
            self.layout().setCurrentIndex(1)
        else:
            self.layout().setCurrentIndex(0)

        if body_mode is BodyMode.LIVEVIEW:
            state.cast('camera', 'offline')

            trigger = state.get('trigger')
            if trigger:
                state.cast(
                    'camera', 'live_view', True,
                    scale_length=state.get('live_view_size'),
                    close_up=state.get('closeup_camera')
                )
        elif state.get('live_view'):
            state.cast('camera', 'live_view', False)

    def _setup_ui(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

        self.addWidget(CameraViewLayout())
        self.addWidget(ModelView())

        self._update()
