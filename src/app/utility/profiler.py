from time import perf_counter


class Profiler():
    """性能監測器

    給予指定的閥值，到達閥值便會觸發事件，然後歸零

    Args:
        threashold: 閥值
        on_count_reached: 觸發事件

    """

    def __init__(self, threshold, on_count_reached):
        self._threshold = threshold  # 閥值
        self._on_count_reached = on_count_reached  # 觸發事件

        self._count = 0  # 紀錄次數
        self._timestamp = perf_counter()  # 紀錄時間

    def count(self):
        """紀錄點"""
        self._count += 1
        if self._count == self._threshold:
            now = perf_counter()

            avg_time = now - self._timestamp
            self._on_count_reached(avg_time)

            self._count = 0
            self._timestamp = now
