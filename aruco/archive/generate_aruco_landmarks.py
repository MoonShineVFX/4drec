import subprocess
import re
import yaml
import json
import tempfile
import os


class LandmarkGenerator:
    def __init__(
            self, aruco_path: str, camera_ids_path: str, images_path: str,
            marker_path
    ):
        self._aruco_path: str = aruco_path
        self._camera_ids: [str] = []
        self._images_path: str = images_path
        self._landmarks: dict = {}

        # Initialize
        with open(camera_ids_path) as f:
            self._camera_ids = yaml.full_load(f)['cameras']
        with open(marker_path) as f:
            lines = '\n'.join(f.readlines()[2:])
            data = yaml.full_load(lines)
            for feature in data['aruco_bc_markers']:
                for key in feature.keys():
                    if key.startswith('id'):
                        marker_id = int(key.split(':')[1])
                        break
                for i, pose in enumerate(feature['corners']):
                    for r in range(1):
                        landmark_id = self.get_landmark_id(marker_id, i, r)
                        self._landmarks[landmark_id] = {
                            'X': pose,
                            'observations': []
                        }

    def get_landmark_id(self, marker_id, point_number, repeat_times):
        return f'{marker_id:04d}{point_number:03d}{repeat_times:03d}'

    def get_observations(self):
        fp = tempfile.NamedTemporaryFile(delete=False)
        fp.close()
        command_list = [
            f'{self._aruco_path}aruco_batch_processing.exe',
            self._images_path,
            fp.name,
            '-minSizeImage', '0.01',
            '-MSize', '0.06256',
            '-d', 'ARUCO_MIP_36h12'
        ]

        cmd = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0
        )

        for line in iter(cmd.stdout.readline, b''):
            line = line.decode('utf-8').rstrip()
            print(line)

        cmd.wait()

        with open(fp.name) as f:
            lines = f.readlines()

        os.remove(f.name)

        obs = {}
        current_camera_id = None
        for line in lines:
            result = re.findall(
                r'\:\/.*(\d{8})_\d+.jpg|'
                r'(\d+)\s\[(.*?), (.*?)\]\s\[(.*?), '
                r'(.*?)\]\s\[(.*?), (.*?)\]\s\[(.*?), (.*?)\]',
                line
            )[0]
            camera_id = result[0]
            if camera_id != '':
                obs[camera_id] = []
                current_camera_id = camera_id
            else:
                obs[current_camera_id].append(
                    result[1:]
                )
        return obs

    def apply_observations(self):
        obs = self.get_observations()
        feature_num = 0
        for camera_id in self._camera_ids:
            for ob in obs[camera_id]:
                marker_id = int(ob[0])
                for i in range(4):
                    for r in range(1):
                        start_idx = i * 2 + 1
                        x = ob[start_idx:start_idx + 2]
                        landmark_id = self.get_landmark_id(marker_id, i, r)
                        if landmark_id not in self._landmarks:
                            print(f'landmark_id [{landmark_id}] not found')
                            continue

                        self._landmarks[landmark_id]['observations'].append({
                            'observationId': camera_id,
                            'featureId': str(feature_num),
                            'x': x
                        })
                        feature_num += 1

    def generate(self):
        self.apply_observations()
        data = [
            {
                'landmarkId': key,
                'descType': 'sift',
                'color': [255, 255, 255],
                **value
            }
            for key, value in self._landmarks.items()
        ]

        return data


# generator = LandmarkGenerator(
#     aruco_path='c:/users/moonshine/desktop/marker_mapper_1.0.12w64/',
#     camera_ids_path='cameras.yaml',
#     images_path='c:/users/moonshine/desktop/cali/',
#     marker_path='c:/users/moonshine/desktop/cali/out.yml'
# )
# print(generator.generate())