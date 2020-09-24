import os
import lz4framed
import struct
from utility.setting import setting
from common.jpeg_coder import jpeg_coder
from common.fourd_frame import FourdFrameManager
import json
import numpy as np
import cv2


class CompressedCache:
    def __init__(self, arr):
        self._shape = arr.shape
        self._type = arr.dtype
        self._data = lz4framed.compress(arr.tobytes())

    def load(self):
        data = lz4framed.decompress(self._data)
        arr = np.frombuffer(data, self._type)
        arr.shape = self._shape
        return arr

    def get_size(self):
        return len(self._data)


class ResolvePackage:
    def __init__(self, job_id, frame):
        self._geo_cache = None
        self._tex_cache = None
        self._job_id = job_id
        self._frame = frame
        self._resolution = setting.max_display_resolution

    def get_name(self):
        if self._frame is None:
            return f'{self._job_id}_rig'
        return f'{self._job_id}_{self._frame:08d}'

    def get_meta(self):
        return self._job_id, self._frame

    def _cache_buffer(self, geo_data, texture_data):
        self._geo_cache = (
            CompressedCache(geo_data[0]),
            CompressedCache(geo_data[1])
        )
        self._tex_cache = CompressedCache(texture_data)

    def get_cache_size(self):
        return self._geo_cache[0].get_size() +\
               self._geo_cache[1].get_size() +\
               self._tex_cache.get_size()

    def load(self):
        # if size is not None, means already loaded.
        if self._geo_cache is not None:
            return True

        # open file
        load_path = (
            f'{setting.submit_job_path}{self._job_id}/export/'
        )

        file_path = f'{load_path}{self._frame:06d}'
        old_format_path = file_path + '.4dr'
        new_format_path = file_path + '.4df'

        # old format
        if os.path.isfile(old_format_path):
            with open(old_format_path, 'rb') as f:
                data = f.read()

            geo_size, tex_size = struct.unpack(
                'II', data[:8]
            )
            seek = 8

            # load geo
            buffer = lz4framed.decompress(data[seek:seek + geo_size])
            arr = np.frombuffer(buffer, dtype=np.float32)
            seek += geo_size
            arr = arr.reshape(-1, 5)

            geo_data = [arr[:, :3], arr[:, 3:]]

            # load texture
            tex_data = jpeg_coder.decode(data[seek:seek + tex_size])

            self._cache_buffer(geo_data, tex_data)
            return True
        # new format
        elif os.path.isfile(new_format_path):
            fourd_frame = FourdFrameManager.load(new_format_path)
            geo_data = fourd_frame.get_geo_data()
            tex_data = fourd_frame.get_texture_data()
            self._resolution = fourd_frame.get_texture_resolution()

            # resize for better playback performance
            if self._resolution > setting.max_display_resolution:
                tex_data = cv2.resize(
                    tex_data,
                    dsize=(
                        setting.max_display_resolution,
                        setting.max_display_resolution
                    ),
                    interpolation=cv2.INTER_CUBIC
                )
                self._resolution = setting.max_display_resolution

            self._cache_buffer(geo_data, tex_data)
            return True
        return None

    def to_payload(self):
        geo_data = (self._geo_cache[0].load(), self._geo_cache[1].load())
        return len(geo_data[0]), geo_data, self._tex_cache.load(), self._resolution


def build_camera_pos_list():
    with open('source/ui/camera.json') as f:
        clist = json.load(f)
    return np.array(clist, np.float32)


class RigPackage(ResolvePackage):
    _camera_pos_list = build_camera_pos_list()

    def __init__(self, job_id, cali_id):
        super().__init__(job_id, None)
        self._cali_id = cali_id

    def load(self):
        if self._geo_cache is not None:
            return True

        file = (
            f'{setting.submit_cali_path}{self._cali_id}/'
            'StructureFromMotion/struct.sfm'
        )

        if not os.path.isfile(file):
            return None

        total_camera_pos_list = []

        with open(file) as f:
            sfm_data = json.load(f)

        for pose in sfm_data['poses']:
            transform = pose['pose']['transform']
            m = np.array([float(r) for r in transform['rotation']], np.float32)
            m = m.reshape(3, 3)
            m = m.T

            p = np.array([float(c) for c in transform['center']], np.float32)

            this_list = self._camera_pos_list.copy()
            this_list = this_list.dot(m)
            this_list += p

            total_camera_pos_list.append(this_list)

        pos_list = np.concatenate(total_camera_pos_list, axis=0)
        geo_data = pos_list

        self._cache_buffer(geo_data, None)
        return True

    def _cache_buffer(self, geo_data, texture_data):
        self._geo_cache = CompressedCache(geo_data)

    def get_cache_size(self):
        return self._geo_cache.get_size()

    def to_payload(self):
        geo_data = (self._geo_cache.load(), [])
        return len(geo_data[0]), geo_data, None, None
