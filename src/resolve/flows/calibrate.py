# -*- coding: future_fstrings -*-
import json
import time
import os

from reference import process

from .flow import PythonFlow, Flow, FlowCommand


class ConstructFromAruco(Flow):
    _file = {
        'pos': 'out.log',
        'cam': 'out-cam.yml',
        'ids': 'camera_ids.json'
    }

    def __init__(self):
        super(ConstructFromAruco, self).__init__()
        self._camera_ids = []

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.aruco_path +
                'mapper_from_images'
            ),
            args=[
                process.setting.shot_path,
                process.setting.aruco_path + 'cam.yml',
                self.get_parameter('aruco_size'),
                self.get_parameter('aruco_dict'),
                self.get_folder_path() + 'out'
            ]
        )

    def _check_force_quit(self, line):
        if line.startswith('Reading...'):
            if not line.endswith('jpg'):
                return False
            camera_id = line.split('/')[-1].split('_')[0]
            self._camera_ids.append(camera_id)
        elif line.startswith('BundleAdjustmentOptimization'):
            with open(self.get_file_path('ids'), 'w') as f:
                json.dump(self._camera_ids, f)

            while True:
                time.sleep(3)
                if (
                    os.path.isfile(self.get_file_path('pos')) and
                    os.path.isfile(self.get_file_path('cam'))
                ):
                    break
            return True
        return False


class GenerateSFM(PythonFlow):
    _file = {
        'sfm': 'out.sfm'
    }

    def __init__(self):
        super(GenerateSFM, self).__init__()

    def run_python(self):
        import yaml
        from pyquaternion import Quaternion


        class SFMDataGenerator:
            _template = {
                'base': {
                    'version': ['1', '0', '0'],
                    'intrinsics': [],
                    'views': [],
                    'poses': []
                },
                'intrinsic': {
                    'intrinsicId': 'xxxxxxxx00',
                    'serialNumber': f'sxxxxxxxx',
                    'principalPoint': [2048, 1500],
                    'locked': '0',
                    'pxFocalLength': 4944.309375740098,
                    'height': 3000,
                    'width': 4096,
                    'initializationMode': 'unknown',
                    'pxInitialFocalLength': '-1',
                    'type': 'radial3',
                    'distortionParams': [0, 0, 0]
                },
                'view': {
                    'viewId': 'xxxxxxxx',
                    'intrinsicId': 'xxxxxxxx00',
                    'poseId': 'xxxxxxxx',
                    'height': 0,
                    'width': 0,
                    'path': 'x:/xxxxxxxx_xxxxxx.jpg',
                    'metadata': {
                        'YResolution': '1',
                        'ResolutionUnit': 'none',
                        'oiio:ColorSpace': 'sRGB',
                        'XResolution': '1',
                        'jpeg:subsampling': '4:2:0'
                    }
                },
                'pose': {
                    'pose': {
                        'locked': '0',
                        'transform': {
                            'rotation': [
                                0, 0, 0,
                                0, 0, 0,
                                0, 0, 0
                            ],
                            'center': [
                                0, 0, 0
                            ]
                        }
                    },
                    'poseId': 'xxxxxxxx'
                }
            }

            def __init__(self):
                self._camera_data = {
                    'matrix': {},
                    'distortion': {},
                    'resolution': []
                }
                self._camera_ids = []
                self._camera_positions = []

                # Initialize
                with open(ConstructFromAruco.get_file_path('cam')) as f:
                    lines = [l.split('!!')[0] for l in f.readlines()]
                    data_string = '\n'.join(lines[1:])
                    data = yaml.full_load(data_string)
                    self._camera_data['matrix'] = data['camera_matrix']['data']
                    self._camera_data['distortion'] = \
                        data['distortion_coefficients']['data']
                    self._camera_data['resolution'] = [
                        data['image_width'],
                        data['image_height']
                    ]

                with open(ConstructFromAruco.get_file_path('ids')) as f:
                    self._camera_ids = json.load(f)

                with open(ConstructFromAruco.get_file_path('pos')) as f:
                    lines = f.readlines()
                    for l in lines:
                        nums = l.split()[1:]
                        nums = [float(num) for num in nums]
                        self._camera_positions.append(
                            {
                                't': nums[:3],
                                'r': nums[3:7]
                            }
                        )

            def generate(self):
                data = self._template['base'].copy()
                for camera_id, camera_pose in zip(
                        self._camera_ids, self._camera_positions
                ):
                    intrinsic = self.make_intrinsic(camera_id)
                    view = self.make_view(camera_id)
                    pose = self.make_position(camera_id, camera_pose)
                    data['intrinsics'].append(intrinsic)
                    data['views'].append(view)
                    data['poses'].append(pose)
                return data

            def make_intrinsic(self, camera_id):
                m = self._camera_data['matrix']
                d = self._camera_data['distortion']
                res = self._camera_data['resolution']
                intrinsic = self._template['intrinsic'].copy()
                intrinsic.update({
                    'intrinsicId': f'{camera_id}00',
                    'serialNumber': f's{camera_id}',
                    'height': res[1],
                    'width': res[0],
                    'principalPoint': [m[2], m[5]],
                    'pxFocalLength': m[0],
                    'distortionParams': [d[0], d[1], d[4]]
                })
                return intrinsic

            def make_view(self, camera_id):
                res = self._camera_data['resolution']
                view = self._template['view'].copy()
                view.update({
                    'viewId': camera_id,
                    'intrinsicId': f'{camera_id}00',
                    'poseId': camera_id,
                    'height': res[1],
                    'width': res[0],
                    'path': f'{process.setting.shot_path}/{camera_id}_{0:06d}.jpg',
                })
                return view

            def make_position(self, camera_id, camera_pose):
                qx, qy, qz, qw = camera_pose['r']
                quat = Quaternion(qw, qx, qy, qz)
                matrix = quat.rotation_matrix
                matrix = matrix[:3, :3].reshape((1, -1))
                matrix = matrix.tolist()[0]

                pose = self._template['pose'].copy()
                pose.update({
                    'poseId': camera_id,
                    'pose': {
                        'locked': '0',
                        'transform': {
                            'center': camera_pose['t'],
                            'rotation': matrix
                        }
                    }
                })
                return pose

        sfm_generator = SFMDataGenerator()
        data = sfm_generator.generate()

        with open(self.get_file_path('sfm'), 'w') as f:
            json.dump(data, f, indent=4)


