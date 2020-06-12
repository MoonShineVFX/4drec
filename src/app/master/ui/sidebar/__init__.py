from PyQt5.Qt import QScrollArea, Qt

from master.ui.state import state
from master.ui.custom_widgets import LayoutWidget
from master.ui.popup import popup

from .shot_list import ShotList


class Sidebar(LayoutWidget):
    _default = '''
    Sidebar {
        background-color: qlineargradient(
            x1:0, y1:0, x2:0, y2:0.01,
            stop: 0 palette(alternate-base), stop: 1 palette(window)
        );
        border-right: 1px solid palette(dark);
    }
    QScrollArea {
        background-color: transparent;
    }
    '''

    def __init__(self):
        super().__init__()
        state.on_changed('shot_new_dialog', self._new_shot)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setFixedWidth(300)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(ShotList())

        self.addWidget(scroll)

    def _new_shot(self):
        if state.get('shot_new_dialog'):
            is_cali = state.get('is_cali')
            shot_type = 'cali' if is_cali else 'shot'

            result = popup(
                None,
                f'Create New {shot_type.title()}',
                f"Please input new {shot_type}'s name (optional)",
                f'{shot_type.title()} Name'
            )

            if result is not False:
                project = state.get('current_project')
                project.create_shot(is_cali, result)
                state.set('shot_new_dialog', False)
