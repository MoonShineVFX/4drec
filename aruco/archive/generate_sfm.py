import yaml
from pyquaternion import Quaternion
import json
from generate_aruco_landmarks import LandmarkGenerator


class SFMDataGenerator:
    _template: dict = {
        'base': {
            'version': ['1', '0', '0'],
            'intrinsics': [],
            'views': [],
            'poses': []
        },
        'intrinsic': {
            'intrinsicId': 'xxxxxxxx00',
            'serialNumber': f'sxxxxxxxx',
            'principalPoint': [1224, 1024],
            'locked': '0',
            'pxFocalLength': 2954.9974003446682,
            'height': 2048,
            'width': 2448,
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

    def __init__(
            self,
            camera_data_path: str,
            camera_ids_path: str,
            camera_positions_path: str,
            view_path: str,
            camera_images_path: str
    ):
        self._camera_data: dict = {
            'matrix': {},
            'distortion': {},
            'resolution': []
        }
        self._camera_ids: [str] = []
        self._camera_positions: [dict] = []
        self._view_path: str = view_path
        self._camera_images_path: str = camera_images_path

        # Initialize
        with open(camera_data_path) as f:
            lines = [l.split('!!')[0] for l in f.readlines()]
            data_string = '\n'.join(lines[1:])
            data: dict = yaml.full_load(data_string)
            self._camera_data['matrix'] = data['camera_matrix']['data']
            self._camera_data['distortion'] = \
                data['distortion_coefficients']['data']
            self._camera_data['resolution'] = [
                data['image_width'],
                data['image_height']
            ]

        with open(camera_ids_path) as f:
            data: dict = yaml.full_load(f)
            self._camera_ids = data['cameras']
            self._camera_ids.sort()

        with open(camera_positions_path) as f:
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

    def generate(self, frame: int):
        data: dict = self._template['base'].copy()
        for camera_id, camera_pose in zip(
                self._camera_ids, self._camera_positions
        ):
            intrinsic = self.make_intrinsic(camera_id)
            view = self.make_view(camera_id, frame)
            pose = self.make_position(camera_id, camera_pose)
            data['intrinsics'].append(intrinsic)
            data['views'].append(view)
            data['poses'].append(pose)
        return data

    def make_intrinsic(self, camera_id: str) -> dict:
        m: [float] = self._camera_data['matrix']
        d: [float] = self._camera_data['distortion']
        res: [float] = self._camera_data['resolution']
        intrinsic: dict = self._template['intrinsic'].copy()
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

    def make_view(self, camera_id: str, frame: int) -> dict:
        res: [float] = self._camera_data['resolution']
        view = self._template['view'].copy()
        view.update({
            'viewId': camera_id,
            'intrinsicId': f'{camera_id}00',
            'poseId': camera_id,
            'height': res[1],
            'width': res[0],
            'path': f'{self._camera_images_path}/{camera_id}_{frame:06d}.jpg',
        })
        return view

    def make_position(self, camera_id: str, camera_pose: dict) -> dict:
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


cali_path: str = 'c:/users/moonshine/desktop/cali/'
sfm_generator = SFMDataGenerator(
    camera_data_path=f'{cali_path}out-cam.yml',
    camera_ids_path='cameras.yaml',
    camera_positions_path=f'{cali_path}out.log',
    camera_images_path='c:/users/moonshine/desktop/cali/',
    view_path=cali_path
)
data = sfm_generator.generate(0)

# landmarks_generator = LandmarkGenerator(
#     aruco_path='c:/users/moonshine/desktop/marker_mapper_1.0.12w64/',
#     camera_ids_path='cameras.yaml',
#     images_path=cali_path,
#     marker_path=f'{cali_path}out.yml'
# )
# data['structure'] = landmarks_generator.generate()

with open('c:/users/moonshine/desktop/cali.sfm', 'w') as f:
    json.dump(data, f, indent=4)
