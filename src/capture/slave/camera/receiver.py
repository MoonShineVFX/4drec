import PySpin

from utility.message import message_manager
from utility.mix_thread import MixThread
from utility.define import MessageType


class Receiver(MixThread):
    def __init__(self, camera_connector, log):
        super().__init__()
        self._camera_connector = camera_connector
        self._log = log
        self.start()

    def _run(self):
        while self._running:
            # Message 接收與觸發
            message = message_manager.receive_message()
            # self._log.debug(f'Receive Messasge: {message}')

            if message.type is MessageType.TOGGLE_LIVE_VIEW:
                self._toggle_live_view(message)

            elif message.type is MessageType.TOGGLE_RECORDING:
                self._toggle_recording(message)

            elif message.type is MessageType.GET_SHOT_IMAGE:
                self._load_shot_image(message)

            elif message.type is MessageType.RETRIGGER:
                self._camera_connector.retrigger()

            elif message.type is MessageType.CAMERA_PARM:
                self._change_parameter(message)

            elif message.type is MessageType.REMOVE_SHOT:
                self._remove_shot(message)

            elif message.type is MessageType.SUBMIT_SHOT:
                self._submit_shot(message)

            elif message.type is MessageType.CAMERA_STATUS:
                self._report_status()

            elif message.type is MessageType.MASTER_DOWN:
                break

        self._log.warning('Master down, stop camera system')
        self._camera_connector.kill()

    def _toggle_live_view(self, message):
        """開關即時預覽

        解出訊息的參數，將要啟動即時預覽的相機開啟並賦予參數，其餘關閉

        Args:
            message: LiveView訊息

        """
        parms = message.unpack()

        if parms['toggle']:
            if parms['close_up'] and parms['close_up'] == self._camera_connector.get_id():
                length = None
            else:
                length = parms['scale_length']

            self._camera_connector.start_live_view(
                quality=parms['quality'],
                scale_length=length
            )
        else:
            self._camera_connector.stop_live_view()

    def _toggle_recording(self, message):
        """開關錄製

        解出訊息的參數，根據參數開關相機的錄製

        Args:
            message: 錄製訊息

        """
        is_start, shot_id, is_cali = message.unpack()
        if is_start:
            self._camera_connector.start_recording(shot_id, is_cali)
        else:
            self._camera_connector.stop_recording()

    def _load_shot_image(self, message):
        """讀取錄製的圖像

        解出訊息的參數，根據參數從指定的相機讀取指定的圖像

        Args:
            message: 讀取圖像訊息

        """
        parms = message.unpack()
        camera_id = parms['camera_id']
        if camera_id == self._camera_connector.get_id():
            self._camera_connector.load_shot_image(parms)

    def _change_parameter(self, message):
        """更改相機參數

        解出訊息的參數，根據參數更改相機的參數

        Args:
            message: 相機參數訊息

        """
        name, value = message.unpack()

        # 檢查是否有設定白平衡，有的話需要做額外設定
        balance = None
        if not name.startswith('BalanceRatio'):
            attr = name
        else:
            balance = name.replace('BalanceRatio', '')
            attr = 'BalanceRatio'

        # 設定白平衡的情況，需要先去選擇要調整的白平衡類型
        if balance is not None:
            if balance == 'Red':
                selector = PySpin.BalanceRatioSelector_Red
            else:
                selector = PySpin.BalanceRatioSelector_Blue

            self._camera_connector.change_parameter(
                'BalanceRatioSelector', selector
            )

        # 改變相機參數
        self._camera_connector.change_parameter(attr, value)

        self._log.info(f'Parameter <{name}> changes to {value}')

    def _remove_shot(self, message):
        """移除 Shot

        Args:
            message: 移除訊息

        """
        shot_id = message.unpack()
        self._camera_connector.remove_shot(shot_id)

    def _submit_shot(self, message):
        """發布 Shot

        Args:
            message: 發佈訊息

        """
        parms = message.unpack()
        shot_id = parms['shot_id']
        job_name = parms['job_name']
        frames = parms['frames']

        # 蒐集檔案路徑
        shot_file_paths = {
            self._camera_connector.get_id(): self._camera_connector.get_shot_file_path_for_recording(shot_id)
        }

        self._camera_connector.add_submit_task((
            shot_id,
            job_name,
            frames,
            shot_file_paths
        ))

    def _report_status(self):
        message_manager.send_message(
            MessageType.CAMERA_STATUS,
            {self._camera_connector.get_id(): self._camera_connector.get_status()}
        )

    def _stop(self):
        self._report_status()
