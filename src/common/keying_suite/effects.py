import numpy as np
import cv2

from .parameter import *
from .payload import ImagePayload


class EffectStack:
    def __init__(self, name, parameters):
        self._name = name
        self._parameters = parameters

    def get_parameter(self, parm_name):
        for parm in self._parameters:
            if parm_name == parm.get_name():
                return parm
        raise KeyError(
            f'No {parm_name} found in {self._name}.'
        )

    def process(self, payload):
        pass


class ChromaKeyingEffect(EffectStack):
    def __init__(self):
        super().__init__(
            'Chroma Key',
            [
                RangeParameter('hue', (55, 70)),
                RangeParameter('sat', (32, 62)),
                RangeParameter('val', (20, 255))
            ]
        )

    def _get_key_range(self, lower=True):
        idx = 0 if lower else 1
        return np.array([
            self.get_parameter('hue').get_value()[idx],
            self.get_parameter('sat').get_value()[idx],
            self.get_parameter('val').get_value()[idx],
        ])

    def process(self, payload):
        image = payload.get(ImagePayload.ORIGINAL)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        result = cv2.inRange(
            hsv,
            self._get_key_range(lower=True),
            self._get_key_range(lower=False)
        )
        payload.set(ImagePayload.MASK, result)


class MorphOpenEffect(EffectStack):
    def __init__(self):
        super().__init__(
            'Morph Open',
            [
                IntParameter('kernel', 3)
            ]
        )

    def process(self, payload):
        kv = self.get_parameter('kernel').get_value()
        kernel = np.ones((kv, kv), np.uint8)
        mask = payload.get(ImagePayload.MASK)
        result = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        payload.set(ImagePayload.MASK, result)


class MorphCloseEffect(EffectStack):
    def __init__(self):
        super().__init__(
            'Morph Close',
            [
                IntParameter('kernel', 3)
            ]
        )

    def process(self, payload):
        kv = self.get_parameter('kernel').get_value()
        kernel = np.ones((kv, kv), np.uint8)
        mask = payload.get(ImagePayload.MASK)
        result = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        payload.set(ImagePayload.MASK, result)


class ApplyMaskEffect(EffectStack):
    def __init__(self):
        super().__init__('Apply Mask', [])

    def process(self, payload):
        image = payload.get(ImagePayload.ORIGINAL).copy()
        mask = payload.get(ImagePayload.MASK)
        m = mask == 255
        image[m] = 0
        payload.set(ImagePayload.RESULT, image)
