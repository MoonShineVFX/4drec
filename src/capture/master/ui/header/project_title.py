from PyQt5.Qt import Qt, QLabel, QApplication

from master.ui.state import state, EntityBinder


class ProjectTitle(QLabel, EntityBinder):
    _default = '''
        font-size: 30px;
        color: palette(bright-text);
        border: none;
        border-right: 1px solid palette(dark);
        padding: 0px 16px;
    '''

    _hover = '''
        color: palette(highlight);
        background-color: palette(window);
    '''

    def __init__(self):
        super().__init__()
        state.on_changed('current_project', self._update)
        self._setup_ui()

    def _update(self):
        current_project = state.get('current_project')
        self.bind_entity(current_project, self._apply_data)
        self._apply_data()

    def _apply_data(self):
        if self._entity is not None:
            self.setText(self._entity.name)
        else:
            self.setText('Load Project ...')

    def _setup_ui(self):
        self.setStyleSheet(self._default)

    def enterEvent(self, event):
        self.setStyleSheet(self._default + self._hover)
        QApplication.setOverrideCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self.setStyleSheet(self._default)
        QApplication.restoreOverrideCursor()

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.LeftButton
        ):
            self.leaveEvent(None)
            state.set('project_list_dialog', True)
