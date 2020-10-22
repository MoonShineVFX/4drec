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
                'output': self.get_folder_path()
            },
            override=self.get_parameters()
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
                'output': self.get_folder_path(),
            },
            override=self.get_parameters()
        )


class StructureFromMotion(Flow):
    _file = {
        'sfm': 'struct.sfm',
        'stats': 'stats.json'
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
                'output': self.get_file_path('sfm'),
            },
            override=self.get_parameters()
        )

    def _check_force_quit(self, line):
        detect = re.match(r'.*Resection of view.*failed', line)
        return detect is not None


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

        with open(StructureFromMotion.get_file_path('sfm')) as f:
            data = json.load(f)

        # Take cali's data
        # load_sfm_path = StructureFromMotion.get_file_path_with_folder(
        #     'sfm', process.setting.cali_path
        # )
        # with open(load_sfm_path) as f:
        #     cali_data = json.load(f)
        # data['structure'] = cali_data['structure']

        for structure in data['structure']:
            x, y, z = [float(x) for x in structure['X']]
            dist = np.sqrt(x * x + z * z)
            if dist > process.setting.clip_range.diameter / 2:
                ratio = process.setting.clip_range.diameter / 2 / dist
                structure['X'][0] = x * ratio
                structure['X'][2] = z * ratio
            if y > process.setting.clip_range.height:
                structure['X'][1] = process.setting.clip_range.height
            elif y < process.setting.clip_range.ground:
                structure['X'][1] = process.setting.clip_range.ground

        with open(self.get_file_path('sfm'), 'w') as f:
            json.dump(data, f, indent=4)


class MaskImages(PythonFlow):
    def __init__(self):
        super(MaskImages, self).__init__()

    @staticmethod
    def mask_image(image_file, export_path):
        import cv2
        import numpy as np
        from pathlib import Path

        lower_green = np.array([53, 36, 60])
        upper_green = np.array([74, 95, 180])

        img = cv2.imread(image_file)

        # convert hsv
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # mask
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # smooth
        okernel = np.ones((7, 7), np.uint8)
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, okernel)
        ckernel = np.ones((6, 6), np.uint8)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, ckernel)

        # apply
        img[closed == 255] = 0

        # export
        filename = f'{Path(image_file).stem}.png'
        cv2.imwrite(
            f'{export_path}\\matte\\{filename}',
            closed,
            [cv2.IMWRITE_PNG_COMPRESSION, 5]
        )
        cv2.imwrite(
            f'{export_path}\\{filename}',
            img,
            [cv2.IMWRITE_PNG_COMPRESSION, 5]
        )

        return filename

    def run_python(self):
        if process.setting.is_cali():
            return

        from pathlib import Path
        from concurrent.futures import ProcessPoolExecutor, as_completed

        # start
        folder = Path(process.setting.shot_path)
        export_path = self.get_folder_path()
        (Path(export_path) / 'matte').mkdir(parents=True, exist_ok=True)

        with ProcessPoolExecutor() as executor:
            future_list = []

            for image_file in folder.glob(
                    f'*_{process.setting.frame:06d}.jpg'
            ):
                future = executor.submit(
                    MaskImages.mask_image, str(image_file), export_path
                )
                future_list.append(future)

            for future in as_completed(future_list):
                result = future.result()
                process.log_info(result)


class PrepareDenseSceneWithMask(Flow):
    def __init__(self):
        super(PrepareDenseSceneWithMask, self).__init__()

    def _make_command(self):
        if process.setting.is_cali():
            return
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_prepareDenseScene'
            ),
            args={
                'input': ClipLandmarks.get_file_path('sfm'),
                'output': self.get_folder_path(),
                'imagesFolders': MaskImages.get_folder_path()
            }
        )


class PrepareDenseSceneOnlyMask(Flow):
    def __init__(self):
        super(PrepareDenseSceneOnlyMask, self).__init__()

    def _make_command(self):
        if process.setting.is_cali():
            return
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_prepareDenseScene'
            ),
            args={
                'input': ClipLandmarks.get_file_path('sfm'),
                'output': self.get_folder_path(),
                'imagesFolders': MaskImages.get_folder_path() + 'matte/',
                'outputFileType': 'png'
            }
        )


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
                'input': ClipLandmarks.get_file_path('sfm'),
                'output': self.get_folder_path()
            }
        )


if '__main__' == __name__:
    pass
