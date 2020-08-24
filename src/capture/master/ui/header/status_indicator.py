from PyQt5.Qt import Qt, QLabel, QPushButton, QIcon

from master.ui.custom_widgets import LayoutWidget
from master.ui.resource import icons
from master.ui.state import state


class StatusIndicator(LayoutWidget):
    def __init__(self):
        super().__init__(
            alignment=Qt.AlignRight,
            spacing=24
        )
        self._widgets = {}
        state.on_changed('status', self._update)
        self._setup_ui()

    def _update(self):
        if state.get('caching'):
            return

        status = state.get('status')
        for key, value in status.items():
            if key not in self._widgets:
                continue

            if isinstance(value, float):
                text = f'{value:.2f}'
            else:
                text = str(value)
            self._widgets[key].set_text(text)

    def _setup_ui(self):
        self.addWidget(ScreenButton())
        self.addWidget(TriggerButton())
        for text in ('slaves', 'bias', 'cache_size'):
            widget = StatusItem(text)
            self._widgets[text] = widget
            self.addWidget(widget)


class StatusItem(LayoutWidget):
    _default = 'font-size: 18px; padding-bottom: 5px'

    def __init__(self, icon):
        super().__init__(spacing=5)
        self._text = ''
        self._text_label = None
        self._icon = icon
        self._setup_ui()

    def set_text(self, text):
        self._text_label.setText(text)

    def _setup_ui(self):
        icon_label = QLabel()
        pixmap = icons.get(self._icon)
        icon_label.setPixmap(pixmap)
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignCenter)

        self._text_label = QLabel(self._text)
        self._text_label.setStyleSheet(self._default)

        self.addWidget(icon_label)
        self.addWidget(self._text_label)


class HeaderButton(QPushButton):
    def __init__(self, icon_name):
        super().__init__()
        self.setIcon(QIcon(icons.get(icon_name)))
        self.setStyleSheet('''
            padding: 8px;
            width: 24px;
            height: 24px;
        ''')


class ScreenButton(HeaderButton):
    def __init__(self):
        super().__init__(icon_name='airplay')
        self._setup_ui()
        self.clicked.connect(self._toggle_screen)

    def _setup_ui(self):
        self.setCheckable(True)

    def _toggle_screen(self):
        state.set('second_screen', self.isChecked())


class TriggerButton(HeaderButton):
    def __init__(self):
        super().__init__(icon_name='refresh')
        self.clicked.connect(self._trigger)

    def _trigger(self):
        state.cast('camera', 'retrigger')
