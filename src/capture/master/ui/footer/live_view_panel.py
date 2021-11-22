from PyQt5.Qt import (
    QHBoxLayout, QGridLayout, Qt, QLabel, QSlider, QIcon, QPushButton
)
from functools import partial

from utility.setting import setting

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.resource import icons
from master.ui.state import state

from .support_button import SupportButtonGroup


class LiveViewPanel(LayoutWidget):
    def __init__(self):
        super().__init__(spacing=36, margin=(0, 0, 0, 0))
        self._setup_ui()

    def _setup_ui(self):
        self.addLayout(
            SupportButtonGroup(('Serial', 'Calibrate', 'Focus'))
        )
        self.addLayout(ParameterFields())
        self.addWidget(RecordButton())


class RecordButton(PushButton):
    def __init__(self):
        super().__init__('  Streaming', 'record', (180, 60))
        self._is_recording = False
        self.setEnabled(False)
        state.on_changed('recording', self._update)
        state.on_changed('status', self._update)
        state.on_changed('has_arduino', self._update)
        self.clicked.connect(self._record)

    def _record(self):
        state.cast('camera', 'record')

    def _update(self):
        recording = state.get('recording')
        shot = state.get('current_shot')

        if recording:
            frames = state.get('status')['frames']
            self.setText(f'  {frames}')

        if not self._is_recording and recording:
            self.setIcon(QIcon(icons.get('record_red')))
            self._is_recording = True

        if self._is_recording and not recording:
            self.setText('  RECORD')
            self.setIcon(QIcon(icons.get('record')))

        if shot is None or shot.state > 0:
            self.setEnabled(False)
        elif state.get('has_arduino'):
            self.setEnabled(True)
        else:
            self.setEnabled(False)


class ParameterFields(QGridLayout):
    _grid_pos = {
        'ExposureTime': (0, 0),
        'Gamma': (0, 2),
        'Gain': (1, 0),
        'BalanceRatioRed': (0, 1),
        'BalanceRatioBlue': (1, 1)
    }

    def __init__(self):
        super().__init__()
        self._parameters = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setHorizontalSpacing(16)
        self.setVerticalSpacing(8)

        for key, parm in setting.camera_parameters.items():
            self._parameters[key] = ParameterBar(
                key,
                parm['min'],
                parm['max'],
                parm['type'],
                parm['tick']
            )
            self.addLayout(self._parameters[key], *self._grid_pos[key])

        self.addLayout(PresetButtons(), 1, 2)


class ParameterBar(QHBoxLayout):
    def __init__(self, name, vmin, vmax, _type, tick):
        super().__init__()
        self._name = name
        self._vmin = vmin
        self._vmax = vmax
        self._type = _type
        self._tick = tick
        self._length = self._get_interval_length()
        self._label = None
        self._slider = None

        state.set('parm_outside', True)
        self._setup_ui()
        state.on_changed(self._name, self._update)
        state.set('parm_outside', False)

    def _setup_ui(self):
        self.setSpacing(12)
        self.setAlignment(Qt.AlignCenter)

        if 'BalanceRatio' in self._name:
            icon_path = 'wb'
        else:
            icon_path = self._name.lower()

        # icon
        label = QLabel()
        label.setToolTip(self._name)
        label.setPixmap(icons.get(icon_path))
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setFixedWidth(45)

        self.addWidget(label)

        # slider
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(self._length)
        if icon_path == 'wb':
            self._slider.setObjectName(self._name)
        self._slider.valueChanged.connect(self._on_slider_changed)

        self.addWidget(self._slider)

        # value
        self._label = QLabel()
        self._label.setContentsMargins(0, 0, 0, 4)
        self._label.setFixedWidth(45)
        self.addWidget(self._label)

        self._update()

    def _get_interval_length(self):
        return int((self._vmax - self._vmin) / self._tick) + 1

    def _on_slider_changed(self, value):
        if not state.get('parm_outside'):
            v = self._vmin + (self._vmax - self._vmin) * value / self._length
            state.cast('camera', 'change_parameter', self._name, v)

    def _update(self):
        value = state.get(self._name)
        if self._type == 'int':
            text = str(int(value))
        elif value == 0:
            text = '0'
        else:
            text = f'{value:.02f}'.rstrip('0.')

        self._label.setText(text)

        if state.get('parm_outside'):
            v = (value - self._vmin) / (self._vmax - self._vmin) * self._length
            self._slider.setValue(int(v))


class PresetButtons(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        self.setSpacing(8)
        self.setContentsMargins(16, 0, 16, 0)
        for name in ('Base', 'User', 'Save'):
            button = QPushButton(name)
            button.setFixedSize(50, 25)
            button.clicked.connect(partial(self._on_click, name))
            self.addWidget(button)

    def _on_click(self, preset_type):
        if preset_type == 'Base':
            state.cast('camera', 'load_parameters', 'Base')
        elif preset_type == 'User':
            state.cast('camera', 'load_parameters', 'User')
        elif preset_type == 'Save':
            state.cast('camera', 'save_parameters')