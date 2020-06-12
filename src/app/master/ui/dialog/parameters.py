from PyQt5.Qt import (
    QDialog, Qt, QLabel, QDialogButtonBox, QLineEdit, QHBoxLayout,
    QSpinBox, QDoubleSpinBox
)

from utility.setting import setting

from master.ui.custom_widgets import move_center, make_layout, make_split_line
from master.ui.state import state, get_slider_range


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
        self.setWindowTitle(f'[{shot.name}] Camera Parameters')

        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

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

        buttons = QDialogButtonBox.Ok
        self._buttons = QDialogButtonBox(buttons)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.setLayout(layout)
        move_center(self)
