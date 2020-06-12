from PyQt5.Qt import (
    QListWidget, QListWidgetItem, QWidget, QMenu, QAction,
    QAbstractItemView, QPushButton, QLabel, QPainter,
    QStyledItemDelegate, QIcon, QSize, Qt, QPixmap, QPainterPath
)

from master.ui.resource import icons
from master.ui.custom_widgets import LayoutWidget, make_layout
from master.ui.state import state, EntityBinder
from master.ui.popup import popup


def _load_project():
    state.cast(
        'project', 'select_project',
        state.get('project_list_select')
    )
    state.set('project_list_dialog', False)


def _is_loadable():
    current_select = state.get('project_list_select')
    current_project = state.get('current_project')
    return current_select is not None and current_select != current_project


class ProjectList(QListWidget):
    _default = '''
    ProjectList {
        background-color: palette(alternate-base);
    }
    '''

    def __init__(self):
        super().__init__()
        self._project_widgets = {}
        self.setSelectionMode(QAbstractItemView.NoSelection)
        state.on_changed('projects', self._update)
        self._setup_ui()

    def _update(self):
        projects = state.get('projects')
        new_project_ids = []

        added_item = None
        for order, project in enumerate(projects):
            project_id = project.get_id()
            if project_id not in self._project_widgets:
                item = QListWidgetItem()
                widget = ProjectItem(item, project)
                self.insertItem(order, item)
                self.setItemWidget(item, widget)
                self._project_widgets[project_id] = widget

                if added_item is None:
                    added_item = item

            new_project_ids.append(project_id)

        deleted_widgets = [
            widget for widget in self._project_widgets.values()
            if widget.get_project_id() not in new_project_ids
        ]

        for widget in deleted_widgets:
            project_id = widget.get_project_id()
            index = self.indexFromItem(widget.get_item())
            self.takeItem(index.row())
            del self._project_widgets[project_id]

        if added_item:
            self.scrollToItem(added_item)

    def _setup_ui(self):
        self.setItemDelegate(ProjectDelegate())
        self.setStyleSheet(self._default)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self._update()


class ProjectDelegate(QStyledItemDelegate):
    def __init__(self):
        super().__init__()

    def paint(self, painter, option, index):
        pass

    def sizeHint(self, option, index):
        return QSize(-1, 120 + 16)


