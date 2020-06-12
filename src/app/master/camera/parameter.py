class CameraParameter():
    """相機參數控制單位

    Args:
        name: 參數名稱
        _min: 最小值
        _max: 最大值
        default: 預設數值
        _type: 參數單位(int, float)

    """

    def __init__(self, name, _min, _max, default, _type):
        self._name = name  # 參數名稱
        self._min = _min  # 最小值
        self._max = _max  # 最大值
        self._default = default
        self._value = default  # 參數數值，初始化給預設數值
        self._type = int if _type == 'int' else float  # 單位

    def get_value(self):
        """取得參數數值"""
        return self._value

    def get_default(self):
        return self._default

    def set(self, value):
        """設定參數數值

        會先驗證數值是否在設定範圍內，如果不是便不會設定並回傳原因

        Args:
            value: 要設定的數值

        """
        value = self._type(value)

        if value < self._min:
            return 'min'
        elif value > self._max:
            return 'max'

        self._value = value
        return 'OK'

    def __str__(self):
        return '{:^20}|| {:>6}<{:^10}>{:<6}'.format(
            self._name,
            self._min,
            self._value,
            self._max
        )
