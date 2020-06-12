from pymongo import MongoClient
from datetime import datetime
import pytz
from bson.codec_options import CodecOptions

from utility.logger import log
from utility.define import EntityEvent, CameraCacheType, TaskState, UIEventType
from utility.setting import setting
from utility.repeater import Repeater

from master.ui import ui

from .deadline import get_task_list, submit_deadline


# 資料庫設定
client = MongoClient(host=[setting.mongodb_address])

DB_ROOT = client['4drec']
DB_ROOT.with_options(
    codec_options=CodecOptions(
        tz_aware=True, tzinfo=pytz.timezone('Asia/Taipei')
    )
)

DB_SHOTS = DB_ROOT['shots']
DB_PROJECTS = DB_ROOT['projects']
DB_JOBS = DB_ROOT['jobs']


def get_projects(include_archived=False, callback=None):
    """取得所有專案

    Args:
        include_archived: 是否包含已封藏的專案

    """

    # 看是否要包含封藏的專案
    if include_archived:
        query = {}
    else:
        query = {'is_archived': False}

    projects = list(DB_PROJECTS.find(query).sort([('_id', -1)]))

    return [ProjectEntity(d, callback) for d in projects]


def get_calibrations():
    return list(DB_JOBS.find({'cali': True}).sort([('_id', -1)]))


class Entity():
    """文件實體

    資料庫的文件實體
    將類實例化也會連結到資料庫去創建
    藉由屬性取得元件的內容
    用 update 來設定元件屬性

    Args:
        db: 所屬 mongoDB 資料庫
        doc: 資料庫文件

    """

    def __init__(self, db, doc):
        self._db = db  # 所屬 mongodb 資料庫

        # 如果該 doc 不是資料庫文件，創建一份
        if '_id' not in doc:
            doc = self._create_document(doc)

        self._doc = doc

        self._callbacks = []  # 註冊的回調

    def _create_document(self, doc):
        """創建文件"""

        # 增加時間戳
        doc['last_modified'] = datetime.now()

        # 複製預設範本並將資料更新上去
        template = self._template.copy()
        template.update(doc)

        # 取得文件ID並返回資料庫文件
        _doc_id = self._db.insert_one(template).inserted_id
        new_doc = self._db.find_one({'_id': _doc_id})
        return new_doc

    def __getattr__(self, prop):
        # 如果是 _doc_id 返回文件ID
        if prop == '_doc_id':
            return self._doc['_id']
        elif prop == 'create_at_str':
            return f'{self._doc_id.generation_time:%Y-%m-%d %H:%M:%S}'
        else:
            if prop not in self._doc:
                raise KeyError('[{}] not found in <{}>'.format(
                    prop, self.__class__.__name__
                ))
            return self._doc[prop]

    def has_prop(self, prop):
        return prop in self._doc

    def rename(self, name):
        self.update({'name': name})

    def update(self, doc=None):
        """更新內容

        Args:
            doc: 要更新的資料，字典檔

        """
        if doc is not None:
            self._doc.update(doc)
            self._doc['last_modified'] = datetime.now()
            self._db.update_one({'_id': self._doc_id}, {'$set': self._doc})
        self.emit(EntityEvent.MODIFY, self)

    def register_callback(self, func):
        """註冊回調

        文件發生創建、更動、刪除的事件註冊回調

        Args:
            func: 回調的函式

        """
        if func not in self._callbacks:
            self._callbacks.append(func)

    def unregister_callback(self, func):
        if func in self._callbacks:
            self._callbacks.remove(func)

    def emit(self, event, entity):
        """產生事件訊號

        文件發生創建、更動、刪除的事件
        呼叫所有已註冊的回調

        Args:
            event: 實體事件
            entity: 發生事件的實體

        """
        to_del_funcs = []

        for func in self._callbacks:
            try:
                func(event, entity)
            except RuntimeError:
                to_del_funcs.append(func)

        for func in to_del_funcs:
            self._callbacks.remove(func)

    def remove(self):
        """刪除實體"""
        self._db.delete_one({'_id': self._doc_id})
        self.emit(EntityEvent.REMOVE, self)

    def get_detail(self):
        """實體的詳細內容，回傳 str"""
        msg = f'[{self.print_name}]\n'
        msg += '\n'.join(
            f'{key}: {getattr(self, key)}' for key in self._doc
        )
        for key, value in self._doc:
            if isinstance(value, list) and len(value) > 0:
                msg += f'{key}: [{value[0]}...{value[-1]}] ({len(value)})\n'
            else:
                msg += f'{key}: {value}\n'
        msg += f'\ncreate_at: {self.create_at_str}'
        return msg

    def get_id(self):
        """取得文件ID"""
        return str(self._doc_id)

    def __str__(self):
        return (
            f'{self.name} '
            f'[{self.create_at_str}]'
        )


