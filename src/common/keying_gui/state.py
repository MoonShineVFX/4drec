from PyQt5.Qt import QObject, pyqtSignal


class UIState():
    def __init__(self):
        self._state = {
            'keying_image': None,
            'hover_color': (-1, -1, -1)
        }

        self._callbacks = {}
        for key in self._state:
            self._callbacks[key] = UIStateSignal()

    def get(self, state_name):
        return self._state[state_name]

    def set(self, state_name, value):
        self._state[state_name] = value
        self._callbacks[state_name].signal.emit()

    def on_changed(self, state_name, func):
        self._callbacks[state_name].signal.connect(func)


class UIStateSignal(QObject):
    signal = pyqtSignal()

    def __init__(self):
        super().__init__()


state = UIState()