from PyQt5.Qt import (
    QDialog, QLabel, QDialogButtonBox
)

from master.ui.custom_widgets import move_center, make_layout
from master.ui.state import state


class CameraParametersDialog(QDialog):
    _default = '''
    QLabel {
      font-size: 14px;
    }

    QDialogButtonBox {
      min-height: 30px;
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
        # else:
        #     self.setWindowTitle(f'[{job.name}] Submit Parameters')
        #     for key, value in job.parameters:
        #         if


        buttons = QDialogButtonBox.Ok
        self._buttons = QDialogButtonBox(buttons)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setLayout(layout)
        move_center(self)

# TODO: show parameters

# def convert_submit_parm_widgets(key, value, layer):
#     widgets = []
#     parm_layout = make_layout(
#         spacing=48,
#         margin=(layer * 8, 0, 0, 0)
#     )
#
#     if key is None:
#
#     if isinstance(value, dict):
#         widgets.append(QLabel(f'{key}:'))
#         for k, v in value.items():
#             widgets += convert_submit_parm_widgets(k, v, layer + 1)
#         return widgets
#     elif isinstance(value, list):
#         widgets.append(QLabel(f'{key}:'))
#         for l in value:
#             widgets += convert_submit_parm_widgets(None, l, layer + 1)
#         return widgets