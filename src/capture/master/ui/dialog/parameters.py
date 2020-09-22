from PyQt5.Qt import (
    QDialog, QLabel, QDialogButtonBox, QLayout, QScrollArea,
    QWidget, QVBoxLayout, Qt
)

from master.ui.custom_widgets import move_center, make_layout, make_split_line
from master.ui.state import state


class CameraParametersDialog(QDialog):
    _default = '''
    QLabel {
      font-size: 14px;
    }

    QDialogButtonBox {
      min-height: 30px;
    }
    
    QScrollArea {
        min-height: 400px;
        min-width: 400px;
    }
    '''

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        shot = state.get('current_shot')
        job = state.get('current_job')

        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

        # shot parms
        if job is None:
            self.setWindowTitle(f'[{shot.name}] Camera Parameters')
            if isinstance(shot.camera_parameters, dict):
                for key, value in shot.camera_parameters.items():
                    parm_layout = make_layout(spacing=48)
                    name_label = QLabel(f'{key}:')
                    if isinstance(value, float):
                        value = f'{value:.2f}'
                    else:
                        value = str(value)
                    value_label = QLabel(value)

                    parm_layout.addWidget(name_label)
                    parm_layout.addStretch(0)
                    parm_layout.addWidget(value_label)

                    layout.addLayout(parm_layout)
        # job parms
        else:
            self.setWindowTitle(f'[{job.name}] Submit Parameters')

            submit_widget = QWidget()
            submit_control = make_layout(
                horizon=False, spacing=8, margin=24
            )

            for key, value in job.parameters.items():
                widgets = convert_submit_parm_widgets(key, value, 0)
                for widget in widgets:
                    if isinstance(widget, QLayout):
                        submit_control.addLayout(widget)
                    else:
                        submit_control.addWidget(widget)

            scroll = QScrollArea()
            scroll.setWidgetResizable(False)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            submit_widget.setLayout(submit_control)
            scroll.setWidget(submit_widget)
            layout.addWidget(scroll)

        buttons = QDialogButtonBox.Ok
        self._buttons = QDialogButtonBox(buttons)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setLayout(layout)
        move_center(self)


def convert_submit_parm_widgets(key, value, layer):
    widgets = []
    parm_layout = make_layout(
        spacing=30,
        margin=(layer * 24, 24 if layer == 0 else 0, 0, 0)
    )

    if key is None:
        return convert_submit_parm_widgets(value[0], value[1], layer)
    if isinstance(value, dict):
        parm_layout.addWidget(
            QLabel(f'{key}:')
        )
        widgets.append(parm_layout)
        for k, v in value.items():
            widgets += convert_submit_parm_widgets(k, v, layer + 1)
        return widgets
    elif isinstance(value, list):
        parm_layout.addWidget(
            QLabel(f'{key}:')
        )
        widgets.append(parm_layout)
        for l in value:
            widgets += convert_submit_parm_widgets(None, l, layer + 1)
        return widgets

    name_label = QLabel(f'{key}:')
    if isinstance(value, float):
        value = f'{value}'
    else:
        value = str(value)
    value_label = QLabel(value)

    parm_layout.addWidget(name_label)
    parm_layout.addStretch(0)
    parm_layout.addWidget(value_label)

    return [parm_layout]
