from common.fourd_frame import FourdFrameManager


load_path = r'Q:\jobs\5f43add5253791a3da376079\export\003689.4df'
fourd_frame = FourdFrameManager.load(load_path)

fourd_frame.get_geo_data()