from PyQt5.Qt import QFileDialog

from master.ui.custom_widgets import LayoutWidget, PushButton
from master.ui.dialog import CacheProgressDialog
from master.ui.popup import popup
from master.ui.dialog import ShotSubmitDialog, SubmitProgressDialog
from master.ui.state import state

from .support_button import SupportButtonGroup


class RollPanel(LayoutWidget):
    def __init__(self, playback_control):
        super().__init__(spacing=24)
        self._playback_control = playback_control
        self._setup_ui()

    def _setup_ui(self):
        buttons = SupportButtonGroup(('Serial', 'Cache', 'Crop', 'Save'))
        buttons.buttons['Cache'].clicked.connect(self._on_cache)
        buttons.buttons['Save'].clicked.connect(self._on_save)

        self.addLayout(
            buttons
        )

        self.addWidget(SubmitButton())

    def showEvent(self, event):
        self.layout().insertLayout(1, self._playback_control)

    def hideEvent(self, event):
        self.layout().removeItem(self._playback_control)

    def _on_cache(self):
        popup(dialog=CacheProgressDialog)

    def _on_save(self):
        directory = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if directory is not None and directory != '':
            state.cast(
                'camera',
                'request_save_image',
                state.get('current_slider_value') +
                state.get('offset_frame'),
                directory
            )


class SubmitButton(PushButton):
    _submit_text = '  SUBMIT'
    _connect_text = '  CONNECT'

    def __init__(self):
        super().__init__(self._connect_text, 'submit', size=(180, 60))
        self._is_server_on = False
        self.clicked.connect(self._submit)

        state.on_changed('deadline_status', self._update)
        state.on_changed('current_shot', self._update_shot)

        self._check_server()

    def _check_server(self):
        state.cast(
            'project', 'check_deadline_server'
        )

    def _update(self):
        check_result = state.get('deadline_status')
        self.setText(self._submit_text if check_result else self._connect_text)
        self._is_server_on = check_result

        if check_result:
            self._submit()

    def _update_shot(self):
        shot = state.get('current_shot')

        if shot is None:
            return

        if shot.is_cali() and shot.state == 2:
            self.setEnabled(False)
        else:
            self.setEnabled(True)

    def _submit(self):
        if self._is_server_on:
            shot = state.get('current_shot')

            if not shot.is_cali():
                result = popup(dialog=ShotSubmitDialog)

                if result:
                    popup(
                        dialog=SubmitProgressDialog,
                        dialog_args=(
                            result['name'],
                            result['frames'],
                            result['parms']
                        )
                    )
            else:
                state.cast(
                    'camera',
                    'submit_shot',
                    shot.name, [0], {}
                )
        else:
            self._check_server()
