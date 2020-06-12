from PyQt5.Qt import Qt

from master.ui.custom_widgets import LayoutWidget, make_layout

from .project_title import ProjectTitle
from .body_switcher import BodySwitcher
from .status_indicator import StatusIndicator


class Header(LayoutWidget):
    _default = 'Header {background-color: palette(base)}'

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        title_layout = make_layout(alignment=Qt.AlignLeft)
        title_layout.addWidget(ProjectTitle())

        switcher_layout = make_layout(alignment=Qt.AlignCenter)
        switcher_layout.addWidget(BodySwitcher())

        status_layout = make_layout(
            alignment=Qt.AlignRight, margin=(0, 0, 16, 0)
        )
        status_layout.addWidget(StatusIndicator())

        self.addLayout(title_layout)
        self.addLayout(switcher_layout)
        self.addLayout(status_layout)

        self.setFixedHeight(65)
        self.setStyleSheet(self._default)
