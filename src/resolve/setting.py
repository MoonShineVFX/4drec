# -*- coding: future_fstrings -*-
import yaml
import os
import sys
import json
if sys.version_info[0] < 3:
    from pathlib2 import Path
else:
    from pathlib import Path

from define import ResolveStep


class Setting():
    def __init__(
        self, frame, alicevision_path, aruco_path, shot_path, job_path, cali_path,
        resolve_steps, gpu_core
    ):
        export_path = job_path
        if cali_path is not None:
            export_path += 'export/'

        self._data = WrapProperty({
            'frame': frame,
            'alicevision_path': alicevision_path,
            'aruco_path': aruco_path,
            'shot_path': shot_path,
            'job_path': job_path,
            'cali_path': cali_path,
            'resolve_steps': resolve_steps,
            'export_path': export_path,
            'gpu_core': gpu_core
        })

        with open('setting.yaml', 'r') as f:
            self._data.update(yaml.load(f, Loader=yaml.FullLoader))

    def __getattr__(self, attr):
        return getattr(self._data, attr)

    def set(self, prop, value):
        self._data[prop] = value

    def is_cali(self):
        return self.cali_path is None

    def get_job_id(self):
        return Path(self.job_path).stem

    def get_environment(self):
        env = os.environ.copy()
        if self.gpu_core != -1:
            env['CUDA_VISIBLE_DEVICES'] = str(self.gpu_core)
        return env

    def get_python_executable_path(self):
        if sys.version_info[0] < 3:
            return self._data['src_path'] + 'resolve.bat'
        else:
            return str(Path().parent.joinpath('resolve.bat'))

    @property
    def frame_path(self):
        if self.is_cali():
            return f'{self.job_path}'
        return f'{self.job_path}{self.frame:06d}/'

    def to_argument(self):
        data = self._data.copy()
        if 'resolve_steps' in data:
            data['resolve_steps'] = [
                step.value for step in data['resolve_steps']
            ]
        return json.dumps(data, ensure_ascii=True)

    def from_json(self, arg):
        data = json.loads(arg)
        if 'resolve_steps' in data:
            enum_steps = []
            for step in data['resolve_steps']:
                result = None
                for es in ResolveStep:
                    if es.value == step:
                        result = es
                if result is None:
                    raise KeyError(f'No found key: {step}')
                enum_steps.append(result)
            data['resolve_steps'] = enum_steps

        self._data.update(data)


class WrapProperty(dict):
    def __init__(self, value):
        super(WrapProperty, self).__init__()
        self.update(value)

    def __getattr__(self, attr):
        if attr not in self:
            raise AttributeError(
                f'{attr} not found in {self}'
            )

        value = self[attr]
        if isinstance(value, dict):
            return WrapProperty(value)
        else:
            return value
