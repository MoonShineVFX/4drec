from PyQt5.Qt import (
    QDialog, Qt, QLabel, QDialogButtonBox, QLineEdit, QHBoxLayout, QWidget,
    QSpinBox, QDoubleSpinBox, QComboBox, QGroupBox, QScrollArea, QVBoxLayout
)

from utility.setting import setting

from master.ui.custom_widgets import (
    move_center, make_layout, make_split_line
)
from master.ui.state import state, get_slider_range


def create_submit_parameter_widget(parm_name, parm_value, layer):
    if layer > 0 or isinstance(parm_value, list):
        return ShotSubmitContainer(parm_name, parm_value, layer)
    return ShotSubmitParameter(parm_name, parm_value)


class HeaderLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HeaderLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ShotSubmitDialog(QDialog):
    _default = '''
    HeaderLabel {
      font-size: 14px;
    }

    HeaderLineEdit {
      font-size: 18px;
      min-height: 30px;
      padding: 4px 16px;
    }

    QDialogButtonBox {
      min-height: 30px;
    }
    
    QScrollArea {
        min-height: 180px;
    }
    
    QGroupBox {
        font-weight: 600;
    }
    QGroupBox:title {
        subcontrol-origin: margin;
        subcontrol-position: top;
        padding: 0px 8px 0px 4px;
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
        label = HeaderLabel('Job Name')
        label.setAlignment(Qt.AlignCenter)
        name_layout.addWidget(label)

        name = f'resolve {len(shot.jobs) + 1}'
        self._text_name = HeaderLineEdit()
        self._text_name.setAlignment(Qt.AlignRight)
        self._text_name.setText(name)
        self._text_name.setPlaceholderText('Submit Job Name')
        name_layout.addWidget(self._text_name)

        layout.addLayout(name_layout)

        # --------------
        layout.addWidget(make_split_line())

        label = HeaderLabel(
            'Frame Range (seperate by comma, space or dash)'
        )
        layout.addWidget(label)

        min_slider_value, max_slider_value = get_slider_range()
        self._text_frames = HeaderLineEdit()
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
        label = HeaderLabel('Calibration')
        hlayout.addWidget(label)

        self._comboBox = CalibrationComboBox()
        hlayout.addWidget(self._comboBox)

        layout.addLayout(hlayout)

        # submit parameter
        submit_widget = QWidget()
        submit_control = QVBoxLayout()
        submit_meta = {
            'reference': 1,
            'clip_range': 1,
            'mesh_reduce_ratio': 0,
            'flows': 2
        }
        for parm_name, layer in submit_meta.items():
            parm_value = setting.resolve[parm_name]
            parm_widget = create_submit_parameter_widget(
                parm_name, parm_value, layer
            )
            if isinstance(parm_widget, ShotSubmitContainer):
                submit_control.addWidget(parm_widget)
            else:
                submit_control.addLayout(parm_widget)
            self._parms.append(parm_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        submit_widget.setLayout(submit_control)
        scroll.setWidget(submit_widget)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self._buttons = QDialogButtonBox(buttons)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setLayout(layout)

        self.setMinimumSize(580, 710)
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
            name, value = parm_widget.get_result()
            parms[name] = value

        return {
            'name': self._text_name.text(),
            'frames': frames,
            'parms': parms
        }


class ShotSubmitContainer(QGroupBox):
    def __init__(self, parm_name, parm_value, layer):
        super().__init__(parm_name)
        self._parm_name = parm_name
        self._parm_value = parm_value
        self._layer = layer

        if isinstance(parm_value, dict):
            self._children = [
                create_submit_parameter_widget(p_name, p_value, layer - 1)
                for p_name, p_value in parm_value.items()
            ]
        elif isinstance(parm_value, list):
            self._children = [
                ShotSubmitParameter(None, p_value)
                for p_value in parm_value
            ]

        self._setup_ui()

    def _setup_ui(self):
        layout = make_layout(
            horizon=False, margin=8
        )

        for child in self._children:
            if isinstance(child, ShotSubmitContainer):
                layout.addWidget(child)
            else:
                layout.addLayout(child)
        self.setLayout(layout)

    def get_result(self):
        if isinstance(self._parm_value, list):
            return self._parm_name, [child.get_result() for child in self._children]
        return self._parm_name, {
                name: value
                for name, value in
                [child.get_result() for child in self._children]
            }


class ShotSubmitParameter(QHBoxLayout):
    def __init__(self, parm_name, parm_value):
        super().__init__()
        self._parm_name = parm_name
        self._parm_value = parm_value
        self._input_widget = None
        self._setup_ui()
        
    def _create_widget(self, value):
        if isinstance(value, str):
            widget = QLineEdit()
            widget.setText(value)
            widget.setPlaceholderText('String Val')
        elif isinstance(value, list):
            return [
                self._create_widget(v)
                for v in value
            ]
        else:
            if isinstance(value, int):
                widget = QSpinBox()
            else:
                widget = QDoubleSpinBox()
                decimal = str(value)[::-1].find('.')
                widget.setDecimals(decimal)
                widget.setSingleStep(pow(10, -decimal))

            widget.setMinimum(-9999999)
            widget.setMaximum(9999999)
            widget.setValue(value)

        widget.setFixedWidth(100)
        widget.setAlignment(Qt.AlignRight)
        return widget

    def _get_widget_value(self, widget):
        if isinstance(widget, list):
            return [self._get_widget_value(w) for w in widget]
        if isinstance(widget, QLineEdit):
            return widget.text()
        return widget.value()
        
    def _setup_ui(self):
        margin = 8
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(8)
        if self._parm_name is not None:
            label = QLabel(self._parm_name)
            self.addWidget(label)
        else:
            self.addStretch(1)
        
        self._input_widget = self._create_widget(self._parm_value)

        if isinstance(self._input_widget, list):
            for widget in self._input_widget:
                self.addWidget(widget)
        else:
            self.addWidget(self._input_widget)

    def get_result(self):
        value = self._get_widget_value(self._input_widget)
        if isinstance(value, list):
            return value
        return self._parm_name, value


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