class TransformStructure(PythonFlow):
    _file = {
        'sfm': 'out.sfm',
    }

    def __init__(self):
        super(TransformStructure, self).__init__()

    def run_python(self):
        import numpy as np
        from common.camera_structure import camera_structure

        def distance(a, b):
            return np.linalg.norm(a - b)

        def normalize(a):
            return a / np.linalg.norm(a)

        def get_struct():
            with open(GenerateSFM.get_file_path('sfm'), 'r') as f:
                data = json.load(f)

            camera_position_list = []
            camera_indices = []
            camera_id_position_dict = {}

            for i, pose in enumerate(data['poses']):
                pos = [float(p) for p in pose['pose']['transform']['center']]
                camera_position_list.append(pos)

                _id = pose['poseId']
                camera_id_position_dict[_id] = np.array(pos, np.float32)
                camera_indices.append(_id)

            camera_position_list = np.array(camera_position_list, np.float32)

            return data, camera_position_list, camera_id_position_dict, camera_indices

        def get_vertical_vector(camera_id_position_dict):
            vertical_vectors = []

            for truss_letter in camera_structure.get_position_letters():
                for upper_idx, lower_idx in ((2, 0), (3, 1)):
                    upper_pos = camera_id_position_dict[
                        camera_structure.get_camera_id_by_position(
                            f'{truss_letter}{upper_idx}'
                        )
                    ]
                    lower_pos = camera_id_position_dict[
                        camera_structure.get_camera_id_by_position(
                            f'{truss_letter}{lower_idx}'
                        )
                    ]
                    if upper_pos is None or lower_pos is None:
                        continue
                    vertical_vectors.append(normalize(upper_pos - lower_pos))

                return normalize(np.average(vertical_vectors, axis=0))

        def get_rotation(p0, p2, y, scale):
            x_p = p2 - y * abs(
                process.setting.reference.cameras[1][1] -
                process.setting.reference.cameras[0][1]
            ) / scale
            x = normalize(x_p - p0)
            z = normalize(np.cross(x, y))
            return np.array([x, y, z], np.float32)

        data, camera_position_list, camera_id_position_dict, camera_indices = get_struct()

        # get positions
        truss_position_0 = process.setting.reference.cameras[0][0]
        cam0_p = camera_id_position_dict[
            camera_structure.get_camera_id_by_position(truss_position_0)
        ]
        truss_position_1 = process.setting.reference.cameras[1][0]
        cam2_p = camera_id_position_dict[
            camera_structure.get_camera_id_by_position(truss_position_1)
        ]

        # get calculate ref
        scale = process.setting.reference.diameter / distance(cam0_p, cam2_p)
        rot = get_rotation(
            cam0_p, cam2_p,
            get_vertical_vector(camera_id_position_dict),
            scale
        )
        real_p0 = np.array(
            (
                -process.setting.reference.diameter / 2.0,
                process.setting.reference.cameras[0][1],
                0
            ), np.float32
        )

        camera_position_list = camera_position_list.dot(np.linalg.inv(rot))
        camera_position_list *= scale

        offset = (
            real_p0 -
            camera_position_list[camera_indices.index(
                camera_structure.get_camera_id_by_position(truss_position_0)
            )]
        )

        camera_position_list += offset

        for pose in data['poses']:
            _id = pose['poseId']
            pose['pose']['transform']['center'] = [
                str(p) for p in camera_position_list[camera_indices.index(_id)]
            ]

        with open(self.get_file_path('sfm'), 'w') as f:
            json.dump(data, f)


class AlignStructure(Flow):
    _file = {
        'sfm': 'out.sfm',
    }

    def __init__(self):
        super(AlignStructure, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_utils_sfmAlignment'
            ),
            args={
                'input': GenerateSFM.get_file_path('sfm'),
                'output': self.get_file_path('sfm'),
                'reference': TransformStructure.get_file_path('sfm')
            }
        )