class ProjectEntity(Entity):
    """專案實體

    專案的資料包裝，也會管理所屬的 shot

    """

    print_name = 'Project'

    # 專案資料範本
    _template = {
        'name': None,
        'shot_count': 1,
        'is_archived': False
    }

    def __init__(self, doc, callback=None):
        super().__init__(DB_PROJECTS, doc)
        self._shots = None  # shot 的元件實體陣列

        if callback is not None:
            self.register_callback(callback)

        self.emit(EntityEvent.CREATE, self)

    @property
    def shots(self):
        if self._shots is None:
            self._shots = self._initial_shots()
        return self._shots

    def _initial_shots(self):
        query = DB_SHOTS.find(
            {'project_id': self._doc_id}
        ).sort([('_id', -1)])

        shots = list(query)

        return [ShotEntity(self, s) for s in shots]

    def create_shot(self, is_cali, name=None):
        """創建 Shot

        Args:
            name: Shot 名稱，沒有的話便用預設前綴 + 創建數

        """
        # 名稱
        if name is None or name == '':
            name = 'Shot no.{}'.format(self.shot_count)

        # 創建
        shot = ShotEntity(
            self,
            {
                'project_id': self._doc_id,
                'name': name,
                'cali': is_cali
            },
        )

        # 更新資料庫和加到 self._shots
        self._shots.insert(0, shot)
        self.update({'shot_count': self.shot_count + 1})

        # 觸發創建事件
        self.emit(EntityEvent.CREATE, shot)

        return shot

    def get_overview(self):
        shots = 0
        resolve = 0
        length = 0
        size = 0

        query = DB_SHOTS.find(
            {'project_id': self._doc_id}
        )

        for shot in query:
            shots += 1
            if shot['state'] > 1:
                resolve += 1
            frame_range = shot['frame_range']
            if frame_range is not None:
                length += (
                    (frame_range[1] - frame_range[0] - 1) / 20
                )
            if shot['size'] is not None:
                size += shot['size']

        length = f'{int(length / 60)}:{int(length % 60):02d}'
        size = size / 1024 / 1024 / 1024
        size = f'{size:.2f}'.rstrip('0.')
        if not size:
            size = '0GB'

        return {
            'shots': shots,
            'resolve': resolve,
            'length': length,
            'size': size if size else '0'
        }

    def emit(self, event, entity):
        """觸發事件的回調

        專案的部分會接收 Shot 的事件，當 Shot 刪除時，自身資料也同步更新

        Args:
            event: 實體事件
            entity: 元件實體

        """

        if event == EntityEvent.REMOVE and entity in self.shots:
            self._shots.remove(entity)

        super().emit(event, entity)

    def remove(self):
        """刪除實體

        刪除自己時，也會同步刪除所屬的 Shots

        """
        shots = self._shots.copy()
        for shot in shots:
            shot.remove()

        super().remove()


