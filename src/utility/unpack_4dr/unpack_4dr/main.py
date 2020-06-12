import struct
import lz4framed
from turbojpeg import TurboJPEG, TJPF_RGB
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


def unpack_4fr(file_path):
    jpeg_encoder = TurboJPEG('turbojpeg.dll')

    with open(file_path, 'rb') as f:
        data = f.read()

    header = data[:8]
    geo_size, texture_size = struct.unpack('II', header)

    geo_buffer = data[8:8 + geo_size]
    texture_buffer = data[8 + geo_size:]

    # obj
    geo_buffer = lz4framed.decompress(geo_buffer)
    point_list = np.frombuffer(geo_buffer, dtype=np.float32)
    point_list = point_list.reshape(-1, 5)

    pos_list = point_list[:, 0:3]
    uv_list = point_list[:, 3:5]

    uv_list = np.array(uv_list, np.float32)
    uv_list -= [0, 1.0]
    uv_list *= [1, -1]

    pos_strings = [f'v {x} {y} {z}' for x, y, z in pos_list]
    uv_strings = [f'vt {u} {v}' for u, v in uv_list]
    face_strings = [f'f {f}/{f} {f + 1}/{f + 1} {f + 2}/{f + 2}' for f in range(1, point_list.shape[0], 3)]

    obj_data = ['g'] + pos_strings + uv_strings + ['g'] + face_strings
    obj_data = '\n'.join(obj_data)

    with open(file_path.replace('4dr', 'obj'), 'w') as f:
        f.write(obj_data)

    # jpg
    with open(file_path.replace('4dr', 'jpg'), 'wb') as f:
        im = jpeg_encoder.decode(texture_buffer, TJPF_RGB)
        f.write(jpeg_encoder.encode(im))

    return file_path


if __name__ == '__main__':
    path = Path('c:/users/moonshine/desktop/4im')
    files = path.glob('*.4dr')
    files = [str(f) for f in files]
    with ProcessPoolExecutor() as executor:
        results = executor.map(unpack_4fr, files)
        for r in results:
            print(r)

