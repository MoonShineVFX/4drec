import queue

from utility.mix_thread import MixThread
from utility.logger import log

from .message import Message


class MessageNodeManager():
    """Node 管理

    把 socket 存放成 node 並與之和 manager 溝通
    負責 node 的動作控制與存活

    Args:
        put_inbox: manager 放入收件匣的 func

    """

    def __init__(self, put_inbox):
        self._nodes = {}  # 存放的 node 字典
        self._put_inbox = put_inbox  # 從 manager 取得的收件匣

    def add_connection(self, conn):
        """增加連線

        將新增的連線包成 node，納入管理

        Args:
            conn: 連線的 socket

        """
        name = conn.getpeername()  # 取得連線名稱當作ID
        log.info(f'Connection established ({name[0]})')
        send_node = MessageSendNode(conn, name)
        receive_node = MessageReceiveNode(
            conn, name, put_inbox=self._put_inbox
        )

        self._nodes[name] = (send_node, receive_node)

    def get_all(self):
        """取得全部的 node"""
        nodes = []
        for node_pair in self._nodes.values():
            nodes.extend(node_pair)
        return nodes

    def get_count(self):
        """取得正在連線的 node數量"""
        return len(self._nodes)

    def remove(self, node):
        """刪除 node，刪除前會先停止其運行

        Args:
            node: 要刪除的 node

        """
        name = node.get_name()
        if name in self._nodes:
            for node in self._nodes[name]:
                if node.is_running():
                    node.stop()

            del self._nodes[name]

    def add_send_queue(self, message):
        """增加訊息到寄件佇列

        Args:
            message: 要放到佇列的訊息

        """
        for pair_node in self._nodes.values():
            pair_node[0].add_send_queue(message)

    def clear(self):
        """清空連線

        主要是給 slave 用，當 master 斷訊時將連線清空重整

        """
        self.stop()
        self._nodes = {}

    def stop(self):
        """停止時將所有管理的 node 都停下來"""
        for node in self.get_all():
            node.stop()


class MessageNode(MixThread):
    """Node 元件

    讓 socket 方便管理的包裝，平時看收發類型運作
    當有錯誤時會將錯誤存放在 self._error 並結束運行

    Args:
        sock: 連線 socket
        name: 連線的位址

    """

    def __init__(self, sock, name):
        super().__init__()
        self._sock = sock  # 連線 socket
        self._name = name  # 連線的位址
        self._error = None  # 連線錯誤時的放置位置

    def get_error(self):
        """取得錯誤訊息，如果沒有會回傳 None"""
        return self._error

    def get_name(self):
        """取得連線位址"""
        return self._name

    def _stop(self):
        """停止運作時，強制關閉 socket"""
        try:
            self._sock.shutdown(2)
            self._sock.close()
        except Exception:
            pass


class MessageSendNode(MessageNode):
    """Node 寄送元件

    繼承 MessageNode 元件，檢查自己的 self._send_queue
    一有訊息就執行寄送

    """

    def __init__(self, sock, name):
        super().__init__(sock, name)
        self._send_queue = queue.Queue()  # 寄送佇列

        # 初始化後即自動執行
        self.start()

    def _run(self):
        """監測寄送佇列，有訊息變將其轉換成封包送出"""
        while self._running:
            message = self._send_queue.get()

            packet = message.to_packet()

            try:
                self._sock.sendall(packet)
            except Exception as error:
                self._error = error
                self.stop()

    def add_send_queue(self, message):
        """加入寄送佇列"""
        self._send_queue.put(message)


class MessageReceiveNode(MessageNode):
    """Node 接收元件

    繼承 MessageNode 元件，檢查自己的 self._send_queue
    一有訊息就執行寄送

    Args:
        put_inbox: manager 放入收件匣的 func

    """

    def __init__(self, sock, name, put_inbox):
        super().__init__(sock, name)
        self._put_inbox = put_inbox  # manager 放入收件匣的 func

        # 初始化後即自動執行
        self.start()

    def _run(self):
        """接收封包並轉換成訊息後，放到收件匣"""
        while self._running:
            try:
                # 取得大小資訊
                meta = self._recvall(Message.META_SIZE)
                message_size, payload_size = Message.unpack_meta(meta)

                # 取得確切大小的封包
                message_bytes = self._recvall(message_size)
                payload = self._recvall(payload_size)

                # 將封包轉換成物件
                message = Message.load_from_bytes(message_bytes, payload)

                # 存入收件匣
                self._put_inbox(message)
            except Exception as error:
                self._error = error
                self.stop()

    def _recvall(self, n):
        """接收封包到指定大小為止

        Args:
            n: 封包大小

        """
        data = b''
        while len(data) < n:
            packet = self._sock.recv(n - len(data))
            data += packet
        return data
