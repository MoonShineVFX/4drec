from multiprocessing import Process
from threading import Thread
import os
import PySpin

from utility.define import CameraState
from utility.setting import setting

from .encoder import CameraLiveViewer, CameraShotLoader, CameraShotSubmitter
from .recorder import CameraRecorder
from .configurator import CameraConfigurator
from .shot import CameraShotFileCore, CameraShotMeta
from .image import CameraImage
from .receiver import Receiver


class CameraConnector(Process):
    """相機管理

    以每台相機為單位，去控制相機、讀寫 shot 及圖像處理。

    Args:
        camera: PySpin 的相機
        record_folder_path: 錄製的資料夾路徑

    """

    def __init__(self, camera_index, logger):
        super().__init__()

        # PySpin
        self._system = None
        self._cameras = None

        # main
        self._camera_index = camera_index
        self._camera = None  # PySpin 相機
        self._id = None  # 相機ID
        self._record_folder_path = setting.get_record_folder_path(camera_index)  # 錄製的資料夾路徑
        self._receiver = None
        self._log = logger

        # 即時預覽
        self._live_viewer = None

        # 錄製
        self._recorder = None

        # 讀取圖像
        self._shot_loader = None
        self._submitter = None

        # 相機參數
        self._configurator = None

        # 狀態
        self._current_frame = -1  # 目前擷取的相機格數
        self._is_recording = False  # 錄製中
        self._stop_sign = False
        self._is_live_view = False  # 預覽中
        self._state = CameraState.CLOSE  # 目前狀態
        self._is_retrigger = False

    def run(self):
        """運行

        相機先進行初始化，之後會開始進行擷取流程

        擷取流程:
            1. 事前準備完畢後會改變成待命並等待觸發
            2. 觸發後開始進行擷取，改變狀態
            3. 停止擷取時，關閉所有擷取的功能，改變狀態
            4. 重複第一步

        """
        self._initialize()
        while self._is_retrigger:
            self._is_retrigger = False
            self._begin_capture()
            self._end_capture()
        self.clear()

    def _initialize(self):
        """相機初始化並給予預設相機參數"""
        self._log.debug('Initializing...')
        self._system = PySpin.System.GetInstance()
        self._cameras = self._system.GetCameras()

        # get camera
        self._camera = self._cameras.GetByIndex(self._camera_index)

        # set attribute
        self._id = self._camera.GetUniqueID()
        self._configurator = CameraConfigurator(self._camera, self._log)
        # self._log = get_prefix_log(f'<{self._id}> ')

        # set child threads
        self._live_viewer = CameraLiveViewer(self._id)
        self._receiver = Receiver(self, self._log)
        self._shot_loader = CameraShotLoader(self._log)
        self._submitter = CameraShotSubmitter(self._log)

        # Initialize
        self._camera.Init()
        self._log.debug('Initialized')

        self._log.debug('Apply default config')
        self._configurator.apply_default_config()

        self._is_retrigger = True
        self._log.info('Initialized')

    def _begin_capture(self):
        """開始擷取

        準備好後改變待命狀態，並等待觸發
        開始擷取後，每一張擷取都確認是否需要錄製檔案或者即時預覽

        """

        self._camera.BeginAcquisition()

        # 待命觸發
        self._change_state(CameraState.STANDBY)

        # 開始擷取
        while True:
            image_ptr = self._camera.GetNextImage()

            if self._state is CameraState.STANDBY:
                self._change_state(CameraState.CAPTURING)

            if image_ptr.IsIncomplete():
                self._log.warning('received incomplete image!')

            self._current_frame = image_ptr.GetFrameID()

            # 判斷是否有開啟即時預覽或錄製，有的情況才執行影像處理
            if self._is_live_view or self._is_recording:
                camera_image = CameraImage(
                    image_ptr.GetData(),
                    image_ptr.GetWidth(),
                    image_ptr.GetHeight()
                )

                if self._is_live_view and not self._is_recording:
                    self._live_viewer.set_buffer(camera_image)

                if self._is_recording:
                    self._recorder.add_task(
                        self._current_frame,
                        camera_image
                    )

                    if self._stop_sign:
                        if len(self._recorder.get_record_frames()) > 0:
                            self._stop_recording()

            image_ptr.Release()

            if self._state is not CameraState.CAPTURING:
                break

    def _end_capture(self):
        """結束擷取

        關閉擷取相關的功能，即時預覽、錄製跟 PySpin

        """
        self._log.info('Stop capture')
        self.stop_live_view()
        self.stop_recording()
        self._camera.EndAcquisition()

    def _change_state(self, state):
        """改變相機狀態

        Args:
            state: CameraState 相機狀態

        """
        self._log.info(f'Change to state: {state.name}')
        self._state = state

    def get_shot_file_path_for_recording(self, shot_id):
        """取得 shot 的檔案位置

        Args:
            shot_id: Shot ID

        """
        return f'{self._record_folder_path}{shot_id}_{self._id}'

    def stop_capture(self):
        """停止擷取

        將狀態改成 CameraState.CLOSE
        如果相機還在等待觸發的狀態直接觸發

        """
        self._change_state(CameraState.CLOSE)

    def get_id(self):
        """取得ID"""
        return self._id

    def get_status(self):
        """取得相機狀態，回報給 master 用"""
        status = {
            'state': self._state.value,
            'current_frame': self._current_frame
        }

        if self._is_recording and self._recorder:
            status['record_frames_count'] = len(
                self._recorder.get_record_frames()
            )

        return status

    def start_recording(self, shot_id, is_cali):
        """開始錄製

        Args:
            shot_id: 錄製的 shot id，用以存檔的檔名

        """
        self._log.info('Start recording')
        shot_meta = CameraShotMeta(
            {'shot_id': shot_id, 'camera_id': self._id, 'is_cali': is_cali},
            self.get_shot_file_path_for_recording(shot_id)
        )
        self._recorder = CameraRecorder(shot_meta, self._log)
        self._is_recording = True
        self._stop_sign = False

    def _stop_recording(self):
        self._recorder.stop()
        self._recorder = None
        self._is_recording = False

    def stop_recording(self):
        """停止錄製"""
        if not self._stop_sign:
            self._log.info('Stop recording')
            self._stop_sign = True

    def start_live_view(self, quality, scale_length):
        """開始即時預覽

        Args:
            quality: JPEG品質
            scale_length: 最長邊長度

        """
        self._log.info('Start LiveView')
        self._live_viewer.apply_encode_parms({
            'quality': quality,
            'scale_length': scale_length
        })
        self._is_live_view = True

    def stop_live_view(self):
        """停止即時預覽"""
        self._log.info('Stop LiveView')
        self._is_live_view = False

    def load_shot_image(self, parms):
        """讀取 shot 圖像

        Args:
            parms: {camera_id, shot_id, frame, quality, scale_length}

        """
        meta = CameraShotMeta(
            parms,
            setting.get_shot_file_path(parms['shot_id'], parms['camera_id'])
        )
        self._log.info(f'Load frame {meta.frame} from {meta.shot_id}')

        self._shot_loader.add_task(meta)

    def change_parameter(self, parm_name, value):
        """更改相機參數

        利用 PySpin 去控制相機參數

        Args:
            parm_name: 參數名稱
            value: 參數數值

        """
        if self._configurator:
            self._configurator.apply_config({parm_name: value})

    def remove_shot(self, shot_id):
        """刪除 shot

        刪除硬碟內的 shot 檔案，用另外的 thread 執行不阻擋主程序

        Args:
            shot_id: Shot ID

        """
        shot_file_path = setting.get_shot_file_path(shot_id, self._id)
        self._log.info(f'Remove shot file: {shot_id}')

        def remove_shot_file():
            self._shot_loader.on_shot_will_remove(shot_file_path)

            for ext in (
                CameraShotFileCore.image_ext,
                CameraShotFileCore.meta_ext
            ):
                file = shot_file_path + ext
                if os.path.isfile(file):
                    os.remove(file)

        t = Thread(target=remove_shot_file)
        t.start()

    def retrigger(self):
        self._is_retrigger = True
        self.stop_capture()

    def add_submit_task(self, task):
        self._submitter.add_task(task)

    def clear(self):
        self._submitter.stop()
        self._log.debug('Stop submitter')
        self._configurator.stop()
        self._log.debug('Stop configurator')
        self._live_viewer.stop()
        self._log.debug('Stop live viewer')
        self._shot_loader.stop()
        self._log.debug('Stop shot loader')
        del self._camera
        del self._configurator
