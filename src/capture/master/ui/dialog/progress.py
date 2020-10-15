from PyQt5.Qt import QDialog, QProgressBar, Qt

from utility.setting import setting
from utility.define import BodyMode

from master.ui.custom_widgets import move_center, make_layout
from master.ui.state import state


class ProgressDialog(QDialog):
    _default = '''
    QProgressBar {
      min-width: 350px;
    }
    '''

    def __init__(self, parent, title, total_progress):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._total_progress = total_progress

        self._progress_bar = None

        self._setup_ui()
        self._prepare()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint
        )

        self.setStyleSheet(self._default)
        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, self._total_progress)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat(r'%p% (%v/%m)')
        self._progress_bar.setValue(0)

        layout.addWidget(
            self._progress_bar
        )

        self.setLayout(layout)
        move_center(self)

    def _prepare(self):
        return

    def increase(self, step=1):
        self._progress_bar.setValue(self._progress_bar.value() + step)

        if self._progress_bar.value() == self._progress_bar.maximum():
            self.close()

    def _on_show(self):
        return

    def _on_close(self):
        return

    def showEvent(self, event):
        self._on_show()
        event.accept()

    def closeEvent(self, event):
        self._on_close()
        event.accept()


class ExportProgressDialog(ProgressDialog):
    def __init__(self, parent, export_path):
        super().__init__(parent, 'Exporting', len(state.get('frames')))
        self._export_path = export_path

    def _prepare(self):
        state.on_changed('tick_export', self.increase)

    def _on_show(self):
        offset_frame = state.get('offset_frame')
        frames = state.get('frames')
        state.cast(
            'resolve',
            'export_model',
            state.get('current_project'),
            state.get('current_shot'),
            state.get('current_job'),
            [f + offset_frame for f in frames],
            self._export_path
        )

class CacheProgressDialog(ProgressDialog):
    def __init__(self, parent):
        super().__init__(parent, 'Caching', self._get_total_progress())

    def _get_total_progress(self):
        shot = state.get('current_shot')
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            count = len(setting.get_working_camera_ids())

            if state.get('closeup_camera'):
                count += 1

            return (
                shot.frame_range[1] - shot.frame_range[0] + 1
            ) * count
        elif body_mode is BodyMode.MODEL:
            return len(state.get('frames'))

    def _prepare(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            for camera_id in setting.get_working_camera_ids():
                state.on_changed(f'pixmap_{camera_id}', self.increase)
            if state.get('closeup_camera'):
                state.on_changed('pixmap_closeup', self.increase)
        elif body_mode is BodyMode.MODEL:
            state.on_changed('opengl_data', self.increase)

    def _on_show(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            state.cast(
                'camera', 'cache_whole_shot', state.get('closeup_camera')
            )
        elif body_mode is BodyMode.MODEL:
            state.cast('resolve', 'cache_whole_job')
        state.set('caching', True)

    def _on_close(self):
        state.set('caching', False)


class SubmitProgressDialog(ProgressDialog):
    def __init__(self, parent, job_name, job_frames, job_parms):
        camera_count = len(setting.get_working_camera_ids())
        super().__init__(parent, 'Submitting', len(job_frames) * camera_count)
        self._job_name = job_name
        self._job_frames = job_frames
        self._job_parms = job_parms

    def _prepare(self):
        state.on_changed('tick_submit', self._on_submit)

    def _on_submit(self):
        submit_count = state.get('tick_submit')
        current_count = self._progress_bar.value()
        if current_count >= submit_count:
            return
        self.increase(submit_count - current_count)

    def _on_show(self):
        state.cast(
            'camera',
            'submit_shot',
            self._job_name,
            self._job_frames,
            self._job_parms
        )
