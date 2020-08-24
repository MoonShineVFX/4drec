from PyQt5.Qt import QLabel, Qt, QApplication

from master.ui.state import state, EntityBinder
from master.ui.resource import icons
from master.ui.custom_widgets import LayoutWidget, ElideLabel


class JobList(LayoutWidget):
    def __init__(self, jobs):
        super().__init__(horizon=False, spacing=8)
        self._jobs = jobs
        self._setup_ui()

    def _setup_ui(self):
        for job in self._jobs:
            self.addWidget(JobItem(job))

    def showEvent(self, event):
        job = state.get('current_job')
        if job not in self._jobs:
            state.cast('project', 'select_job', self._jobs[0])


class JobItem(LayoutWidget, EntityBinder):
    _default = '''
    JobItem {
        background-color: palette(window);
        border-radius: 5px;
        margin: 0px 8px;
    }

    QLabel {
        font-size: 14px;
    }
    '''
    _hover = '''
    JobItem {
        border: 1px solid palette(midlight);
    }
    '''

    def __init__(self, job):
        super().__init__(margin=(16, 4, 16, 4), spacing=16)
        self._job = job
        self._state_label = None
        self._name_label = None
        self._frame_label = None
        self._is_current = None

        self._setup_ui()
        self.bind_entity(job, self._apply_data)
        state.on_changed('current_job', self._update)

    def _setup_ui(self):
        self.setStyleSheet(self._default)

        self._state_label = QLabel()
        self._name_label = ElideLabel()
        self._name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._frame_label = QLabel()

        self.addWidget(self._state_label)
        self.addWidget(self._name_label)
        self.layout().addStretch(0)
        self.addWidget(self._frame_label)

        self._apply_data()

    def _apply_data(self):
        self._state_label.setPixmap(
            icons.get(f'state_{self._job.state + 2}')
        )
        self._name_label.setText(self._job.name)

        frame_count = str(len(self._job.frames))
        completed_count = self._job.get_completed_count()
        self._frame_label.setText(f'{completed_count} ({frame_count})')

    def _update(self):
        current_job = state.get('current_job')
        if current_job == self._job:
            if self._is_current is not True:
                self._is_current = True

            self.setStyleSheet(self._default + self._hover)
        else:
            self._is_current = False
            self.setStyleSheet(self._default)

    def enterEvent(self, event):
        if not self._is_current:
            QApplication.setOverrideCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        QApplication.restoreOverrideCursor()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_select = state.get('current_job')
            if current_select != self._job:
                state.cast('project', 'select_job', self._job)