class ShotEntity(Entity):
    """Shot 實體

    Shot 的資料包裝

    """

    print_name = 'Shot'

    # 專案資料範本
    _template = {
        'project_id': None,
        'name': None,
        'frame_range': None,
        'size': None,
        'missing_frames': None,
        'camera_parameters': None,
        'state': 0,  # created, recorded, submitted
        'cali': False
    }

    def __init__(self, parent, doc):
        super().__init__(DB_SHOTS, doc)
        self._jobs = None

        # 創建時會註冊所屬專案的事件
        self.register_callback(parent.emit)

        # caches
        self._cache_progress = {
            CameraCacheType.THUMBNAIL: {},
            CameraCacheType.ORIGINAL: {}
        }
        self._memory = 0

    @property
    def jobs(self):
        if self._jobs is None:
            self._jobs = self._initial_jobs()
        return self._jobs

    def _initial_jobs(self):
        query = DB_JOBS.find(
            {'shot_id': self._doc_id}
        ).sort([('_id', -1)])
        jobs = list(query)

        return [JobEntity(self, j) for j in jobs]

    def create_job(self, name, frames, parameters, is_cali):
        # 名稱
        if name is None or name == '':
            name = f'submit {len(self.jobs) + 1}'

        # 創建
        job = JobEntity(
            self,
            {
                'shot_id': self._doc_id,
                'name': name,
                'frames': frames,
                'parameters': parameters,
                'cali': is_cali
            }
        )

        self._jobs.insert(0, job)

        # 觸發創建事件
        self.emit(EntityEvent.CREATE, job)

        return job

    def emit(self, event, entity):
        if event == EntityEvent.REMOVE and entity in self.jobs:
            self._jobs.remove(entity)

        super().emit(event, entity)

    def update_cache_progress(self, camera_pixmap):
        self._memory += camera_pixmap.get_size()

        if camera_pixmap.get_cache_type() is CameraCacheType.THUMBNAIL:
            thumb_origin = self._cache_progress[
                CameraCacheType.THUMBNAIL
            ]
            unit = 1 / len(setting.cameras)
            if camera_pixmap.frame not in thumb_origin:
                thumb_origin[camera_pixmap.frame] = unit
            else:
                thumb_origin[camera_pixmap.frame] += unit
        else:
            camera_id = camera_pixmap.camera_id
            progress_origin = self._cache_progress[
                CameraCacheType.ORIGINAL
            ]
            if camera_id not in progress_origin:
                progress_origin[camera_id] = []

            progress_origin[camera_id].append(camera_pixmap.frame)

        self.emit(EntityEvent.PROGRESS, self)

    def get_cache_progress(self):
        return self._cache_progress

    def get_cache_size(self):
        return self._memory

    def submit(self, name, frames, parameters={}):
        job = self.create_job(name, frames, parameters, self.is_cali())

        # Deadline integration
        log.info(f'Deadline submit shot: {self}')

        deadline_ids = submit_deadline(self, job)

        if deadline_ids is None:
            log.error('Deadline submit server error!')
            job.remove()
            return

        log.info(f'Deadline submit done: {self}')

        ui.dispatch_event(
            UIEventType.NOTIFICATION,
            {
                'title': f'[{self.name}] Submit Success',
                'description': (
                    f'Shot [{self.name}] submitted with {len(frames)} frames.'
                )
            }
        )

        if self.state != 2:
            self.update({'state': 2})

        job.update({'deadline_ids': deadline_ids})

    def is_cali(self):
        if 'cali' in self._doc:
            return self.cali
        return False


class JobEntity(Entity):

    print_name = 'Job'

    # 專案資料範本
    _template = {
        'shot_id': None,
        'deadline_ids': [],
        'name': None,
        'frames': None,
        'parameters': {},
        'state': 0,  # created, resolved
        'task_list': {},
        'cali': False
    }

    def __init__(self, parent, doc):
        super().__init__(DB_JOBS, doc)
        # 創建時會註冊所屬專案的事件
        self.register_callback(parent.emit)

        # caches
        self._cache_progress = []
        self._deadline_tasks = self._get_deadline_tasks()
        self._memory = 0

        if self.state == 0:
            self._repeater = Repeater(self._update_deadline_tasks, 60, True)

    def _get_deadline_tasks(self):
        return {
            int(key): TaskState(value) for key, value in self.task_list.items()
        }

    def _update_deadline_tasks(self):
        if len(self.deadline_ids) == 0:
            return

        task_list = get_task_list(self.deadline_ids[-1])
        if task_list == self.task_list:
            return

        self.update({'task_list': task_list})

        self._deadline_tasks = self._get_deadline_tasks()
        self.emit(EntityEvent.PROGRESS, self)

        if all(
            [s is TaskState.COMPLETED for s in self._deadline_tasks.values()]
        ):
            self._repeater.stop()
            self.update({'state': 1})

    def update_cache_progress(self, frame, size):
        self._memory += size
        self._cache_progress.append(frame)
        self.emit(EntityEvent.PROGRESS, self)

    def get_cache_progress(self):
        return self._cache_progress, self._deadline_tasks

    def get_cache_size(self):
        return self._memory

    def get_completed_count(self):
        return len(
            [
                t for t in self._deadline_tasks.values()
                if t is TaskState.COMPLETED
            ]
        )

    def is_cali(self):
        if 'cali' in self._doc:
            return self.cali
        return False

    def get_cali_id(self):
        if self.is_cali():
            return self.get_id()
        return self.parameters['cali'][0]
