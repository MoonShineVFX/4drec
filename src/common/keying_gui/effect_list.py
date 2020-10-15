from PyQt5.Qt import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSpinBox
)

from .state import state
from common.keying.parameter import *


class EffectList(QWidget):
    def __init__(self):
        super().__init__()
        self._effect_widgets = []

        self._setup_ui()

        state.on_changed('keying_image', self._update)

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

    def _update(self):
        for effect_widget in self._effect_widgets:
            effect_widget.setParent(None)
        self._effect_widgets = []

        keying_image = state.get('keying_image')
        for effect in keying_image.get_effects():
            effect_dock = EffectDock(effect)
            self._effect_widgets.append(effect_dock)
            self.layout().addWidget(effect_dock)


class EffectDock(QWidget):
    def __init__(self, effect):
        super().__init__()
        self._effect = effect
        self._label = QLabel(effect.get_name())

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self._label)

        for parm in self._effect.get_parameters():
            layout.addWidget(ParameterField(parm))

        self.setLayout(layout)


class ParameterField(QWidget):
    def __init__(self, parm):
        super().__init__()
        self._parm = parm

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout()

        layout.addWidget(QLabel(self._parm.get_name()))

        if isinstance(self._parm, IntParameter):
            spin_box = QSpinBox()
            spin_box.setValue(self._parm.get_value())
            spin_box.valueChanged.connect(self._update)
            layout.addWidget(spin_box)
        elif isinstance(self._parm, RangeParameter):
            pass

        self.setLayout(layout)

    def _update(self, value):
        self._parm.set_value(value)
