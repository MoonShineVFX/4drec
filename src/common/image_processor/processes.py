import numpy as np
import cv2
from pathlib import Path

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
        return self._enabled

    def set_enabled(self, enabled):
        self.set_modified()
        self._enabled = enabled

    def is_modified(self):
        return self._modified

    def set_modified(self, toggle=True):
        self._modified = toggle

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
        self.set_modified(False)
        if not self.is_enabled():
            return
        self._result = self._process(image)


class FileProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'File',
            [
                FileParameter('file', r"C:\Users\moonshine\Desktop\samples\19471994_002473.jpg")
            ]
        )

    def _process(self, image):
        file_path = self.get_parameter('file').get_value()
        if not Path(file_path).is_file():
            return np.zeros((100, 100, 4), dtype=np.uint8)
        image = cv2.imread(file_path)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)
        return image


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
        if factor <= 1:
            return image
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


class RemoveSmallAreaProcess(ProcessStack):
    def __init__(self):
        super().__init__(
            'Remove Small Area',
            [
                IntParameter('threshold', 1200)
            ]
        )

    def _process(self, image):
        binary = (image[:, :, 3] == 0).astype(np.uint8)
        num_labels, label_map, stats, centroids = cv2.connectedComponentsWithStats(
            binary, 4, cv2.CV_32S
        )

        keep_labels = []
        for i in range(1, num_labels):
            x, y, w, h, area = stats[i]
            if area > self.get_parameter('threshold').get_value():
                keep_labels.append(i)

        matte = np.in1d(label_map, keep_labels).reshape(label_map.shape)
        image[~matte, 3] = 255

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
