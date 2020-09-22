import lz4framed
from PIL import Image
import numpy as np
import struct
import json

from common.jpeg_coder import jpeg_coder, TJPF_RGB


class FourdFrameManager:
    # header will be first 1k
    # v1: no pad for header which is 80
    header = {
        'format': b'4dk2',
        'job_id': b'',
        'frame': 0,
        # stats.json
        'validViews': 0,
        'poses': 0,
        'points': 0,
        'residual': 0.0,
        # content
        'geo_faces': 0,
        'texture_quality': 85,
        'texture_width': 0,
        'texture_height': 0,
        # buffer size
        'geo_buffer_size': 0,
        'texture_buffer_size': 0,
        'submit_parameters_buffer_size': 0,
        'sfm_parameters_buffer_size': 0
    }
    header_format = '4s24sIIIIfIIIIIIII'
    header_size = 1024

    @classmethod
    def get_header_template(cls):
        return cls.header.copy()

    @classmethod
    def save(
            cls,
            save_path, obj_path, jpg_path,
            frame,
            submit_parameters=None,
            sfm_parameters=None,
            **kwargs
    ):
        header = cls.get_header_template()
        header.update({
            'frame': frame,
            **kwargs
        })

        # buffer
        geo_buffer = b''
        texture_buffer = b''
        submit_parameters_buffer = b''
        sfm_parameters_buffer = b''

        # geo
        print('Convert geo')
        pos_list = []
        uv_list = []
        point_list = []

        with open(obj_path, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    _, x, y, z = line.split()
                    pos_list.append((x, y, z))
                elif line.startswith('vt '):
                    _, u, v = line.split()
                    uv_list.append((u, v))
                elif line.startswith('f '):
                    points = line.split()[1:]
                    for point in points:
                        p, uv = point.split('/')
                        point_list.append((p, uv))

        pos_list = np.array(pos_list, np.float32)
        uv_list = np.array(uv_list, np.float32)
        point_list = np.array(point_list, np.int32)

        faces_count = int(len(point_list) / 3)

        uv_list *= [1, -1]
        uv_list += [0, 1.0]
        point_list -= 1
        point_list = point_list.T

        pos_list = pos_list[point_list[0]]
        uv_list = uv_list[point_list[1]]

        out_list = np.hstack((pos_list, uv_list))
        geo_buffer = lz4framed.compress(out_list.tobytes())
        header['geo_buffer_size'] = len(geo_buffer)
        header['geo_faces'] = faces_count

        # texture
        print('Convert texture')
        image = Image.open(jpg_path)
        texture_buffer = jpeg_coder.encode(
            np.array(image), quality=header['texture_quality']
        )
        header['texture_buffer_size'] = len(texture_buffer)
        header['texture_width'] = image.size[0]
        header['texture_height'] = image.size[1]
        image.close()

        # submit_parameters
        if submit_parameters is not None:
            submit_parameters_buffer = lz4framed.compress(
                submit_parameters.encode()
            )
            header['submit_parameters_buffer_size'] = len(submit_parameters_buffer)

        # sfm_parameters
        if sfm_parameters is not None:
            sfm_parameters_string = json.dumps(sfm_parameters)
            sfm_parameters_buffer = lz4framed.compress(
                sfm_parameters_string.encode()
            )
            header['sfm_parameters_buffer_size'] = len(sfm_parameters_buffer)

        # pack
        print('save 4dp')
        header_buffer = struct.pack(cls.header_format, *header.values())
        header_buffer = header_buffer.ljust(cls.header_size, b'\0')

        with open(save_path, 'wb') as f:
            for buffer in (
                    header_buffer, geo_buffer, texture_buffer,
                    submit_parameters_buffer,
                    sfm_parameters_buffer
            ):
                f.write(buffer)

    @classmethod
    def load(cls, file_path):
        return FourdFrame(file_path)


class FourdFrame:
    def __init__(self, file_path):
        self._file = open(file_path, 'rb')
        self.header = self._load_header()
        self._geo_data = None
        self._texture_data = None
        self._submit_data = None
        self._sfm_data = None

    def _load_header(self):
        header_size = struct.calcsize(FourdFrameManager.header_format)
        header_data = struct.unpack(
            FourdFrameManager.header_format, self._file.read(header_size)
        )

        header = FourdFrameManager.get_header_template()
        for key, data in zip(header.keys(), header_data):
            header[key] = data

        return header

    def get_texture_resolution(self):
        return self.header['texture_width']

    def get_file_data(self, seek_buffer_name):
        if self.header['format'] == b'4dk1':
            seek_pos = 80
        else:
            seek_pos = FourdFrameManager.header_size
        for buffer_name in ('geo', 'texture', 'submit', 'sfm'):
            if seek_buffer_name == buffer_name:
                self._file.seek(seek_pos)
                return self._file.read(
                    self.header[f'{buffer_name}_buffer_size']
                )
            seek_pos += self.header[f'{buffer_name}_buffer_size']

    def get_geo_data(self):
        if self._geo_data is None:
            geo_file = self.get_file_data('geo')
            buffer = lz4framed.decompress(geo_file)
            arr = np.frombuffer(buffer, dtype=np.float32)
            arr = arr.reshape(-1, 5)
            self._geo_data = [arr[:, :3], arr[:, 3:]]
        return self._geo_data

    def get_texture_data(self, raw=False):
        if raw:
            texture_file = self.get_file_data('texture')
            texture_data = jpeg_coder.decode(texture_file, TJPF_RGB)
            return jpeg_coder.encode(texture_data)
        if self._texture_data is None:
            texture_file = self.get_file_data('texture')
            self._texture_data = jpeg_coder.decode(texture_file)
        return self._texture_data

    def get_obj_data(self):
        pos_list, uv_list = self.get_geo_data()

        uv_list = uv_list.copy()
        uv_list -= [0, 1.0]
        uv_list *= [1, -1]

        pos_strings = [f'v {x} {y} {z}' for x, y, z in pos_list]
        uv_strings = [f'vt {u} {v}' for u, v in uv_list]
        face_strings = [f'f {f}/{f} {f + 1}/{f + 1} {f + 2}/{f + 2}' for f in range(1, pos_list.shape[0], 3)]

        obj_data = ['g'] + pos_strings + uv_strings + ['g'] + face_strings
        obj_data = '\n'.join(obj_data)

        return obj_data

    def get_submit_data(self):
        if self._submit_data is None:
            submit_file = self.get_file_data('submit')
            buffer = lz4framed.decompress(submit_file)
            self._submit_data = json.loads(buffer.decode())
        return self._submit_data

    def get_sfm_data(self):
        if self._sfm_data is None:
            sfm_file = self.get_file_data('sfm')
            buffer = lz4framed.decompress(sfm_file)
            self._sfm_data = json.loads(buffer.decode())
        return self._sfm_data

    def close(self):
        self._file.close()
        for prop in ('geo', 'texture', 'submit', 'sfm'):
            setattr(self, f'_{prop}_data', None)
