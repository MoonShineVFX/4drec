class Parameter:
    def __init__(self, name, default_value):
        self._name = name
        self._value = default_value

    def get_value(self):
        return self._value

    def set_value(self, value):
        self._value = value

    def get_name(self):
        return self._name


class IntParameter(Parameter):
    def __init__(self, name, default_value):
        super().__init__(name, default_value)


class RangeParameter(Parameter):
    def __init__(self, name, default_value):
        super().__init__(name, default_value)
