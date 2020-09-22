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
                'depthMapsFolder': DepthMapEstimation.get_folder_path(),
                'output': self.get_folder_path(),
            },
            override=self.get_parameters()
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
            },
            override=self.get_parameters()
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
        radius_mask = radius_list < process.setting.clip_range.diameter / 2

        height_list = point_list[:, 1]
        height_mask = (
            (height_list > process.setting.clip_range.ground) &
            (height_list < process.setting.clip_range.height)
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
                        process.setting.mesh_reduce_ratio
                    )
                ),
                'output': self.get_file_path('obj'),
            },
            override=self.get_parameters()
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
                'output': self.get_folder_path(),
            },
            override=self.get_parameters()
        )


class Package(PythonFlow):
    def __init__(self):
        super(Package, self).__init__(no_folder=True)

    def run_python(self):
        from common.fourd_frame import FourdFrameManager
        import json

        # stats
        with open(StructureFromMotion.get_file_path('stats')) as f:
            stats_data = json.load(f)['sfm']

        # sfm
        with open(ClipLandmarks.get_file_path('sfm')) as f:
            sfm_parameters = json.load(f)
        for del_key in ('version', 'structure'):
            del sfm_parameters[del_key]

        FourdFrameManager.save(
            save_path=process.setting.export_path +
            f'{process.setting.frame:06d}.4df',
            obj_path=Texturing.get_file_path('obj'),
            jpg_path=Texturing.get_file_path('texture'),
            frame=process.setting.frame,
            submit_parameters=process.setting.to_argument(),
            sfm_parameters=sfm_parameters,
            validViews=int(stats_data['validViews']),
            poses=int(stats_data['poses']),
            points=int(stats_data['points']),
            residual=float(stats_data['residual']),
            job_id=process.setting.get_job_id().encode()
        )

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