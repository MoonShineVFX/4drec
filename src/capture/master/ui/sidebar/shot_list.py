from PyQt5.Qt import (
    Qt, QIcon, QAction, QApplication,
    QLabel, QMenu, QPushButton
)

from utility.define import BodyMode

from master.ui.state import state, EntityBinder
from master.ui.custom_widgets import (
    LayoutWidget, make_layout, make_split_line, ElideLabel
)
from master.ui.resource import icons
from master.ui.popup import popup
from master.ui.dialog import CameraParametersDialog

from .job_list import JobList


class ShotList(LayoutWidget):
    _default = '''ShotList {
      background-color: transparent;
    }
    '''

    def __init__(self):
        super().__init__(horizon=False, spacing=16, alignment=Qt.AlignTop)
        self._shot_widgets = {}
        state.on_changed('shots', self._update)
        self._setup_ui()

    def _update(self):
        shots = state.get('shots')
        new_shot_ids = []

        for order, shot in enumerate(shots):
            shot_id = shot.get_id()
            if shot_id not in self._shot_widgets:
                widget = ShotItem(shot)
                self.layout().insertWidget(order + 1, widget)
                self._shot_widgets[shot_id] = widget

            new_shot_ids.append(shot_id)

        deleted_widgets = [
            widget for widget in self._shot_widgets.values()
            if widget.get_shot_id() not in new_shot_ids
        ]

        for widget in deleted_widgets:
            shot_id = widget.get_shot_id()
            self.layout().removeWidget(widget)
            widget.deleteLater()
            del self._shot_widgets[shot_id]

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setFixedWidth(290)

        layout = make_layout(
            alignment=Qt.AlignHCenter,
            margin=(0, 24, 0, 8),
            spacing=16
        )
        shot_button = AddButton(' Shot')
        shot_button.clicked.connect(lambda: self._new_dialog())
        cali_button = AddButton(' Cali')
        cali_button.clicked.connect(lambda: self._new_dialog(True))
        layout.addWidget(shot_button)
        layout.addWidget(cali_button)
        self.addLayout(layout)

        self._update()

    def _new_dialog(self, is_cali=False):
        state.set('is_cali', is_cali)
        state.set('shot_new_dialog', True)


