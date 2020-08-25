# -*- coding: future_fstrings -*-
from reference import process

from .feature import (
    FeatureExtraction, ClipLandmarks, FeatureMatching,
    PrepareDenseScene, StructureFromMotion, ConvertSFM
)
from .flow import Flow, FlowCommand, PythonFlow
from .depth import DepthMapEstimation


class DepthMapFiltering(Flow):
    def __init__(self):
        super(DepthMapFiltering, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_depthMapFiltering'
            ),
            args={
                'input': ClipLandmarks.get_file_path('sfm'),
                'minNumOfConsistentCams': 2,
                'minNumOfConsistentCamsWithLowSimilarity': 3,
                'depthMapsFolder': DepthMapEstimation.get_folder_path(),
                'output': self.get_folder_path(),
                # add
                'nNearestCams': 8,
                # 'pixSizeBall': 1,
                # 'pixSizeBallWithLowSimilarity': 1
            }
        )


class Meshing(Flow):
    _file = {
        'obj': 'mesh.obj',
        'dense': 'dense.abc'
    }

    def __init__(self):
        super(Meshing, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_meshing'
            ),
            args={
                'input': ClipLandmarks.get_file_path('sfm'),
                'depthMapsFolder': DepthMapEstimation.get_folder_path(),
                'depthMapsFilterFolder': DepthMapFiltering.get_folder_path(),
                'output': self.get_file_path('dense'),
                'outputMesh': self.get_file_path('obj'),
                # add
                # 'maxPoints': 120000,
                # 'minStep': 2,
                # 'simGaussianSizeInit': 5,
                # 'simGaussianSize': 5,
                # 'maxPoints': 50000000,
                # 'estimateSpaceMinObservations': 2,
                # 'pixSizeMarginInitCoef': 1,
                # 'refineFuse': 1
            }
        )

    @classmethod
    def _clean_cache(cls):
        import glob
        import os
        files = glob.glob(cls.get_folder_path() + '*.exr')
        for f in files:
            os.remove(f)


class MeshFiltering(Flow):
    _file = {
        'obj': 'filterMesh.obj'
    }

    def __init__(self):
        super(MeshFiltering, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_meshFiltering'
            ),
            args={
                'input': Meshing.get_file_path('obj'),
                'iterations': 10,
                'lambda': 1,
                'removeLargeTrianglesFactor': 30,
                'output': self.get_file_path('obj'),
            }
        )


class MeshClipping(PythonFlow):
    _file = {
        'obj': 'mesh.obj'
    }

    def __init__(self):
        super(MeshClipping, self).__init__()

    def run_python(self):
        import numpy as np

        with open(MeshFiltering.get_file_path('obj')) as f:
            lines = f.readlines()

        point_list = []
        face_list = []
        for line in lines:
            if line.startswith('v'):
                _, x, y, z = line.split()
                point_list.append((x, y, z))
            elif line.startswith('f'):
                _, p1, p2, p3 = line.split()
                face_list.append((p1, p2, p3))

        # declare
        point_list = np.array(point_list, np.float32)
        face_list = np.array(face_list, np.uint32) - 1

        # point mask
        radius_list = np.linalg.norm(point_list[:, [0, 2]], axis=1)
        radius_mask = radius_list < process.setting.clip.diameter / 2

        height_list = point_list[:, 1]
        height_mask = (
            (height_list > process.setting.clip.ground) &
            (height_list < process.setting.clip.height)
        )

        point_mask = radius_mask & height_mask

        # face mask
        face_mask = point_mask[face_list]
        face_mask = np.all(face_mask, axis=1)
        face_list = face_list[face_mask]

        # point_idx
        point_idx = np.arange(point_list.shape[0])
        new_point_idx = point_idx[point_mask]
        point_idx[new_point_idx] = np.arange(new_point_idx.size)

        # new_face_list
        face_list = point_idx[face_list]
        face_list += 1
        point_list = point_list[point_mask]

        data = f'# {point_list.shape[0]}\ng Mesh\n'
        data += '\n'.join([f'v {p[0]} {p[1]} {p[2]}' for p in point_list])
        data += '\n'
        data += '\n'.join([f'f {f[0]} {f[1]} {f[2]}' for f in face_list])

        with open(self.get_file_path('obj'), 'w') as f:
            f.write(data)


