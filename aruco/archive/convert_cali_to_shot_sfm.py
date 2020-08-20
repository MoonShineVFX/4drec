import json
from generate_aruco_landmarks import LandmarkGenerator


with open('c:/users/moonshine/desktop/aout.sfm') as f:
    data = json.load(f)

# for view in data['views']:
#     view['path'] = view['path'].replace('cali', 'shot')

cali_path: str = 'c:/users/moonshine/desktop/cali/'
landmarks_generator = LandmarkGenerator(
    aruco_path='c:/users/moonshine/desktop/marker_mapper_1.0.12w64/',
    camera_ids_path='cameras.yaml',
    images_path=cali_path,
    marker_path=f'{cali_path}out.yml'
)
data['structure'] = landmarks_generator.generate()

# del data['featuresFolders']
# del data['matchesFolders']
# del data['structure']

with open('c:/users/moonshine/desktop/bout.sfm', 'w') as f:
    json.dump(data, f)
