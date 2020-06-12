from PyQt5.Qt import Qt, QPushButton

from utility.define import BodyMode

from master.ui.custom_widgets import LayoutWidget
from master.ui.state import state, EntityBinder


class BodySwitcher(LayoutWidget, EntityBinder):
    def __init__(self):
        super().__init__(alignment=Qt.AlignCenter)
        self._switches = []
        self._setup_ui()
        self._state = None
        state.on_changed('current_shot', self._update)

    def _setup_ui(self):
        for mode in BodyMode:
            button = BodySwitchButton(mode)
            self.addWidget(button)
            self._switches.append(button)

    def _update(self):
        shot = state.get('current_shot')
        if shot is None:
            return

        self.bind_entity(shot, self._update)

        if shot == self._entity and shot.state == self._state:
            return

        if shot.state != self._state:
            self._state = shot.state

        for button in self._switches:
            button.show()

        if shot.state == 0:
            self._set((0, 3, 2))
        elif shot.state == 1:
            self._set((3, 0, 2))
        else:
            self._set((3, 1, 0))

    def _set(self, set_list):
        for i, button in zip(set_list, self._switches):
            button.setEnabled(i < 2)
            button.setVisible(i < 3)

            if i == 0:
                button.on_clicked()


class BodySwitchButton(QPushButton):
    _default = '''
    * {
      border: 1px solid palette(dark);
    }

    *:hover {
      color: palette(highlight);
    }

    *:checked {
      color: palette(bright-text);
      background-color: palette(dark);
      font-weight: 500;
    }

    *:disabled {
      color: palette(dark);
    }

    '''

    def __init__(self, mode):
        super().__init__()
        self._mode = mode
        self.clicked.connect(self.on_clicked)
        state.on_changed('body_mode', self._update)
        self._setup_ui()
        self._update()

    def _setup_ui(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(100, 40)
        self.setStyleSheet(self._default)
        self.setCheckable(True)
        text = '3D' if self._mode is BodyMode.MODEL else '2D'
        self.setText(text)

    def _update(self):
        self.setChecked(self._mode is state.get('body_mode'))

    def on_clicked(self):
        if self._mode is state.get('body_mode'):
            self.setChecked(True)
        else:
            state.set('body_mode', self._mode)
