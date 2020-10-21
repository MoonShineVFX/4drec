from .processes import *
import cv2


class ImageProcessor:
    def __init__(self, image_path):
        image = cv2.imread(image_path)
        self._source_image = cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)
        self._effect_list = []

        self._initialize()

    def _initialize(self):
        self._effect_list = [
            ResizeProcess(),
            ChromaKeyingProcess(),
            MorphOpenProcess(),
            MorphCloseProcess(),
            ApplyMaskProcess()
        ]

    def get_image(self):
        for effect in self._effect_list[::-1]:
            if effect.is_enabled():
                return effect.get_result()

    def get_processes(self):
        return self._effect_list

    def render(self):
        source = self._source_image
        modified = False
        for effect in self._effect_list:
            if (modified or effect.is_modified):
                modified = True
                effect.process(source)

            if effect.is_enabled():
                source = effect.get_result()

    def export(self, image_path):
        cv2.imwrite(image_path, self.get_image())
