from common.fourd_frame import FourdFrameManager


load_path = r'Q:\jobs\5f43add5253791a3da376079\export\003689.4df'
fourd_frame = FourdFrameManager.load(load_path)

export_path = 'c:/users/moonshine/desktop/'


# with open(export_path + 'test.obj', 'w') as f:
#     f.write(fourd_frame.get_obj_data())
#
with open(export_path + 'test.jpg', 'wb') as f:
    f.write(fourd_frame.get_texture_data(raw=True))

with open(export_path + 'test.4dh', 'wb') as f:
    f.write(fourd_frame.get_houdini_data())