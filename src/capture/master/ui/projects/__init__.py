from PyQt5.Qt import QDialog

from master.ui.custom_widgets import make_layout, move_center
from master.ui.popup import popup
from master.ui.state import state

from .project_list import ProjectList, ProjectListButtonGroup


class ProjectListDialog(QDialog):
    _width = 465
    _height = 700

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Open Project')
        state.set('project_list_select', None)
        state.on_changed('project_list_dialog', self._update)
        state.on_changed('project_new_dialog', self._new_project)

        self._setup_ui()

    def _update(self):
        if not state.get('project_list_dialog'):
            self.close()

    def _setup_ui(self):
        layout = make_layout(horizon=False)

        layout.addWidget(ProjectList())
        layout.addWidget(ProjectListButtonGroup())

        self.setLayout(layout)

        self.setFixedSize(self._width, self._height)
        move_center(self)

    def _new_project(self):
        if state.get('project_new_dialog'):
            result = popup(
                self,
                'Create New Project',
                "Please input new project's name",
                'Project Name'
            )
            if result:
                state.cast('project', 'create_project', result)
            state.set('project_new_dialog', False)

    def _move_center(self):
        parent = self.parentWidget()
        center = parent.geometry().center()

        self.setGeometry(
            center.x() - self._width / 2,
            center.y() - self._height / 2,
            self._width, self._height
        )
