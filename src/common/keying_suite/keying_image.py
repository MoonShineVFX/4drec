from .effects import *
import cv2
from .payload import ImagePayload


class KeyingImage:
    def __init__(self, image_path):
        image = cv2.imread(image_path)
        self._payload = ImagePayload(image)
        self._result_image = None
        self._effect_list = []

        self._initialize()
        self.update()

    def _initialize(self):
        self._effect_list = [
            ChromaKeyingEffect(),
            MorphOpenEffect(),
            MorphCloseEffect(),
            ApplyMaskEffect()
        ]

    def update(self):
        self._payload.clear()
        for effect in self._effect_list:
            effect.process(self._payload)
