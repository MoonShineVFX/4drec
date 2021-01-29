from utility.logger import log
from utility.message import message_manager
from utility.define import EntityEvent, UIEventType, MessageType
from utility.setting import setting

from master.ui import ui

from .database import (
    get_projects, ProjectEntity, ShotEntity,
    JobEntity, get_calibrations
)
from .deadline import check_deadline_server


class ProjectManager():
    """專案管理員

    專案資料庫與介面的控制仲介

    """

    def __init__(self):
        self.current_project = None  # 目前選擇的專案
        self.current_shot = None  # 目前選擇的 Shot
        self.current_job = None
        self._projects = self._load_projects()  # 專案，從 database 讀取

        ui.dispatch_event(
            UIEventType.PROJECTS_INITIALIZED,
            list(self._projects)
        )

        """
        選擇過的 Shot，主要是為了在找 Shot 時可以比較快的找到
        """
        self._selected_shots = {}
        self._selected_jobs = {}
        self._selected_projects = {}

        # 自動選擇最近的 project 跟 shot
        if len(self._projects) > 0:
            self.select_project(self._projects[0])

    @property
    def projects(self):
        return self._projects

    def _load_projects(self):
        """讀取專案

        從資料庫讀取專案，並註冊回調

        """
        projects = get_projects(self.on_entity_event, self.on_entity_event)
        return projects

    def select_project(self, project):
        """選擇專案

        選擇專案，如果專案已有 Shot，會選擇最新的 Shot

        """
        self.current_project = project
        if project.get_id() not in self._selected_projects:
            self._selected_projects[project.get_id()] = project

        if project:
            log.info(f'Select project: {project}')
            if len(project.shots) != 0:
                self.select_shot(project.shots[0])
            else:
                self.select_shot(None)
        else:
            log.info('Select project: Empty')
            if self.current_shot is not None:
                self.select_shot(None)

        ui.dispatch_event(UIEventType.PROJECT_SELECTED, project)

    def select_shot(self, shot):
        """選擇 Shot

        選擇 Shot 後，會在 self._selected_shots 新增以便之後快速存取

        """
        if shot:
            log.info(f'Select shot: {shot}')
            if shot.get_id() not in self._selected_shots:
                self._selected_shots[shot.get_id()] = shot
        else:
            log.info('Select shot: Empty')

        self.current_shot = shot
        ui.dispatch_event(UIEventType.SHOT_SELECTED, shot)

    def select_job(self, job):
        if job:
            log.info(f'Select job: {job}')
            if job.get_id() not in self._selected_jobs:
                self._selected_jobs[job.get_id()] = job
        else:
            log.info('Select job: Empty')

        self.current_job = job
        ui.dispatch_event(UIEventType.JOB_SELECTED, job)

    def create_project(self, name):
        """創建專案

        Args:
            name: 專案名稱

        """
        project = ProjectEntity({'name': name}, self.on_entity_event)
        self._projects.insert(0, project)

        ui.dispatch_event(UIEventType.PROJECT_MODIFIED, [*self._projects])
        return project

    def on_entity_event(self, event, entity):
        """聆聽實體事件

        當專案與 Shot 有事件發生時的處理

        Args:
            event: 實體事件
            entity: 發生事件的實體

        """
        # 如果有實體刪除
        if event is EntityEvent.REMOVE:
            # 專案: 同時在 self._projects 刪除並確認是否是 current 來清空
            if isinstance(entity, ProjectEntity):
                log.info('Remove project: {}'.format(entity))
                self._projects.remove(entity)
                ui.dispatch_event(
                    UIEventType.PROJECT_MODIFIED, [*self._projects]
                )
                if self.current_project == entity:
                    self.select_project(None)
            # Shot: 如果是 current 清空，並傳送給 slave 通知刪除檔案
            elif isinstance(entity, ShotEntity):
                log.info('Remove shot: {}'.format(entity))
                if self.current_shot == entity:
                    self.select_shot(None)

                ui.dispatch_event(
                    UIEventType.SHOT_MODIFIED,
                    [*self.current_project.shots]
                )

                message_manager.send_message(
                    MessageType.REMOVE_SHOT,
                    {'shot_id': entity.get_id()}
                )
            elif isinstance(entity, JobEntity):
                log.info('Remove job: {}'.format(entity))
                if self.current_job == entity:
                    self.select_job(None)

                ui.dispatch_event(
                    UIEventType.JOB_MODIFIED,
                    [*self.current_shot.jobs]
                )

        # 如果有實體創建
        elif event is EntityEvent.CREATE:
            log.info(f'Create {entity.print_name}: {entity}')

            if isinstance(entity, ShotEntity):
                ui.dispatch_event(
                    UIEventType.SHOT_MODIFIED,
                    [*self.current_project.shots]
                )
                self.select_shot(entity)

            elif isinstance(entity, JobEntity):
                ui.dispatch_event(
                    UIEventType.JOB_MODIFIED,
                    [*self.current_shot.jobs]
                )

        # 如果有實體更改
        elif event is EntityEvent.MODIFY:
            log.info(f'Modify:\n {entity.print_name}')

    def get_project(self, project_id):
        return self._selected_projects[project_id]

    def get_shot(self, shot_id):
        """取得有選擇過的 shot

        Args:
            shot_id: Shot ID

        """
        return self._selected_shots[shot_id]

    def get_job(self, job_id):
        return self._selected_jobs[job_id]

    def get_all_cache_size(self):
        memory = 0
        for shot in self._selected_shots.values():
            memory += shot.get_cache_size()
        for job in self._selected_jobs.values():
            memory += job.get_cache_size()
        return memory / (1024 ** 3)

    def check_deadline_server(self):
        if setting.is_disable_deadline():
            ui.dispatch_event(
                UIEventType.DEADLINE_STATUS,
                True
            )
            return

        check_result = check_deadline_server()
        if check_result != '':
            ui.dispatch_event(
                UIEventType.NOTIFICATION,
                {
                    'title': 'Deadline Connection Error',
                    'description': check_result
                }
            )

        ui.dispatch_event(
            UIEventType.DEADLINE_STATUS,
            check_result == ''
        )

    def update_cali_list(self):
        calis = get_calibrations()
        result = []
        for cali in calis:
            name = f'{cali["name"]}  -  '\
                   f'{cali["_id"].generation_time:%m/%d %H:%M}'
            value = (str(cali['_id']), cali['deadline_ids'][-1])
            result.append((name, value))

        ui.dispatch_event(
            UIEventType.CALI_LIST,
            result
        )