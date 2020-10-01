import json

from pymongo import MongoClient

from utility.deadline import DeadlineConnect
from utility.setting import setting
from utility.logger import log


# 連線 deadline
deadline = DeadlineConnect.DeadlineCon(*setting.get_deadline_address())

# mongodb
DMC = MongoClient(setting.deadline_mongo.ip, setting.deadline_mongo.port)
JOBS = DMC.deadline10db.Jobs
TASKS = DMC.deadline10db.JobTasks
DELETES = DMC.deadline10db.DeletedJobs


def check_deadline_server():
    try:
        deadline.Repository.GetWindowsAlternateAuxiliaryPath()
    except Exception as error:
        return str(error)

    return ''


def submit_deadline(project_name, shot, job):
    """將專案放算到 Deadline

    Args:
        shot: Shot
        frame_range: 影格範圍

    """
    is_cali = shot.is_cali()

    shot_path = f'{setting.submit_shot_path}{shot.get_id()}/'

    if is_cali:
        job_path = f'{setting.submit_cali_path}{job.get_id()}/'
    else:
        job_path = f'{setting.submit_job_path}{job.get_id()}/'

    label = 'C' if is_cali else 'R'

    # 函式制訂
    def submit_job(step, _job_info):
        """在 deadline 新增排程工作，並返回 job id

        Args:
            _job_info: 要覆蓋的 job 資料
            plugin_info: 要覆蓋的 plugin 資料

        """
        extra_info_dict = {
            'resolve_step': step,
            'shot_path': shot_path,
            'job_path': job_path,
            'parameters': json.dumps(job.parameters, ensure_ascii=True)
        }

        if not is_cali:
            extra_info_dict['cali_path'] = f'{setting.submit_cali_path}{job.get_cali_id()}/'

        count = 0
        extra_info = {}
        for key, value in extra_info_dict.items():
            extra_info[f'ExtraInfoKeyValue{count}'] = f'{key}={value}'
            count += 1

        job_info = {
            'Plugin': '4DREC',
            'BatchName': f'[4D][{label}] {project_name} - {shot.name} - {job.name} ' +
                         f'({job.get_id()})',
            'Name': f'{submit_job.count} - {step} ({job.get_id()})',
            'UserName': 'develop',
            'ChunkSize': '1',
            'Pool': '4drec',
            'Frames': ','.join([str(f) for f in job.frames]),
            'OutputDirectory0': job_path,
            **_job_info,
            **extra_info
        }

        result = deadline.Jobs.SubmitJob(job_info, {})

        if isinstance(result, dict) and '_id' in result:
            log.info(f"Deadline submitted: {job_info['Name']}")
            submit_job.count += 1
            return result['_id']

        return None

    submit_job.count = 0
    ids = []

    if is_cali:
        # calibrate
        calibrate_id = submit_job(
            'calibrate',
            {
                'Group': '4DREC_cpu',
                'Priority': '80',
                'Frames': '0'
            }
        )
        if calibrate_id is None:
            return None

        # feature
        feature_id = submit_job(
            'feature',
            {
                'Group': '4DREC_cpu',
                'Priority': '80',
                'JobDependencies': calibrate_id,
                'Frames': '0'
            }
        )
        if feature_id is None:
            return None

        ids = [calibrate_id, feature_id]
    else:
        # feature
        feature_id = submit_job(
            'feature',
            {
                'Group': '4DREC_cpu',
                'Priority': '70',
                'JobDependencies': job.parameters['cali'][1]
            }
        )
        if feature_id is None:
            return None

        # depth
        depth_id = submit_job(
            'depth',
            {
                'Group': '4DREC_gpu',
                'Priority': '75',
                'JobDependencies': feature_id,
                'IsFrameDependent': 'true'
            }
        )
        if depth_id is None:
            return None

        # mesh
        mesh_id = submit_job(
            'mesh',
            {
                'Group': '4DREC_cpu',
                'Priority': '80',
                'JobDependencies': depth_id,
                'IsFrameDependent': 'true'
            }
        )
        if mesh_id is None:
            return None

        ids = [feature_id, depth_id, mesh_id]

    return ids


def get_task_list(deadline_id):
    is_delete = DELETES.find_one({'_id': deadline_id})
    if is_delete is not None:
        return {}

    task_list = {}
    tasks = TASKS.find({'JobID': deadline_id})

    for task in tasks:
        frame = task['Frames'].split('-')[0]
        state = task['Stat']
        task_list[frame] = state

    return task_list
