from .processes import *
import cv2


class ImageProcessor:
    def __init__(self,):
        self._process_list = []

        self._initialize()

    def _initialize(self):
        self._process_list = [
            FileProcess(),
            ResizeProcess(),
            ChromaKeyingProcess(),
            MorphOpenProcess(),
            MorphCloseProcess(),
            RemoveSmallAreaProcess(),
            ApplyMaskProcess()
        ]

    def get_image(self):
        for effect in self._process_list[::-1]:
            if effect.is_enabled():
                return effect.get_result()

    def get_processes(self):
        return self._process_list

    def render(self):
        source = None
        modified = False

        for process in self._process_list:
            if (modified or process.is_modified()):
                modified = True
                process.process(source)

            if process.is_enabled():
                source = process.get_result()

    def export(self, image_path):
        cv2.imwrite(image_path, self.get_image())
