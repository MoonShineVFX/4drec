from utility.define import BodyMode

from master.ui.state import state
from master.ui.custom_widgets import LayoutWidget, make_layout

from .live_view_panel import LiveViewPanel
from .roll_panel import RollPanel
from .playback_control import PlaybackControl
from .model_panel import ModelPanel


class Footer(LayoutWidget):
    _default = '''
    Footer {
        background-color: palette(window);
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }
    '''

    def __init__(self):
        super().__init__(margin=(32, 16, 32, 16))
        self._widgets = []
        self._setup_ui()
        state.on_changed('body_mode', self._update)

    def _update(self):
        body_mode = state.get('body_mode')

        if body_mode is BodyMode.LIVEVIEW:
            self._layout.setCurrentIndex(0)
        elif body_mode is BodyMode.PLAYBACK:
            self._layout.setCurrentIndex(1)
        elif body_mode is BodyMode.MODEL:
            self._layout.setCurrentIndex(2)

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setFixedHeight(120)

        self._layout = make_layout(stack=True)

        playback_control = PlaybackControl()
        self._layout.addWidget(LiveViewPanel())
        self._layout.addWidget(RollPanel(playback_control))
        self._layout.addWidget(ModelPanel(playback_control))

        self.addLayout(self._layout)

        self._update()
