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

    def _initialize(self):
        self._effect_list = [
            ChromaKeyingEffect(),
            MorphOpenEffect(),
            MorphCloseEffect(),
            ApplyMaskEffect()
        ]

    def get_image(self, image_name):
        return self._payload.get(image_name)

    def get_effects(self):
        return self._effect_list

    def update(self):
        self._payload.clear()
        for effect in self._effect_list:
            effect.process(self._payload)

    def export(self, image_path):
        image = self._payload.get(ImagePayload.RESULT)
        cv2.imwrite(image_path, image)
