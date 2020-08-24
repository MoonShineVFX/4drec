from PyQt5.Qt import (
    QDialog, Qt, QLabel, QDialogButtonBox, QLineEdit, QHBoxLayout,
    QSpinBox, QDoubleSpinBox, QComboBox
)

from utility.setting import setting

from master.ui.custom_widgets import move_center, make_layout, make_split_line
from master.ui.state import state, get_slider_range


class ShotSubmitDialog(QDialog):
    _default = '''
    QLabel {
      font-size: 14px;
    }

    QLineEdit {
      font-size: 18px;
      min-height: 30px;
      padding: 4px 16px;
    }

    QDialogButtonBox {
      min-height: 30px;
    }
    '''

    def __init__(self, parent):
        super().__init__(parent)
        self._text_name = None
        self._text_frames = None
        self._parms = []
        self._comboBox = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        shot = state.get('current_shot')
        self.setWindowTitle(f'Submit [{shot.name}]')

        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

        name_layout = make_layout(spacing=24)
        label = QLabel('Job Name')
        label.setAlignment(Qt.AlignCenter)
        name_layout.addWidget(label)

        name = f'resolve {len(shot.jobs) + 1}'
        self._text_name = QLineEdit()
        self._text_name.setAlignment(Qt.AlignRight)
        self._text_name.setText(name)
        self._text_name.setPlaceholderText('Submit Job Name')
        name_layout.addWidget(self._text_name)

        layout.addLayout(name_layout)

        # --------------
        layout.addWidget(make_split_line())

        label = QLabel(
            'Frame Range (seperate by comma, space or dash)'
        )
        layout.addWidget(label)

        min_slider_value, max_slider_value = get_slider_range()
        self._text_frames = QLineEdit()
        self._text_frames.setAlignment(Qt.AlignCenter)
        self._text_frames.setText(f'{min_slider_value}-{max_slider_value}')
        self._text_frames.setPlaceholderText(
            '1-101 or 1 2 3 or 1,2,3 or 1 3,4,6-9'
        )
        layout.addWidget(self._text_frames)

        hlayout = make_layout(
            horizon=True,
            margin=0,
            spacing=24
        )
        label = QLabel('Calibration')
        hlayout.addWidget(label)

        self._comboBox = CalibrationComboBox()
        hlayout.addWidget(self._comboBox)

        layout.addLayout(hlayout)

        # --------------
        layout.addWidget(make_split_line())

        for parm in setting.submit_parameters:
            parm_widget = ShotSubmitParameter(parm)
            layout.addLayout(parm_widget)
            self._parms.append(parm_widget)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self._buttons = QDialogButtonBox(buttons)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setLayout(layout)
        move_center(self)

    def showEvent(self, event):
        event.accept()

    def closeEvent(self, event):
        event.accept()

    def get_result(self):
        frames = []
        offset_frame = state.get('offset_frame')

        for s1 in self._text_frames.text().strip().split():
            for s2 in s1.split(','):
                if s2 == '' or s2 is None:
                    continue
                if '-' in s2:
                    sf, ef = s2.split('-')
                    frames += [i for i in range(int(sf), int(ef) + 1)]
                else:
                    frames.append(int(s2))

        frames.sort()
        frames = set(frames)
        frames = [f + offset_frame for f in frames]

        parms = {'cali': self._comboBox.currentData()}
        for parm_widget in self._parms:
            parm = parm_widget.get_parm()

            value = parm[1]

            parms[parm[0]] = value

        return {
            'name': self._text_name.text(),
            'frames': frames,
            'parms': parms
        }


class ShotSubmitParameter(QHBoxLayout):
    def __init__(self, parm):
        super().__init__()
        self._parm = parm
        self._spin = None
        self._setup_ui()

    def _setup_ui(self):
        label = QLabel(self._parm['desc'])
        self.addWidget(label)

        if self._parm['type'] == 'int':
            self._spin = QSpinBox()
        else:
            self._spin = QDoubleSpinBox()
            self._spin.setDecimals(1)
            self._spin.setSingleStep(0.1)

        self._spin.setMinimum(self._parm['min'])
        self._spin.setMaximum(self._parm['max'])
        self._spin.setValue(self._parm['default'])

        self._spin.setFixedWidth(100)
        self._spin.setAlignment(Qt.AlignRight)
        self.addWidget(self._spin)

    def get_parm(self):
        return (self._parm['name'], self._spin.value())


class CalibrationComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        state.on_changed('cali_list', self._update)
        state.cast('project', 'update_cali_list')

    def _update(self):
        cali_list = state.get('cali_list')
        self.clear()

        for label, job_id in cali_list:
            self.addItem(label, job_id)

        if len(cali_list) == 0:
            self.addItem('None', None)
