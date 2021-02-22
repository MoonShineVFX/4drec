import PySpin
import time

from utility.setting import setting
from utility.logger import log

from .connector import CameraConnector


class CameraSystem:
    """相機管理系統

    藉由 PySpin 與相機做溝通控制，由底下的 self._connectors 去列管

    """

    def __init__(self):
        self._camera_system = None  # PySpin 的系統
        self._camera_list = None  # PySpin 的相機列表
        self._connectors = []  # 相機 connector 列表

    def _initialize(self):
        """初始化相機系統

        用 has_reset 去操作恢復原廠設定
        另外檢查相機初始化的數量是否正確，如果不是正確數量，隔一段時間再重試

        """
        has_reset = True  # 恢復原廠設定的開關，false 的話初始化都會重置一次

        while True:
            log.info('Initialize camera system')
            self._camera_system = PySpin.System.GetInstance()
            self._camera_list = self._camera_system.GetCameras()
            current_cameras_count = self._camera_list.GetSize()

            setting_cameras_count = setting.get_slave_cameras_count()

            # 相機數量不對的狀況
            if current_cameras_count < setting_cameras_count:
                log.error((
                    "Camera count didn't match setting"
                    f' ({current_cameras_count}/{setting_cameras_count}),'
                    ' try again after 30s'
                ))
                time.sleep(10)
                self.clear(retry=True)
                continue

            # 需要恢復原廠設定的狀況
            if not has_reset:
                log.info('Factory reset cameras')

                for i in range(current_cameras_count):
                    camera = self._camera_list.GetByIndex(i)
                    camera.Init()
                    camera.FactoryReset()
                    del camera

                self.clear(retry=True)
                has_reset = True
                continue

            # 正常初始化的狀況，將相機給 connector 納管
            self._connectors = self._build_connectors()

            break

    def stop(self):
        for connector in self._connectors:
            connector.kill()
        log.info('Connector stop...')
        self.clear()

    def _build_connectors(self):
        connectors = []
        for i in range(self._camera_list.GetSize()):
        # for i in range(setting.get_slave_cameras_count()):
            connector = CameraConnector(i, log)
            connector.start()
            connectors.append(connector)

        return connectors

    def start(self):
        self._initialize()

    def clear(self, retry=False):
        """斷開與 PySpin的連結

        將記憶體清空，必須把變數刪除才能從 SDK 斷開

        """
        self._camera_list.Clear()
        del self._camera_list
        self._camera_system.ReleaseInstance()
        del self._camera_system