class AddButton(QPushButton):
    _default = '''
        background-color: palette(base);
        border-radius: 18px;
        font-size: 16px;
    '''
    _hover = '''
        color: palette(highlight);
    '''

    def __init__(self, name):
        super().__init__(name)
        self._icon = None
        self._hover_icon = None
        state.on_changed('current_project', self._update)
        self._setup_ui()

    def _update(self):
        current_project = state.get('current_project')
        self.setVisible(current_project is not None)

    def _setup_ui(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(self._default)
        self.setFixedSize(102, 36)

        self._icon = QIcon(icons.get('add'))
        self._hover_icon = QIcon(icons.get('add_hl'))
        self.setIcon(self._icon)

    def enterEvent(self, event):
        self.setIcon(self._hover_icon)
        self.setStyleSheet(self._default + self._hover)
        QApplication.setOverrideCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        self.setIcon(self._icon)
        self.setStyleSheet(self._default)
        QApplication.restoreOverrideCursor()


class ShotItem(LayoutWidget, EntityBinder):
    _default = '''
    ShotItem {
        border-radius: 5px;
        margin: 0px 8px;
    }
    '''
    _base = '''
    ShotItem {
        background-color: palette(base);
    }
    '''
    _cali = '''
    ShotItem {
        background-color: #474538;
    }
    '''
    _hover = '''
    ShotItem {
        border: 2px solid palette(midlight);
    }
    '''
    _state_text = (
        'Created',
        'Recorded',
        'Submitted'
    )
    _field_info_list = ('frame_range', 'size', 'state')

    def __init__(self, shot):
        super().__init__(
            horizon=False,
            margin=(8, 12, 8, 12),
            spacing=16
        )
        self._shot = shot
        self._job_list = None
        self._menu = None
        self._name_label = None
        self._state_label = None
        self._is_current = False
        self._field_info_labels = []

        self.bind_entity(shot, self._apply_data)
        state.on_changed('current_shot', self._update)
        state.on_changed('current_shot', self._update_shot_list)
        state.on_changed('body_mode', self._update_shot_list)
        self._setup_ui()

    def _update(self):
        current_shot = state.get('current_shot')
        bg_style = self._cali if self._shot.is_cali() else self._base
        if current_shot == self._shot:
            if self._is_current is not True:
                self._is_current = True

            self.setStyleSheet(self._default + bg_style + self._hover)
        else:
            self._is_current = False
            self.setStyleSheet(self._default + bg_style)

    def _update_shot_list(self):
        current_shot = state.get('current_shot')
        body_mode = state.get('body_mode')
        if (
            body_mode is BodyMode.MODEL and
            current_shot == self._shot and
            len(self._shot.jobs) > 0
        ):
            if self._job_list is None:
                self._job_list = JobList(self._shot._jobs)
                self.addWidget(self._job_list)
        else:
            if self._job_list is not None:
                self._job_list.deleteLater()
                self._job_list = None
                state.cast('project', 'select_job', None)

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self._menu = self._build_menu()

        # top
        top_layout = make_layout(
            alignment=Qt.AlignVCenter,
            margin=(12, 0, 12, 0),
            spacing=8
        )
        self._name_label = ElideLabel()
        self._name_label.setStyleSheet(
            'font-size: 18px; color: palette(light)'
        )
        self._state_label = QLabel()
        top_layout.addWidget(self._name_label)
        top_layout.addStretch()
        top_layout.addWidget(self._state_label)

        # bottom
        bottom_layout = make_layout()
        for i in range(len(self._field_info_list)):
            layout = make_layout(alignment=Qt.AlignVCenter)
            label = QLabel()
            label.setStyleSheet('font-size: 12px')
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            bottom_layout.addLayout(layout)
            if i != len(self._field_info_list) - 1:
                bottom_layout.addWidget(make_split_line(vertical=True))
            self._field_info_labels.append(label)

        self.addLayout(top_layout)
        self.addLayout(bottom_layout)
        self._apply_data()
        self._update()

    def _apply_data(self):
        self._name_label.setText(self._shot.name)

        if self._shot.state > 0:
            self._state_label.setPixmap(
                icons.get(f'state_{self._get_state_index()}')
            )
            self._state_label.show()
        else:
            self._state_label.hide()

        for field, label in zip(
            self._field_info_list, self._field_info_labels
        ):
            label.setText(self._get_shot_info(field))

        self._update_shot_list()

    def _get_shot_info(self, field):
        if field == 'frame_range' and self._shot.is_cali():
            return 'Calibrate'
        if getattr(self._shot, field) is None:
            return '---'
        if field == 'frame_range':
            frame_range = self._shot.frame_range
            return f'{frame_range[1] - frame_range[0] + 1}F'
        if field == 'size':
            size = self._shot.size / 1024 / 1024 / 1024
            size = f'{size:.2f}'.rstrip('0.')
            return f'{size}GB'
        if field == 'state':
            return self._state_text[self._shot.state]

    def _get_state_index(self):
        if self._shot.missing_frames is not None:
            for camera_id, frames in self._shot.missing_frames.items():
                if len(frames) != 0:
                    return 4
        return self._shot.state

    def get_shot_id(self):
        return self._shot.get_id()

    def _build_menu(self):
        menu = QMenu()

        parm_action = QAction('Parameters', self)
        parm_action.triggered.connect(self._show_parameters)
        menu.addAction(parm_action)

        rename_action = QAction('Rename', self)
        rename_action.triggered.connect(self._rename)
        menu.addAction(rename_action)

        delete_action = QAction('Delete', self)
        delete_action.triggered.connect(self._remove)
        menu.addAction(delete_action)
        return menu

    def _show_parameters(self):
        popup(dialog=CameraParametersDialog)

    def _rename(self):
        result = popup(
            None,
            'Rename Shot',
            "Please input new shot's name",
            f'Shot Name:{self._shot.name}'
        )
        if result and result != self._shot.name:
            self._shot.rename(result)

    def _remove(self):
        if (
            popup(
                None, 'Delete Shot Confirm',
                f'Are you sure to delete [{self._shot.name}]?'
            )
        ):
            self._shot.remove()

    def enterEvent(self, event):
        if not self._is_current:
            QApplication.setOverrideCursor(Qt.PointingHandCursor)

    def leaveEvent(self, event):
        QApplication.restoreOverrideCursor()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_select = state.get('current_shot')
            if current_select != self._shot:
                state.cast('project', 'select_shot', self._shot)
        elif event.button() == Qt.RightButton:
            pos = self.mapToGlobal(event.pos())
            self._menu.exec_(pos)
