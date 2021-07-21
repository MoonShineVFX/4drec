from pathlib import Path
import shutil


frame_range = (5981, 6011)
shot_path = Path(r'Q:\shots\5fa4c479318496d390b56949')
export_path = Path(r'Q:\metadata\4dsample')


for frame in range(frame_range[0], frame_range[1] + 1):
    frame_path = export_path / f'{frame:06d}'
    frame_path.mkdir(parents=True, exist_ok=True)
    for jpg_file in shot_path.glob(f'*_{frame:06d}.jpg'):
        filename = jpg_file.stem
        camera_id, _ = filename.split('_')

        target_path = frame_path / f'{camera_id}.jpg'
        shutil.copy(jpg_file, target_path)
