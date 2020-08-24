from win10toast import ToastNotifier
from PyQt5.Qt import (
    Qt, QDialog, QLabel, QDialogButtonBox,
    QLineEdit, QApplication
)

from .custom_widgets import make_layout, move_center


class MessageBox(QDialog):
    _default = '''
    MessageBox {
      min-width: 280px;
    }

    QLabel {
      font-size: 14px;
    }

    QLineEdit {
      font-size: 18px;
      min-height: 30px;
      padding: 4px 16px;
    }

    QDialogButtonBox {
      min-height: 30px;
    }

    '''

    def __init__(self, parent, title, message, field, confirm):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._buttons = None
        self._edit_text = None
        self._setup_ui(message, field, confirm)

    def _setup_ui(self, message, field, confirm):
        self.setStyleSheet(self._default)
        layout = make_layout(
            horizon=False,
            margin=24,
            spacing=24
        )

        if message != '':
            label = QLabel(message)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

        if field != '':
            self._edit_text = QLineEdit()
            if ':' in field:
                field, default_text = field.split(':')
                self._edit_text.setText(default_text)
            self._edit_text.setPlaceholderText(field)
            layout.addWidget(self._edit_text)

            buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        elif confirm:
            buttons = QDialogButtonBox.Ok
        else:
            buttons = QDialogButtonBox.Yes | QDialogButtonBox.No

        self._buttons = QDialogButtonBox(buttons)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout.addWidget(
            self._buttons
        )

        self.setLayout(layout)

        move_center(self)

    def get_result(self):
        if self._edit_text is not None:
            return self._edit_text.text().strip()
        return True


def popup(
    parent=None, title='MessageBox', message='', field='', dialog=None,
    confirm=False
):
    if parent is None:
        from .main import MainWindow
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                parent = widget
                break

    if dialog is None:
        dialog = MessageBox(parent, title, message, field, confirm)
    else:
        dialog = dialog(parent)

    dialog.setWindowFlags(
        dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint
    )

    exit_code = dialog.exec_()

    if exit_code == 1:
        if hasattr(dialog, 'get_result'):
            return dialog.get_result()
        return True
    else:
        return False


def notify(title, description):
    toaster = ToastNotifier()
    toaster.show_toast(
        title,
        description,
        icon_path='source/ico.ico',
        duration=10,
        threaded=True
    )
