class Parameter:
    def __init__(self, name, default_value):
        self._name = name
        self._value = default_value

    def get_value(self):
        return self._value

    def get_name(self):
        return self._name


class IntParameter:
    def __init__(self, name, default_value):
        super().__init__(name, default_value)


class RangeParameter:
    def __init__(self, name, default_value):
        super().__init__(name, default_value)
