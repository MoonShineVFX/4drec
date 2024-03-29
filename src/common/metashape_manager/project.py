import Metashape
import os
from pathlib import Path
import numpy as np

from common.fourd_frame import FourdFrameManager

from .keying import keying_images


class MetashapeProject:
    _psx_name = 'project'
    _cameras_name = 'cameras'
    _calibrate_chunk_name = 'calibrate'
    _masks_name = 'masks'
    _chunk_prefix_name = 'frame_'
    _export_name = 'export'

    _sensor_pixel_width = 0.00345
    _sensor_focal_length = 12
    _region_size_large = (12, 7, 12)
    _region_size_small = (5, 4, 5)

    _marker_reference = {
        'target 1': (0, 0.18, 0),
        'target 2': (0.133, 0.18, 0),
        'target 5': (0, 0.424, 0)
    }

    def __init__(self):
        self._start_frame = int(os.environ['start_frame'])
        self._end_frame = int(os.environ['end_frame'])
        self._current_frame = int(os.environ['current_frame'])

        self._cali_path = Path(os.environ['cali_path'])
        self._shot_path = Path(os.environ['shot_path'])
        self._job_path = Path(os.environ['job_path'])

        self._project_path = self._job_path / f'{self._psx_name}.psx'
        self._files_path = self._job_path / f'{self._psx_name}.files'
        self._cameras_path = self._job_path / f'{self._cameras_name}.out'
        self._masks_path = self._shot_path / self._masks_name
        self._export_path = self._job_path / f'{self._export_name}'

        self._doc = self._initial_doc()

    def _initial_doc(self):
        doc = Metashape.Document()
        if self._project_path.exists():
            doc.open(
                self._project_path.__str__(),
                ignore_lock=True,
                read_only=False
            )
        else:
            doc.save(self._project_path.__str__())
        return doc

    def _create_chunk(self, chunk_name) -> Metashape.Chunk:
        new_chunk = self._doc.addChunk()
        chunk_name = self._convert_chunk_name(chunk_name)
        new_chunk.label = chunk_name
        return new_chunk

    def _import_images_to_chunk(self, chunk, path, frame):
        photos = [p.__str__() for p in path.glob(f'*_{frame:06d}.jpg')]
        chunk.addPhotos(photos)
        for camera in chunk.cameras:
            camera.label = camera.label.split('_')[0]

    def _log_progress(self, title, progress):
        print(f'{title}: {progress:.2f}%')

    def _get_chunk(self, chunk_name) -> Metashape.Chunk:
        chunk_name = self._convert_chunk_name(chunk_name)
        for chunk in self._doc.chunks:
            if chunk.label == chunk_name:
                return chunk
        raise ValueError(f'No chunk named {chunk_name}')

    def _convert_chunk_name(self, chunk_name):
        # is calibrate
        if isinstance(chunk_name, str):
            return chunk_name
        # is frame number
        return f'{self._chunk_prefix_name}{chunk_name:06d}'

    def _import_camera_to_chunk(self, chunk):
        ref_sensor = chunk.sensors[0]
        ref_sensor.focal_length = self._sensor_focal_length
        ref_sensor.pixel_width = self._sensor_pixel_width
        ref_sensor.pixel_height = self._sensor_pixel_width
        return ref_sensor

    def _export(self, chunk):
        # get model
        model = chunk.model

        # geo
        vtx_idxs = []
        uv_idxs = []
        for face in model.faces:
            vtx_idxs += face.vertices
            uv_idxs += face.tex_vertices

        vtx_arr = np.array(
            [list(vtx.coord) for vtx in model.vertices],
            np.float32
        )
        uv_arr = np.array(
            [list(uv.coord) for uv in model.tex_vertices],
            np.float32
        )

        vtx_arr = vtx_arr[vtx_idxs]

        uv_arr = uv_arr[uv_idxs]
        uv_arr *= [1, -1]
        uv_arr += [0, 1.0]

        geo_arr = np.hstack((vtx_arr, uv_arr))

        # texture
        image = model.textures[0].image()
        tex_arr = np.fromstring(image.tostring(), dtype=np.uint8)
        tex_arr = tex_arr.reshape((image.width, image.height, 4))
        tex_arr = tex_arr[:, :, :3]

        # make dir
        self._export_path.mkdir(parents=True, exist_ok=True)
        export_4df_path = self._export_path / f'{self._current_frame:06d}.4df'

        FourdFrameManager.save_from_metashape(
            geo_arr, tex_arr, export_4df_path.__str__(), self._current_frame
        )

    def initial(self):
        self._create_chunk(self._calibrate_chunk_name)
        for f in range(self._start_frame, self._end_frame + 1):
            self._create_chunk(f)
        self.save(self._doc.chunks)

    def calibrate(self):
        # get chunk
        chunk = self._get_chunk(self._calibrate_chunk_name)

        # add photos
        self._import_images_to_chunk(chunk, self._cali_path, 0)

        # detect markers
        chunk.detectMarkers()

        # camera calibration sensor
        ref_sensor = self._import_camera_to_chunk(chunk)

        # camera calibration all
        for camera in chunk.cameras:
            sensor = chunk.addSensor(ref_sensor)
            sensor.label = f'sensor_{camera.label}'
            camera.sensor = sensor
        chunk.remove([ref_sensor])

        # build points
        chunk.matchPhotos(
            reference_preselection=False,
        )

        # align photos
        chunk.alignCameras(chunk.cameras)

        # set reference
        for marker in chunk.markers:
            if marker.label in self._marker_reference:
                marker.reference.location = \
                    Metashape.Vector(self._marker_reference[marker.label])
                marker.enabled = True
        chunk.updateTransform()

        # save
        self.save(chunk)

        # export cameras
        chunk.exportCameras(
            self._cameras_path.__str__(),
            Metashape.CamerasFormatBundler,
            bundler_save_list=False
        )
        for camera in chunk.cameras:
            camera.calibration.save(
                (self._job_path / f'{camera.label}.xml').__str__()
            )

    def resolve(self):
        # get chunk
        chunk = self._get_chunk(self._current_frame)

        # add photos
        self._import_images_to_chunk(
            chunk, self._shot_path, self._current_frame
        )

        # detect markers
        # chunk.detectMarkers()

        # keying image
        mask_path_list = keying_images(
            self._shot_path,
            self._masks_path,
            self._current_frame
        )

        # import masks
        for camera, mask_path in zip(chunk.cameras, mask_path_list):
            print(camera.label)
            print(mask_path)
            mask = Metashape.Mask()
            mask.load(mask_path)
            camera.mask = mask

        # import cameras
        ref_sensor = self._import_camera_to_chunk(chunk)

        # camera calibration all
        chunk.importCameras(
            self._cameras_path.__str__(),
            format=Metashape.CamerasFormatBundler
        )

        for camera in chunk.cameras:
            sensor = chunk.addSensor(ref_sensor)
            sensor.label = f'sensor_{camera.label}'
            calibration = sensor.calibration.copy()
            calibration.load(
                (self._job_path / f'{camera.label}.xml').__str__()
            )
            sensor.calibration = calibration
            camera.sensor = sensor

        chunk.remove([ref_sensor])

        # # build points
        # chunk.matchPhotos(
        #     filter_mask=True,
        #     reference_preselection=False,
        #     mask_tiepoints=False,
        #     keypoint_limit=0,
        #     tiepoint_limit=0
        # )
        # chunk.triangulatePoints()

        # # optimize cameras
        # chunk.optimizeCameras()
        #

        # build dense
        chunk.resetRegion()
        chunk.region.size = Metashape.Vector(
            self._region_size_large
        )
        chunk.buildDepthMaps(
          downscale=2
        )
        chunk.region.size = Metashape.Vector(
            self._region_size_small
        )
        chunk.buildDenseCloud(
            point_colors=False,
            keep_depth=False
        )

        # build mesh
        chunk.buildModel(
            face_count=Metashape.FaceCount.MediumFaceCount
        )
        chunk.smoothModel()

        # build texture
        chunk.buildUV()
        chunk.buildTexture()
        self.save(chunk)

        # align chunk
        # cali_chunk = self._get_chunk(5981)
        # self._doc.alignChunks(
        #     chunks=[cali_chunk.key, chunk.key],
        #     reference=cali_chunk.key,
        #     method=1
        # )

        # export 4df
        self._export(chunk)

        # save
        self.save(chunk)

    def save(self, chunks):
        if not isinstance(chunks, list):
            chunks = [chunks]
        self._doc.save(self._project_path.__str__(), chunks)

