from time import perf_counter

from utility.setting import setting
from utility.logger import log
from utility.define import MessageType, UIEventType

from master.projects import project_manager
from master.ui import ui


class CameraReportCollector():
    """報告搜集器

    由於相機分散在各 slave，當需要得到特定報告時
    需要一個接收端將報告都蒐集齊並整理
    每個報告都會是一個 ReportContainer 物件

    """

    def __init__(self):
        self._report_container_list = []  # ReportContainer 陣列

    def new_record_report_container(self, shot_id, parameters):
        """創建新錄製報告搜集器

        錄製結束後，每個相機錄製報告的蒐集

        Args:
            shot_id: 錄製的 Shot ID
            parameters: 錄製當下的相機參數

        """
        self._report_container_list.append(
            RecordReportContainer(
                self,
                shot_id,
                parameters
            )
        )

    def new_submit_report_container(self, shot, name, frames, parameters):
        """創建新發佈報告搜集器

        發布 Shot 後，接收每個 Slave 的發送進度

        Args:
            shot_id: 要發布的 Shot ID

        """
        self._report_container_list.append(
            SubmitReportContainer(
                self, shot, name, frames, parameters
            )
        )

    def import_message(self, message):
        """匯入報告

        檢查進來的訊息種類，歸類到對應的搜集器

        Args:
            message: 訊息

        """
        report = message.unpack()
        for report_container in self._report_container_list:
            # 如果是錄製報告
            if (
                message.type is MessageType.RECORD_REPORT and
                isinstance(report_container, RecordReportContainer) and
                report_container.get_shot_id() == report['shot_id']
            ):
                report_container.import_report(report)
                break
            # 如果是發佈報告
            if (
                message.type is MessageType.SUBMIT_REPORT and
                isinstance(report_container, SubmitReportContainer) and
                report_container.get_shot_id() == report['shot_id'] and
                report_container.get_job_name() == report['job_name']
            ):
                report_container.import_report(report)
                break

    def on_report_container_summarized(self, report_container):
        """當 ReportContainer 做完總結的處理

        主要是給 ReportContainer 做連結，讓搜集器可以從列表刪除

        Args:
            report_container: 做完總結的 ReportContainer

        """
        self._report_container_list.remove(report_container)


class ReportContainer():
    """回報容器

    管理報告的容器，每個容器都有基本的預設流程
    匯入報告 -> 達成總結條件 ->  做總結
                           !-> 繼續等待匯入報告

    Args:
        collector: 搜集器，連結回報完的回調用
        shot_id: Shot ID

    """

    def __init__(self, collector, shot_id):
        self._shot_id = shot_id  # Shot ID

        # 連結回調
        self._on_report_container_summarized = (
            collector.on_report_container_summarized
        )

    def get_shot_id(self):
        """取得 Shot ID"""
        return self._shot_id

    def _import_report(self, report):
        """匯入報告的實際函式"""
        pass

    def import_report(self, report):
        """外部調用的匯入

        先執行實際匯入的函式，然後偵測是否需要做總結

        Args:
            report: 匯入的報告

        """
        self._import_report(report)

        # 偵測總結條件
        if self._summarize_condition():
            self.summarize_report()

    def _summarize_condition(self):
        """做總結的條件，回傳 True 來通過"""
        pass

    def _summarize_report(self):
        """總結的實際函式"""
        pass

    def summarize_report(self):
        """先執行實際做總結的函式，然後發送搜集器的回調"""
        self._summarize_report()
        self._on_report_container_summarized(self)


class RecordReportContainer(ReportContainer):
    """錄製回報容器

    Args:
        collector: 搜集器，連結回報完的回調用
        shot_id: Shot ID
        parameters: 相機錄製時的參數

    """

    def __init__(self, collector, shot_id, parameters):
        super().__init__(collector, shot_id)
        self._parameters = parameters  # 相機參數
        self._reports = []  # 匯入的報告

    def _import_report(self, report):
        """匯入報告"""
        self._reports.append(report)

    def _summarize_condition(self):
        """總結條件，當報告等於相機數量時 /dev"""
        return len(self._reports) == len(setting.get_working_camera_ids())
        # return len(self._reports) == 6

    def _summarize_report(self):
        """總結

        找出所有失蹤格數與最大最小格數，並更新 Shot 的資料

        """
        # 總容量大小與最大、最小的格數
        start_frames = []
        end_frames = []
        size = 0

        for r in self._reports:
            start_frames.append(r['frame_range'][0])
            end_frames.append(r['frame_range'][1])
            size += r['size']

        start_frame = max(start_frames)  # 讓開始格數齊頭
        end_frame = min(end_frames)  # 讓結束格數齊尾

        # 失蹤格數，藉由開始結尾跟相機編號所設立
        missing_frames = {}
        for r in self._reports:
            frames = r['missing_frames']
            missing_frames[r['camera_id']] = (
                [f for f in frames if f >= start_frame and f <= end_frame]
            )

        data = {
            'frame_range': (start_frame, end_frame),
            'size': size,
            'missing_frames': missing_frames,
            'camera_parameters': self._parameters,
            'state': 1
        }

        # 更新資料庫
        log.info('Update shot with recorded data')
        shot = project_manager.get_shot(self._shot_id)
        shot.update(data)


class SubmitReportContainer(ReportContainer):
    """Shot 發布容器

    Args:
        collector: 搜集器，連結回報完的回調用
        shot_id: Shot ID

    """

    def __init__(self, collector, shot, name, frames, parameters):
        super().__init__(collector, shot.get_id())
        self._shot = shot
        self._name = name
        self._frames = frames  # 影格範圍
        self._parameters = parameters
        self._progress_list = {}  # 進度表{相機ID: 進度(0~1)}
        self._complete_check_list = {}

        # 先建立對應表
        for camera_id in setting.get_working_camera_ids():
            self._progress_list[camera_id] = 0
            self._complete_check_list[camera_id] = False

    def _import_report(self, report):
        """匯入報告"""
        from master.ui import ui

        progress = report['progress']
        self._progress_list[report['camera_id']] = progress[0]
        self._complete_check_list[report['camera_id']] = progress[0] == progress[1]

        ui.dispatch_event(
            UIEventType.TICK_SUBMIT,
            sum(self._progress_list.values())
        )

    def _summarize_condition(self):
        """總結條件，全部傳輸進度都完成"""
        # 全部完成即為 1
        if all(self._complete_check_list.values()):
            return True

        return False

    def _summarize_report(self):
        """總結"""
        if setting.is_disable_deadline():
            ui.dispatch_event(
                UIEventType.NOTIFICATION,
                {
                    'title': f'[{self._name}] Transfer Success',
                    'description': (
                        f'Shot [{self._name}] transfer with {len(self._frames)} frames.'
                    )
                }
            )
        else:
            self._shot.submit(self._name, self._frames, self._parameters)

    def get_job_name(self):
        return self._name
