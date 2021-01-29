import PySpin
import queue

from utility.mix_thread import MixThread
from utility.setting import setting
from utility.message import message_manager
from utility.define import MessageType


class CameraConfigurator(MixThread):
    """相機參數控制

    用 PySpin 跟相機去連絡控制參數
    監控 self._queue.parms 去設定參數

    Args:
        camera: PySpin Camera

    """

    # 相機預設值
    default_config = {
        'AcquisitionMode': PySpin.AcquisitionMode_Continuous,

        # 觸發
        'TriggerSelector':
            PySpin.TriggerSelector_AcquisitionStart,
        'TriggerMode': PySpin.TriggerMode_On,
        'TriggerSource': PySpin.TriggerSource_Line0,
        'TriggerActivation': PySpin.TriggerActivation_LevelHigh,
        'TriggerOverlap': PySpin.TriggerOverlap_ReadOut,

        # 緩衝
        'TLStream.StreamBufferCountMode':
            PySpin.StreamBufferCountMode_Manual,
        'TLStream.StreamBufferCountManual': 40,
        'TLStream.StreamBufferHandlingMode':
            PySpin.StreamBufferHandlingMode_OldestFirst,

        # 相機捕捉範圍
        'Width': setting.camera_resolution[0],
        'Height': setting.camera_resolution[1],
        'OffsetX': setting.camera_offset[0],
        'OffsetY': setting.camera_offset[1],

        # 格率
        'AcquisitionFrameRateEnable': True,
        'AcquisitionFrameRate': setting.frame_rate,

        # 解除參數限制
        'ExposureMode': PySpin.ExposureMode_Timed,
        'ExposureAuto': PySpin.ExposureAuto_Off,
        'GainAuto': PySpin.GainAuto_Off,
        'BalanceWhiteAuto': PySpin.BalanceWhiteAuto_Off,
        'BlackLevelSelector': PySpin.BlackLevelSelector_All,
        'GammaEnable': True,
    }

    def __init__(self, camera, log):
        super().__init__()
        self._camera = camera  # PySpin Camera
        self._log = log
        self._queue_parms = queue.Queue()  # 任務佇列

        self.start()

    def _run(self):
        while self._running:
            parms = self._queue_parms.get()

            # 一直取到最底層的屬性
            for key, value in parms.items():
                prop = None
                if '.' in key:
                    keys = key.split('.')
                    prop = self._camera
                    for k in keys:
                        prop = getattr(prop, k)
                else:
                    prop = getattr(self._camera, key)

                try:
                    prop.SetValue(value)
                except PySpin.SpinnakerException as error:
                    self._log.error(f'Property: {key}, Value: {value}')
                    self._log.error(error)
                    message_manager.send_message(
                        MessageType.MASTER_DOWN,
                        is_local=True
                    )

            self._queue_parms.task_done()  # 如果 block 的話通知解鎖

    def apply_default_config(self):
        """套用預設設定，初始化時用"""
        self.apply_config(self.default_config.copy(), block=True)

    def apply_config(self, config, block=False):
        """套用設定

        Args:
            config: {參數名稱: 數值}
            block: 是否會阻擋目前執行緒

        """
        self._queue_parms.put(config)
        if block:
            self._queue_parms.join()

    def _stop(self):
        self.apply_config({})

    def _after_stop(self):
        del self._camera
