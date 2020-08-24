from PyQt5.Qt import pyqtSignal
from queue import Queue

from utility.mix_thread import MixThread


class UIEventHandler(MixThread):
    """介面事件管理器

    接收外部的事件並發送 pyqtSignal 給主介面執行緒
    外部事件由 dispatch_event 去產生

    """

    on_receive = pyqtSignal(object)  # 與主介面的訊號相連

    def __init__(self):
        super().__init__()
        self._event_queue = Queue()

        # 初始化後即自動執行
        self.start()

    def _run(self):
        while self._running:
            event = self._event_queue.get()
            self.on_receive.emit(event)

    def dispatch(self, event_type, payload=None):
        """發送事件

        外部調用來跟介面溝通的函式

        Args:
            event: UIEvent

        """
        self._event_queue.put(UIEvent(event_type, payload))


class UIEvent():
    """介面事件

    傳送到介面的封包

    Args:
        evemt_type: 事件類型
        payload: 事件內容物

    """

    def __init__(self, event_type, payload=None):
        self._type = event_type  # 事件類型
        self._payload = payload  # 事件內容物

    @property
    def type(self):
        """取得類型"""
        return self._type

    def get_payload(self):
        """取得內容"""
        return self._payload
