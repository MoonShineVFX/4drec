from common.fourd_frame import FourdFrameManager
import lz4framed
from time import perf_counter
from common.jpeg_coder import jpeg_coder


load_path = r'Q:\jobs\5f43add5253791a3da376079\export\003689.4df'
fourd_frame = FourdFrameManager.load(load_path)


def print_size(*buffers):
    total_size = 0
    for buf in buffers:
        total_size += len(buf)
    print(total_size / 1024 / 1024)


geo_data_list = fourd_frame.get_geo_data()
geo_data_a = geo_data_list[0].tobytes()
geo_data_b = geo_data_list[1].tobytes()
texture_data = fourd_frame.get_texture_data().tobytes()

geo_a_lz4 = lz4framed.compress(geo_data_a)
geo_b_lz4 = lz4framed.compress(geo_data_b)
texture_lz4 = lz4framed.compress(texture_data)

print_size(geo_data_a, geo_data_b, texture_data)

times = 10
t = perf_counter()
for i in range(times):
    lz4framed.decompress(geo_b_lz4)
    lz4framed.decompress(geo_a_lz4)
    lz4framed.decompress(texture_lz4)
e = perf_counter() - t
print(e / times)
print_size(geo_a_lz4, geo_b_lz4, texture_lz4)

