from PyQt5.Qt import (
    QWidget, QHBoxLayout, QToolButton, QLineEdit, QFileDialog,
    QPushButton, QVBoxLayout
)
from pathlib import Path


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self._line_edit = QLineEdit()
        self._browse_button = QToolButton()
        self._prev_button = QPushButton('<')
        self._next_button = QPushButton('>')
        self._file_list = []

        self._setup_ui()

        self._line_edit.textChanged.connect(self._on_path_changed)
        self.valueChanged = self._line_edit.textChanged

    def _setup_ui(self):
        layout = QVBoxLayout()
        up_layout = QHBoxLayout()
        down_layout = QHBoxLayout()

        self._browse_button.setText('...')
        self._browse_button.clicked.connect(self._pick_file)

        self._prev_button.clicked.connect(lambda: self._next_file(-1))
        self._next_button.clicked.connect(lambda: self._next_file(1))
        self._toggle_buttons(False)

        up_layout.addWidget(self._line_edit)
        up_layout.addWidget(self._browse_button)
        down_layout.addWidget(self._prev_button)
        down_layout.addWidget(self._next_button)

        layout.addLayout(up_layout)
        layout.addLayout(down_layout)
        self.setLayout(layout)

    def _pick_file(self):
        file_path = QFileDialog.getOpenFileName()[0]
        if file_path is not None and file_path != '':
            self._line_edit.setText(file_path)

    def _next_file(self, step):
        file = Path(self._line_edit.text())
        if not file.is_file():
            return

        current_path = self._line_edit.text()

        idx = self._file_list.index(Path(current_path))
        idx += step
        if idx >= len(self._file_list):
            idx = 0
        elif idx < 0:
            idx = len(self._file_list) - 1

        self._line_edit.setText(str(self._file_list[idx]))

    def _toggle_buttons(self, toggle):
        for button in (self._prev_button, self._next_button):
            button.setEnabled(toggle)

    def _on_path_changed(self, path):
        file = Path(self._line_edit.text())
        if not file.is_file():
            self._toggle_buttons(False)
            return
        self._file_list = list(file.parent.glob(f'*{file.suffix}'))
        if len(self._file_list) <= 1:
            self._toggle_buttons(False)
            return
        self._toggle_buttons(True)
