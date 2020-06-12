from utility.message import message_manager
from utility.logger import log
from utility.define import MessageType
from utility.restart import restart

from .camera import CameraSystem


def start_slave():
    """Slave 總啟動程序"""
    log.info('Start slave')

    # 等待 Master 連接
    log.info('Wait for master connecting...')

    if not message_manager.is_connected():
        message = message_manager.receive_message()
        while message.type is not MessageType.MASTER_UP:
            continue

    # 相機系統初始化
    camera_system = CameraSystem()
    camera_system.start()

    while True:
        message = message_manager.receive_message()
        if message.type is MessageType.MASTER_DOWN:
            log.warning('Master Down !!')
            break

    log.info('Stop all connectors')
    camera_system.stop()
    restart()
