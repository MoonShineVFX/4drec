import struct
import pickle
import copy

from utility.define import MessageType


class Message():
    """訊息物件，機器間交互溝通的核心

    訊息物件由訊息類型、參數字典檔、payload (可選，二進制編碼)構成
    訊息傳出時，前二者會 pickle 序列化再加上 payload 來傳輸

    Args:
        msg_type: 訊息類型，為 MessageType Enum
        parms: 額外附帶參數
        payload: 二進制編碼，主要為圖像傳輸用

    """

    # 設定訊息的封包格式
    META_FORMAT = '>II'
    META_SIZE = struct.calcsize(META_FORMAT)

    def __init__(self, msg_type, parms={}, payload=b''):
        self._type = msg_type  # 訊息類型
        self._parms = parms  # 參數
        self._payload = payload  # 二進制編碼

    def __str__(self):
        return f'[{self._type.name}]: {self._parms}'

    def to_packet(self):
        """轉換成封包

        訊息傳輸前的動作
        先複製一個去掉 payload 的自身物件並序列化
        再將 payload 加回去後利用 struct 包裝傳出

        """
        obj = copy.copy(self)
        obj._payload = b''
        msg = pickle.dumps(obj)
        packet = struct.pack(
            self.META_FORMAT,
            len(msg),
            len(self._payload)
        ) + msg + self._payload
        return packet

    def unpack(self):
        """提取資料

        訊息到目的地的動作
        依照訊息類型的不同去提取對應的資料

        """
        if (
            self._type is MessageType.LIVE_VIEW_IMAGE or
            self._type is MessageType.SHOT_IMAGE
        ):
            return (
                self._parms,
                self._payload
            )
        elif self._type is MessageType.TOGGLE_LIVE_VIEW:
            return self._parms
        elif self._type is MessageType.TOGGLE_RECORDING:
            return (
                self._parms['is_start'],
                self._parms.get('shot_id', None),
                self._parms.get('is_cali', None)
            )
        elif self._type is MessageType.GET_SHOT_IMAGE:
            return self._parms
        elif self._type is MessageType.CAMERA_STATUS:
            return self._parms
        elif self._type is MessageType.CAMERA_PARM:
            return self._parms['camera_parm']
        elif self._type is MessageType.RECORD_REPORT:
            return self._parms
        elif self._type is MessageType.REMOVE_SHOT:
            return self._parms['shot_id']
        elif self._type is MessageType.SUBMIT_SHOT:
            return self._parms
        elif self._type is MessageType.SUBMIT_REPORT:
            return self._parms
        elif self._type is MessageType.SLAVE_DOWN:
            return self._parms['node']
        elif self._type is MessageType.TRIGGER_REPORT:
            return self._parms['camera_id']

    @property
    def type(self):
        """取得訊息類型"""
        return self._type

    @classmethod
    def unpack_meta(cls, meta):
        """取得封包的大小資訊

        會回傳兩個數字，一組是訊息物件的大小，一組是 payload 的大小

        Args:
            meta: 收到的二進制封包

        """
        return struct.unpack(cls.META_FORMAT, meta)

    @staticmethod
    def load_from_bytes(message_bytes, payload):
        """從序列化的狀態讀取回 Python 物件

        Args:
            message_bytes: 序列化的訊息物件
            payload: 二進制邊碼

        """
        message = pickle.loads(message_bytes)
        message._payload = payload
        return message