class ProjectItem(LayoutWidget, EntityBinder):
    _default = '''
    #title {
      font-size: 24px;
      color: palette(bright-text);
    }

    #date {
      font-size: 12px;
    }

    #icon-value {
      font-size: 14px;
    }

    '''
    _wrapper_default = '''
    #wrapper {
        background-color: palette(base);
        border-radius: 5px;
    }
    '''
    _wrapper_selected = '''
    #wrapper {
        border: 2px solid palette(midlight);
    }
    '''

    def __init__(self, item, project):
        super().__init__(margin=8)
        self._item = item
        self._project = project
        self._wrapper = None
        self._menu = None
        self._title_label = None

        self._setup_ui()

        self.bind_entity(project, self._update)
        state.on_changed('project_list_select', self._update)

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self._menu = self._build_menu()

        detail_layout = make_layout(
            horizon=False, margin=(0, 8, 0, 8)
        )

        self._title_label = QLabel()
        self._title_label.setObjectName('title')
        self._title_label.setAlignment(Qt.AlignCenter)

        time_label = QLabel(self._project.create_at_str)
        time_label.setObjectName('date')
        time_label.setAlignment(Qt.AlignCenter)

        icon_layout = LayoutWidget(
            margin=(8, 0, 8, 0),
            alignment=Qt.AlignCenter,
            spacing=24
        )

        for key, value in self._project.get_overview().items():
            icon_layout.layout().addLayout(self._icon_widget(key, value))

        detail_layout.addWidget(self._title_label)
        detail_layout.addWidget(time_label)
        detail_layout.addWidget(icon_layout)

        wrapper = LayoutWidget()
        wrapper.setObjectName('wrapper')
        wrapper.setStyleSheet(self._wrapper_default)

        wrapper.addLayout(detail_layout)
        wrapper.layout().setStretch(1, 1)
        self._wrapper = wrapper

        self.layout().addWidget(wrapper)

        self._update()

    def _icon_widget(self, icon, value):
        layout = make_layout(spacing=4, alignment=Qt.AlignHCenter)

        icon_label = QLabel()
        icon_label.setPixmap(icons.get(icon))
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(str(value))
        text_label.setObjectName('icon-value')

        layout.addWidget(icon_label)
        layout.addWidget(text_label)

        return layout

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            current_select = state.get('project_list_select')
            if current_select != self._project:
                state.set('project_list_select', self._project)
        elif event.button() == Qt.RightButton:
            pos = self.mapToGlobal(event.pos())
            self._menu.exec_(pos)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if _is_loadable():
                _load_project()

    def _build_menu(self):
        menu = QMenu()

        rename_action = QAction('Rename', self)
        rename_action.triggered.connect(self._rename)
        menu.addAction(rename_action)

        delete_action = QAction('Delete', self)
        delete_action.triggered.connect(self._remove)
        menu.addAction(delete_action)
        return menu

    def _rename(self):
        result = popup(
            None,
            'Rename Project',
            "Please input new project's name",
            f'Project Name:{self._project.name}'
        )
        if result and result != self._project.name:
            self._project.rename(result)

    def _remove(self):
        if (
            popup(
                None, 'Delete Project Confirm',
                f'Are you sure to delete [{self._project.name}]?'
            )
        ):
            self._project.remove()

    def _update(self):
        current_select = state.get('project_list_select')
        if current_select == self._project:
            self._wrapper.setStyleSheet(
                self._wrapper_default + self._wrapper_selected
            )
        else:
            self._wrapper.setStyleSheet(self._wrapper_default)

        self._title_label.setText(self._project.name)

    def get_item(self):
        return self._item

    def get_project_id(self):
        return self._project.get_id()


class ProjectThumbnail(QWidget):
    def __init__(self):
        super().__init__()
        self._pixmap = None
        self._setup_ui()

    def _setup_ui(self):
        self._pixmap = QPixmap('')
        self.setFixedSize(self._pixmap.size())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self._pixmap)
        painter.fillRect(self.rect(), self.palette().midlight().color())

        round_path = QPainterPath()
        round_path.addRoundedRect(0, 0, self.width(), self.height(), 5, 5)
        sq_path = QPainterPath()
        sq_path.addRect(
            0, 0,
            10, self.height()
        )
        draw_path = sq_path - round_path
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.palette().dark().color())
        painter.drawPath(draw_path)


class ProjectListButtonGroup(LayoutWidget):
    def __init__(self):
        super().__init__(margin=16, alignment=Qt.AlignCenter)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet('font-size: 18px;')

        new_button = ProjectListButton('add', 'New')
        new_button.clicked.connect(
            lambda: state.set('project_new_dialog', True)
        )
        self.addWidget(
            new_button
        )

        self.layout().addStretch()

        load_button = ProjectListButton('load', 'Load')
        load_button.clicked.connect(_load_project)
        load_button.setDisabled(True)
        self.addWidget(
            load_button
        )


class ProjectListButton(QPushButton):
    def __init__(self, icon, text):
        super().__init__(f'  {text}')
        self._icon = icon
        state.on_changed('project_list_select', self._update)
        self._setup_ui()

    def _update(self):
        if self._icon == 'load':
            if _is_loadable():
                self.setDisabled(False)
            else:
                self.setDisabled(True)

    def _setup_ui(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet('font-size: 16px;')
        icon = QIcon(icons.get(self._icon))
        self.setIcon(icon)

    def sizeHint(self):
        return QSize(100, 35)
