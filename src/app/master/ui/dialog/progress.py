from PyQt5.Qt import QDialog, QProgressBar, Qt

from utility.setting import setting
from utility.define import BodyMode

from master.ui.custom_widgets import move_center, make_layout
from master.ui.state import state


class CacheProgressDialog(QDialog):
    _default = '''
    QProgressBar {
      min-width: 350px;
    }
    '''

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Caching')
        self._progress_bar = None
        self._setup_ui()
        self._prepare()

    def _setup_ui(self):
        self.setStyleSheet(self._default)
        self.setWindowFlags(
            Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint
        )

        shot = state.get('current_shot')
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            count = len(setting.get_working_camera_ids())

            if state.get('closeup_camera'):
                count += 1

            total_progress = (
                shot.frame_range[1] - shot.frame_range[0] + 1
            ) * count
        elif body_mode is BodyMode.MODEL:
            count = 1

            total_progress = len(state.get('frames'))

        self.setStyleSheet(self._default)
        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, total_progress)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat(r'%p% (%v/%m)')
        self._progress_bar.setValue(0)

        layout.addWidget(
            self._progress_bar
        )

        self.setLayout(layout)
        move_center(self)

    def _prepare(self):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            for camera_id in setting.get_working_camera_ids():
                state.on_changed(f'pixmap_{camera_id}', self._increase)
            if state.get('closeup_camera'):
                state.on_changed('pixmap_closeup', self._increase)
        elif body_mode is BodyMode.MODEL:
            state.on_changed('opengl_data', self._increase)

    def _increase(self):
        self._progress_bar.setValue(self._progress_bar.value() + 1)

        if self._progress_bar.value() == self._progress_bar.maximum():
            self.close()

    def showEvent(self, event):
        body_mode = state.get('body_mode')
        if body_mode is BodyMode.PLAYBACK:
            state.cast(
                'camera', 'cache_whole_shot', state.get('closeup_camera')
            )
        elif body_mode is BodyMode.MODEL:
            state.cast('resolve', 'cache_whole_job')
        state.set('caching', True)
        event.accept()

    def closeEvent(self, event):
        state.set('caching', False)
        event.accept()
