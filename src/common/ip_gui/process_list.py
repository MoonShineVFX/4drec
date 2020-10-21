from PyQt5.Qt import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSpinBox, QCheckBox
)

from .state import state
from .range_slider import RangeSlider, RangeLabel
from .color_picker import ColorPicker
from .utility import update_process
from common.image_processor.parameter import *


class ProcessList(QWidget):
    def __init__(self):
        super().__init__()
        self._process_widgets = []

        self._setup_ui()

        state.on_changed('image_processor', self._update)

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def _update(self):
        for process_widget in self._process_widgets:
            process_widget.setParent(None)
        self._process_widgets = []

        image_processor = state.get('image_processor')
        for process in image_processor.get_processes():
            process_dock = ProcessDock(process)
            self._process_widgets.append(process_dock)
            self.layout().addWidget(process_dock)


class ProcessDock(QWidget):
    def __init__(self, process):
        super().__init__()
        self._process = process
        self._check_box = QCheckBox(process.get_name())

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        self._check_box.setChecked(self._process.is_enabled())
        self._check_box.stateChanged.connect(self._update_enabled)

        layout.addWidget(self._check_box)

        for parm in self._process.get_parameters():
            layout.addWidget(ParameterField(parm))

        self.setLayout(layout)

    def _update_enabled(self, value):
        self._process.set_enabled(value != 0)
        update_process()


class ParameterField(QWidget):
    def __init__(self, parm):
        super().__init__()
        self._parm = parm

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout()

        layout.addWidget(QLabel(self._parm.get_name()))

        # IntParameter
        if isinstance(self._parm, IntParameter):
            spin_box = QSpinBox()
            spin_box.setValue(self._parm.get_value())
            spin_box.valueChanged.connect(self._update)
            layout.addWidget(spin_box)
        # RangeParameter
        elif isinstance(self._parm, RangeParameter):
            range_slider = RangeSlider()
            range_slider.setRangeLimit(0, 255)
            range_slider.setRange(*self._parm.get_value())
            range_slider.valueChanged.connect(self._update)

            range_label = RangeLabel(range_slider)

            layout.addWidget(range_slider)
            layout.addWidget(range_label)
        # ColorParameter
        elif isinstance(self._parm, ColorParameter):
            color_picker = ColorPicker(self._parm.get_value())
            color_picker.valueChanged.connect(self._update)

            layout.addWidget(color_picker)

        self.setLayout(layout)

    def _update(self, value):
        self._parm.set_value(value)
        update_process()