class MeshDecimate(Flow):
    _file = {
        'obj': 'mesh.obj',
    }

    def __init__(self):
        super(MeshDecimate, self).__init__()

    def _make_command(self):
        with open(MeshClipping.get_file_path('obj')) as f:
            data = f.readline()
            _, vertex_count = data.split()
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_meshDecimate'
            ),
            args={
                'input': MeshClipping.get_file_path('obj'),
                'maxVertices': int(
                    int(vertex_count) *
                    float(
                        process.setting.get_parameters()['mesh_reduce_ratio']
                    )
                ),
                'simplificationFactor': 1,
                'output': self.get_file_path('obj')
            }
        )


class Texturing(Flow):
    _file = {
        'obj': 'texturedMesh.obj',
        'texture': 'texture_1001.png'
    }

    def __init__(self):
        super(Texturing, self).__init__()

    def _make_command(self):
        return FlowCommand(
            execute=(
                process.setting.alicevision_path +
                'aliceVision_texturing'
            ),
            args={
                'input': Meshing.get_file_path('dense'),
                'inputMesh': MeshDecimate.get_file_path('obj'),
                'imagesFolder': PrepareDenseScene.get_folder_path(),
                'textureSide': 4096,
                'useUDIM': 1,
                'downscale': 1,
                'unwrapMethod': 'Basic',
                'output': self.get_folder_path(),
                #add
                # 'useScore': 0,
                # 'bestScoreThreshold': 0,
                # 'angleHardThreshold': 0,
                # 'forceVisibleByAllVertices': 1,
            }
        )


class Package(PythonFlow):
    def __init__(self):
        super(Package, self).__init__(no_folder=True)

    def run_python(self):
        import lz4framed
        from PIL import Image
        import numpy as np
        import struct
        from turbojpeg import TurboJPEG
        jpeg_encoder = TurboJPEG('common/turbojpeg.dll')

        print(f'Start package')
        file_prefix = (
            process.setting.export_path +
            f'{process.setting.frame:06d}'
        )

        # texture
        print('Convert texture')
        image = Image.open(Texturing.get_file_path('texture'))
        jpeg_buffer = jpeg_encoder.encode(
            np.array(image), quality=85
        )
        image.close()

        # model
        print('Convert geo')
        pos_list = []
        uv_list = []
        point_list = []

        with open(Texturing.get_file_path('obj'), 'r') as f:
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

        uv_list *= [1, -1]
        uv_list += [0, 1.0]
        point_list -= 1
        point_list = point_list.T

        pos_list = pos_list[point_list[0]]
        uv_list = uv_list[point_list[1]]

        out_list = np.hstack((pos_list, uv_list))
        geo_buffer = lz4framed.compress(out_list.tobytes())

        # package
        print('Save 4dr')
        header = struct.pack('II', len(geo_buffer), len(jpeg_buffer))

        with open(file_prefix + '.4dr', 'wb') as f:
            f.write(header)
            f.write(geo_buffer)
            f.write(jpeg_buffer)


class OptimizeStorage(PythonFlow):
    def __init__(self):
        super(OptimizeStorage, self).__init__(no_folder=True)

    def run_python(self):
        PrepareDenseScene._clean_folder()
        Meshing._clean_folder()
        FeatureExtraction._clean_folder()
        DepthMapEstimation._clean_folder()
        DepthMapFiltering._clean_folder()
        StructureFromMotion._clean_folder()
        MeshFiltering._clean_folder()
        MeshClipping._clean_folder()
        Texturing._clean_folder()
        MeshDecimate._clean_folder()
        FeatureMatching._clean_folder()
        ClipLandmarks._clean_folder()
        ConvertSFM._clean_folder()
        return