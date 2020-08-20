import json


with open('c:/users/moonshine/desktop/result.sfm') as f:
    data = json.load(f)

for view in data['views']:
    view['path'] = view['path'].replace('cali', 'shot')

with open('c:/users/moonshine/desktop/shot.sfm', 'w') as f:
    json.dump(data, f)
