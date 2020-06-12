"""訊息模組

機器之間溝通的模組，單例模式

"""

from .manager import MessageManager
from .message import Message

message_manager = MessageManager()
