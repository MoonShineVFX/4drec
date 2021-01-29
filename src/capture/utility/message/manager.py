import socket
import queue
import time
from multiprocessing import current_process

from utility.mix_thread import MixThread
from utility.setting import setting
from utility.logger import log
from utility.define import MessageType

from .node import MessageNodeManager
from .message import Message


class MessageManager(MixThread):
    """Message 模組的主控

    管理連線，並負責所有訊息的收發動作
    建立連線的資訊與主從判斷都來自 setting 模組

    """

    def __init__(self):
        super().__init__()
        self._address = setting.get_host_address()  # 連線地址
        self._inbox = queue.Queue()  # 收件匣
        self._node = MessageNodeManager(self.put_inbox)  # Node 管理

        # 初始化後即自動執行
        self.start()

    def _run(self):
        """依照主從狀況去運作"""
        if setting.is_master():
            self._run_master()
        else:
            self._run_slave()

    def _build_socket(self):
        """建立所需 socket 並回傳"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return sock

    def _run_master(self):
        """master 的運作

        在為 master 的情況，socket 建立聆聽後會轉交給另一個執行緒 MessageAccepter
        MessageAccepter 負責把產生連線的對方 socket 傳回 queue 去做監控

        """
        connect_queue = queue.Queue()

        sock = self._build_socket()
        sock.bind(
            (setting.host_address.ip,
             setting.host_address.port)
        )

        # 聆聽連線
        sock.listen(6)
        log.info(f'Socket is Listening')

        # 建立連線交給 Accepter 處理
        self._accepter = MessageAccepter(sock, connect_queue)

        while self._running:
            # 有新連線的狀況
            if not connect_queue.empty():
                conn = connect_queue.get()
                self._node.add_connection(conn)
            else:
                # 檢查已連線的 socket 是否有出錯
                has_error = None

                for node in self._node.get_all():
                    if node.isFinished():
                        error = node.get_error()
                        if error is not None:
                            log.warning(
                                f'<{node.get_name()[0]}> {error}'
                            )
                            has_error = node

                        self._node.remove(node)

                # 連線有出錯的狀況，送警告訊息給自己
                if has_error is not None:
                    self.send_message(
                        MessageType.SLAVE_DOWN,
                        {'node': node},
                        is_local=True
                    )

            # 緩衝 loop 的間隔時間
            time.sleep(0.01)

    def _run_slave(self):
        """slave 的運作

        在為 slave 的情況，socket 會去找 host 並連接
        隨時監控連接是否斷訊並做相應處理

        """

        connected = False

        while self._running:
            try:
                sock = self._build_socket()
                sock.settimeout(1.0)
                sock.connect(self._address)
                sock.settimeout(None)

                # 連接上後的處理
                connected = True
                self._node.add_connection(sock)
                self.send_message(MessageType.MASTER_UP, is_local=True)

                while self._running:
                    # 監測 socket 是否有狀況
                    for node in self._node.get_all():
                        node.join(0.01)
                        error = node.get_error()
                        if error is not None:
                            raise error
            except (
                ConnectionResetError,
                ConnectionRefusedError,
                ConnectionAbortedError,
                TimeoutError,
                OSError
            ) as error:
                # 有狀況時的回報
                if connected:
                    log.warning(error)
                    self.send_message(MessageType.MASTER_DOWN, is_local=True)
                    connected = False  # connected 的設置是避免不斷報錯
                    if error.errno == 10054:
                        if current_process().name == 'MainProcess':
                            log.warning('10054 MainProcess error')

                self._node.clear()

    def _stop(self):
        """如果是 Master 的情況就會有 accepter，停下時也要停止它的運作"""
        if hasattr(self, '_accepter'):
            self._accepter.stop()

    def _after_stop(self):
        """已連線的 Nodes 也都要停下來"""
        self._node.stop()

    def send_message(self, msg_type, parms={}, payload=b'', is_local=False):
        """傳送訊息到 master 或 slaves

        會依照參數建立 Message 物件，詳細方式參照 Message 跟 MessageType

        Args:
            msg_type: 訊息類型，為 MessageType Enum
            parms: 額外附帶參數
            payload: 二進制邊碼，主要為圖像傳輸用
            is_local: 當訊息是傳送給自己時要為 True

        """
        message = Message(msg_type, parms, payload)
        if not is_local:
            self._node.add_send_queue(message)
        else:
            self.put_inbox(message)

    def receive_message(self):
        """查看接收訊息

        會回傳 Message 物件，是阻塞式調用

        """
        message = self._inbox.get()
        return message

    def put_inbox(self, message):
        """將訊息放到收件匣

        Args:
            message: message 物件

        """
        self._inbox.put(message)

    def is_connected(self):
        """是否已連線

        藉由查看 socket 的連線數來確定是否有連線

        """
        return len(self._node.get_all()) != 0

    def get_nodes_count(self):
        """取得正在連線的 node數量"""
        return self._node.get_count()


class MessageAccepter(MixThread):
    """Message 聆聽用模組

    master 用，socket 連線確認建立後
    將 socket 放到 self._connect_queue

    Args:
        sock: 主持的 socket
        connect_queue: 主程式監視的 queue

    """

    def __init__(self, sock, connect_queue):
        super().__init__()
        self._sock = sock  # 主持的 socket
        self._connect_queue = connect_queue  # 主程式監視的 queue

        # 初始化後即自動執行
        self.start()

    def _run(self):
        try:
            while self._running:
                conn, addr = self._sock.accept()
                self._connect_queue.put(conn)
        except OSError as error:
            log.warning(error)

    def _stop(self):
        """用 shutdown 的方式強制關閉 socket"""
        self._sock.shutdown(2)
        self._sock.close()
