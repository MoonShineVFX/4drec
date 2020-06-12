# -*- coding: future_fstrings -*-
import re
import json

from reference import process

from .flow import PythonFlow, Flow, FlowCommand
from .calibrate import AlignStructure


class ConvertSFM(PythonFlow):
    _file = {
        'sfm': 'out.sfm'
    }

    def __init__(self):
        super(ConvertSFM, self).__init__()

    def run_python(self):
        load_sfm_path = AlignStructure.get_file_path('sfm')
        if not process.setting.is_cali():
            load_sfm_path = StructureFromMotion.get_file_path_with_folder(
                'sfm', process.setting.cali_path
            )

        with open(load_sfm_path) as f:
            data = json.load(f)

        if not process.setting.is_cali():
            for key in ('featuresFolders', 'matchesFolders', 'structure'):
                if key in data:
                    del data[key]

            for view in data['views']:
                view['path'] = f'{process.setting.shot_path}' \
                               f'{view["viewId"]}' \
                               f'_{process.setting.frame:06d}.jpg'

        with open(self.get_file_path('sfm'), 'w') as f:
            json.dump(data, f)


class FeatureExtraction(Flow):
    def __init__(self):
        super(FeatureExtraction, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_featureExtraction'
            ),
            args={
                'input': ConvertSFM.get_file_path('sfm'),
                'describerTypes': 'akaze',
                'describerPreset': 'ultra',
                'forceCpuExtraction': 1,
                'output': self.get_folder_path()
            }
        )


class FeatureMatching(Flow):
    def __init__(self):
        super(FeatureMatching, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_featureMatching'
            ),
            args={
                'input': ConvertSFM.get_file_path('sfm'),
                'featuresFolders': FeatureExtraction.get_folder_path(),
                'describerTypes': 'akaze',
                'output': self.get_folder_path()
            }
        )


class StructureFromMotion(Flow):
    _file = {
        'sfm': 'struct.sfm'
    }

    def __init__(self):
        super(StructureFromMotion, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_incrementalSfM'
            ),
            args={
                'input': ConvertSFM.get_file_path('sfm'),
                'featuresFolders': FeatureExtraction.get_folder_path(),
                'matchesFolders': FeatureMatching.get_folder_path(),
                'describerTypes': 'akaze',
                'useLocalBA': 0,
                'lockScenePreviouslyReconstructed': 0,
                'interFileExtension': '.abc',
                'output': self.get_file_path('sfm')
            }
        )

    def _check_force_quit(self, line):
        detect = re.match(r'.*Resection of view.*failed', line)
        return detect is not None


class PrepareDenseScene(Flow):
    def __init__(self):
        super(PrepareDenseScene, self).__init__()

    def _make_command(self):
        if process.setting.is_cali():
            return
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_prepareDenseScene'
            ),
            args={
                'input': StructureFromMotion.get_file_path('sfm'),
                'output': self.get_folder_path(),
            }
        )


class ClipLandmarks(PythonFlow):
    _file = {
        'sfm': 'struct.sfm'
    }

    def __init__(self):
        super(ClipLandmarks, self).__init__()

    def run_python(self):
        if process.setting.is_cali():
            return

        import numpy as np

        with open(ConvertSFM.get_file_path('sfm')) as f:
            data = json.load(f)

        # Take cali's data
        load_sfm_path = StructureFromMotion.get_file_path_with_folder(
            'sfm', process.setting.cali_path
        )
        with open(load_sfm_path) as f:
            cali_data = json.load(f)
        data['structure'] = cali_data['structure']

        for structure in data['structure']:
            x, y, z = [float(x) for x in structure['X']]
            dist = np.sqrt(x * x + z * z)
            if dist > process.setting.clip.diameter / 2:
                ratio = process.setting.clip.diameter / 2 / dist
                structure['X'][0] = x * ratio
                structure['X'][2] = z * ratio
            if y > process.setting.clip.height:
                structure['X'][1] = process.setting.clip.height
            elif y < process.setting.clip.ground:
                structure['X'][1] = process.setting.clip.ground

        with open(self.get_file_path('sfm'), 'w') as f:
            json.dump(data, f, indent=4)
