import time

from utility.setting import setting
from utility.message import message_manager, Message
from utility.logger import log
from utility.repeater import Repeater
from utility.define import UIEventType, CameraState, MessageType
from utility.delay_executor import DelayExecutor

from master.ui import ui
from master.projects import project_manager
from master.hardware_trigger import hardware_trigger

from .proxy import CameraProxy
from .parameter import CameraParameter
from .report_collector import CameraReportCollector
from .mpd_modifier import MPDModifier
from .jpeg_trimmer import JPEGTrimmer


class CameraSaveMeta():
    def __init__(self, shot_id, frame, path):
        self._shot_id = shot_id
        self._frame = frame
        self._path = path
        self._cameras = {
            camera: False for camera in setting.get_working_camera_ids()
        }

    def save(self, camera_id, image_data):
        with open(f'{self._path}/{camera_id}_{self._frame:06d}.jpg', 'wb') as f:
            f.write(image_data)
        self._cameras[camera_id] = True
        return all(self._cameras.values())


class CameraManager():
    """相機管理總成

    負責 slave 訊息過來的相機資訊歸納
    將相機的狀態重現出來，並用來做操控 slave 相機的橋梁

    """

    def __init__(self):
        # 狀態
        self._is_recording = False  # 錄製中
        self._is_live_view = False  # 預覽中
        self._is_capturing = False

        self._mpd_modifier = None
        self._jpeg_trimmer = None

        self._camera_list = self._build_camera_proxies()  # 相機 proxy 列表
        self._parameters = self._build_parameters()  # 相機可控參數
        self._report_collector = CameraReportCollector()  # 相機報告蒐集
        self._ui_status_sender = Repeater(self._send_ui_status, 0.1, True)
        self._camera_status_requester = Repeater(
            self._request_camera_status, 0.1, True
        )
        self._delay = DelayExecutor(0.1)

        self._save_meta = None

        # 綁定 UI
        ui.dispatch_event(
            UIEventType.UI_CONNECT,
            {
                'camera': self,
                'project': project_manager
            }
        )

        self.load_parameters('Default')

    def _build_camera_proxies(self):
        """藉由 setting.get_working_camera_ids 創建相機 proxy 列表"""
        camera_list = {}
        for camera_id in setting.get_working_camera_ids():
            camera_list[camera_id] = CameraProxy(
                camera_id,
                self._on_state_changed
            )
        return camera_list

    def _build_parameters(self):
        """藉由 setting.camera_parameters 創建參數列表"""
        parameters = {}
        for key, parm in setting.camera_parameters.items():
            parameters[key] = CameraParameter(
                key,
                parm['min'],
                parm['max'],
                parm['default'],
                parm['type']
            )

        return parameters

    def update_status(self, message):
        """更新相機狀態

        將 slave 回報的相機狀態更新到 proxy

        Args:
            message: 回報訊息

        """
        data = message.unpack()
        for camera_id, camera in self._camera_list.items():
            if camera_id in data:
                camera.update_status(data[camera_id])

    def _on_state_changed(self, camera):
        """當相機狀態改變的回調

        相機狀態改變的通知，用來驅動整個總成的流程

        Args:
            camera: 狀態改變的相機

        """
        # 有相機為等待觸發狀態，確定全部相機皆在等待後，開始擷取
        if camera.state is CameraState.STANDBY and not self._is_capturing:
            if self.check_all_state(CameraState.STANDBY):
                self.trigger()

        # 當擷取關閉，預覽卻未關閉的情況下，送出斷線圖像給 UI
        if (
            camera.state is not CameraState.CAPTURING and
            self._is_live_view
        ):
            self.receive_image(
                Message(
                    MessageType.LIVE_VIEW_IMAGE,
                    parms={'camera_id': camera.get_id()},
                    payload=None
                )
            )

    def change_parameter(self, parm_name, value, affect_slider=False):
        """改變相機參數

        會驗證參數在 setting 所設定的最大最小值，通過後再送給 slave

        Args:
            parm_name: 參數名稱
            value: 參數數值

        """
        if self._is_recording:
            log.error("Can't change parameter due to wrong camera state")
            return

        parm = self._parameters[parm_name]
        result = parm.set(value)

        if result == 'min':
            log.error(f'{parm_name} value too small ({value})')
        elif result == 'max':
            log.error(f'{parm_name} value too big ({value})')
        elif result == 'OK':
            message_manager.send_message(
                MessageType.CAMERA_PARM,
                {'camera_parm': (parm_name, parm.get_value())}
            )
            log.debug(f'Parameter <{parm_name}> changes to {value}')
            ui.dispatch_event(
                UIEventType.CAMERA_PARAMETER,
                (parm_name, value, affect_slider)
            )

    def save_parameters(self):
        save_parms = {}
        for name, parm in self._parameters.items():
            save_parms[name] = parm.get_value()
        setting.save_camera_parameters(save_parms)

    def check_all_state(self, state):
        """確認所有相機是否在指定狀態

        Args:
            state: 指定的相機狀態

        """
        return all(
            camera.state is state for camera in self._camera_list.values()
        )

    def trigger(self):
        """觸發相機擷取"""
        log.info('Trigger camera capture')
        hardware_trigger.trigger()

        # 觸發後，將相機參數做統一設定
        for name, parm in self._parameters.items():
            self.change_parameter(
                name, parm.get_value()
            )

        ui.dispatch_event(
            UIEventType.TRIGGER,
            True
        )

        self._is_capturing = True

    def retrigger(self):
        log.info('Retrigger')

        message_manager.send_message(
            MessageType.RETRIGGER
        )

        self.stop_capture()

    def load_parameters(self, preset_type):
        if preset_type == 'Default':
            if setting.has_user_parameters():
                preset_type = 'User'
            else:
                preset_type = 'Base'

        if preset_type == 'Base':
            for name, parm in self._parameters.items():
                self.change_parameter(
                    name, parm.get_default(), True
                )
        elif preset_type == 'User':
            for name, parm in self._parameters.items():
                if not setting.has_user_parameters():
                    return
                self.change_parameter(
                    name, setting.camera_user_parameters[name], True
                )

    def live_view(
        self, toggle, scale_length=150, close_up=None
    ):
        """開關相機預覽

        開關指定的相機預覽，同時設定串流品質跟尺寸

        Args:
            camera_ids: [相機ID]
            quality: 串流品質
            scale_length: 最長邊長度

        """

        if toggle:
            self._delay.execute(
                lambda:
                (
                    log.info('Toggle LiveView on'),
                    message_manager.send_message(
                        MessageType.TOGGLE_LIVE_VIEW,
                        {
                            'quality': setting.jpeg.live_view.quality,
                            'scale_length': scale_length,
                            'close_up': close_up,
                            'toggle': toggle
                        }
                    ),
                    ui.dispatch_event(
                        UIEventType.LIVE_VIEW,
                        True
                    )
                )
            )
        else:
            log.info('Toggle LiveView off')
            message_manager.send_message(
                MessageType.TOGGLE_LIVE_VIEW,
                {
                    'toggle': toggle
                }
            )
            ui.dispatch_event(
                UIEventType.LIVE_VIEW,
                False
            )

    def record(self):
        """開關錄製

        根據目前的 shot 選擇去啟動錄製
        如果已在錄製中便關閉，並創建該 shot 的錄製回報蒐集器

        """
        self._is_recording = not self._is_recording

        ui.dispatch_event(
            UIEventType.RECORDING,
            self._is_recording
        )

        parms = {
            'is_start': self._is_recording
        }

        shot_id = project_manager.current_shot.get_id()
        is_cali = project_manager.current_shot.is_cali()
        start_record_frame = max([camera.get_current_frame() for camera in self._camera_list.values()]) + 90

        # 開啟錄製
        if self._is_recording:
            parms['shot_id'] = shot_id
            parms['is_cali'] = is_cali
            parms['start_record_frame'] = start_record_frame
            log.info('Start recording: {} / {}'.format(
                project_manager.current_project,
                project_manager.current_shot
            ))
            self._mpd_modifier = MPDModifier()
            self._jpeg_trimmer = JPEGTrimmer()
        # 關閉錄製
        else:
            log.info('Stop recording')

            # 取得這次錄製的相機參數
            parameters = {}
            for name, parm in self._parameters.items():
                parameters[name] = parm.get_value()

            # 建立錄製報告容器
            self._report_collector.new_record_report_container(
                shot_id, parameters
            )

            self._mpd_modifier.stop()
            self._jpeg_trimmer.stop()
            self._mpd_modifier = None
            self._jpeg_trimmer = None

        message_manager.send_message(
            MessageType.TOGGLE_RECORDING,
            parms
        )

        if self._is_recording and is_cali:
            self.record()

    def stop_capture(self, message=None):
        """停止擷取

        主要是用在有 slave 斷線的情況，或者要重置相機擷取的格數

        """
        for camera in self._camera_list.values():
            camera.update_status({'state': CameraState.CLOSE.value})

        if self._is_capturing and message is not None:
            node = message.unpack()
            log.warning(f'Slave [{node.get_name()}] down, restart cameras')
            time.sleep(1)
            message_manager.send_message(MessageType.MASTER_DOWN)

        self._is_capturing = False

        ui.dispatch_event(
            UIEventType.TRIGGER,
            False
        )

    def collect_report(self, message):
        """蒐集報告

        將報告匯入到報告搜集器

        Args:
            message: 報告訊息

        """
        self._report_collector.import_message(message)

    def receive_image(self, message):
        """收到圖像

        有 slave 傳圖像過來便會用此函式傳給 proxy 處理

        Args:
            message: 圖像訊息

        """
        parms, image_data = message.unpack()

        if self._save_meta is not None:
            result = self._save_meta.save(parms['camera_id'], image_data)
            if result:
                self._save_meta = None
            return

        self._camera_list[parms['camera_id']].on_image_received(
            message
        )

    def request_shot_image(
        self, shot_id, frame, closeup_camera=None, delay=False
    ):
        """取得 shot 圖案

        UI 要圖像的方式，指定的相機找不到自己的緩衝有圖像時，會再向 slave 索取

        Args:
            shot_id: shot ID
            frame: 指定影格
            quality: 轉檔品質
            scale_length: 最長邊長度，預設不更動
            camera_ids: 相機ID列表

        """

        for camera_id, camera in self._camera_list.items():
            if closeup_camera == camera_id:
                scale_length = None
            else:
                scale_length = setting.jpeg.shot.scale_length

            camera.on_image_requested(
                camera_id, shot_id, frame,
                setting.jpeg.shot.quality,
                scale_length, delay
            )

    def request_save_image(self, frame, path):
        shot_id = project_manager.current_shot.get_id()
        self._save_meta = CameraSaveMeta(shot_id, frame, path)
        for camera_id, camera in self._camera_list.items():
            camera.on_image_requested(
                camera_id, shot_id, frame,
                setting.jpeg.submit.quality,
                None, False
            )

    def submit_shot(self, name, frames, parameters):
        """到 deadline 放算"""
        shot = project_manager.current_shot
        log.info(f'Preparing to submit shot: {shot}')

        self._report_collector.new_submit_report_container(
            shot,
            name,
            frames,
            parameters
        )

        # 通知 Slaves 傳輸轉檔 Shot
        message_manager.send_message(
            MessageType.SUBMIT_SHOT,
            {
                'shot_id': shot.get_id(),
                'job_name': name,
                'frames': frames
            }
        )

    def cache_whole_shot(self, closeup_camera):
        shot = project_manager.current_shot
        sf, ef = shot.frame_range

        for f in range(sf, ef + 1):
            self.request_shot_image(
                shot.get_id(), f, closeup_camera
            )

    def _get_bias(self):
        """取得相機實際擷取的格數誤差的最大值"""
        frames = [
            camera.current_frame
            for camera in self._camera_list.values()
        ]
        min_frame = min(frames)
        max_frame = max(frames)
        return max_frame - min_frame

    def _request_camera_status(self):
        message_manager.send_message(
            MessageType.CAMERA_STATUS,
            {
                'calibrate_frame': self._camera_list[
                    setting.get_working_camera_ids()[0]
                ].current_frame
            }
        )

    def _send_ui_status(self):
        status = {
            'bias': self._get_bias(),
            'slaves': message_manager.get_nodes_count(),
            'frames': -1,
            'cache_size': project_manager.get_all_cache_size()
        }

        if self._is_recording:
            status['frames'] = min(
                [
                    camera.record_frames_count for camera
                    in self._camera_list.values()
                ]
            )

        ui.dispatch_event(
            UIEventType.UI_STATUS,
            status
        )

    def offline(self):
        for camera in self._camera_list.values():
            camera.set_offline()
