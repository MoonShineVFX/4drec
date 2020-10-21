import numpy as np
import cv2

from .parameter import *


class ProcessStack:
    def __init__(self, name, parameters):
        self._name = name
        self._parameters = parameters
        self._modified = True
        self._enabled = True

        self._result = None

        for parm in self._parameters:
            parm.on_changed(self.set_modified)

    def is_enabled(self):
        self.set_modified()
        return self._enabled

    def set_enabled(self, enabled):
        self._enabled = enabled

    def is_modified(self):
        return self._modified

    def set_modified(self):
        self._modified = True

    def get_name(self):
        return self._name

    def get_parameter(self, parm_name):
        for parm in self._parameters:
            if parm_name == parm.get_name():
                return parm
        raise KeyError(
            f'No {parm_name} found in {self._name}.'
        )

    def get_parameters(self):
        return self._parameters

    def get_result(self):
        if self._result is not None:
            return self._result.copy()
        return None

    def _process(self, image):
        return

    def process(self, image):
        self._modified = False
        if not self.is_enabled():
            return
        self._result = self._process(image)


class ResizeProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'Resize',
            [
                IntParameter('factor', 2)
            ]
        )

    def _process(self, image):
        factor = self.get_parameter('factor').get_value()
        image = cv2.resize(image, None, fx=1 / factor, fy=1 / factor)
        return image


class ChromaKeyingProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'Chroma Key',
            [
                RangeParameter('hue', (56, 76)),
                RangeParameter('sat', (42, 95)),
                RangeParameter('val', (40, 180))
            ]
        )

    def _get_key_range(self, lower=True):
        idx = 0 if lower else 1
        return np.array([
            self.get_parameter('hue').get_value()[idx],
            self.get_parameter('sat').get_value()[idx],
            self.get_parameter('val').get_value()[idx],
        ])

    def _process(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            self._get_key_range(lower=True),
            self._get_key_range(lower=False)
        )
        image[:, :, 3] = mask
        return image


class MorphOpenProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'Morph Open',
            [
                IntParameter('kernel', 3)
            ]
        )

    def _process(self, image):
        kv = self.get_parameter('kernel').get_value()
        kernel = np.ones((kv, kv), np.uint8)
        image[:, :, 3] = cv2.morphologyEx(
            image[:, :, 3],
            cv2.MORPH_OPEN, kernel
        )
        return image


class MorphCloseProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'Morph Close',
            [
                IntParameter('kernel', 3)
            ]
        )

    def _process(self, image):
        kv = self.get_parameter('kernel').get_value()
        kernel = np.ones((kv, kv), np.uint8)
        image[:, :, 3] = cv2.morphologyEx(
            image[:, :, 3],
            cv2.MORPH_CLOSE, kernel
        )
        return image


class ApplyMaskProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'Apply Mask',
            [
                ColorParameter('mask color', (255, 0, 255, 255))
            ]
        )

    def _process(self, image):
        m = image[:, :, 3] == 255

        image[m, :] = self.get_parameter('mask color').get_value()
        return image
