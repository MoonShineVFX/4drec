class Parameter:
    def __init__(self, name, default_value):
        self._name = name
        self._value = default_value
        self._callbacks = []

    def on_changed(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value
        for callback in self._callbacks:
            callback()

    def get_name(self):
        return self._name


class IntParameter(Parameter):
    def __init__(self, name, default_value):
        super().__init__(name, default_value)


class RangeParameter(Parameter):
    def __init__(self, name, default_value):
        super().__init__(name, default_value)


class ColorParameter(Parameter):
    def __init__(self, name, default_value):
        super().__init__(name, default_value)


class FileParameter(Parameter):
    def __init__(self, name, default_value):
        super().__init__(name, default_value)
