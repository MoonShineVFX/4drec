class ImagePayload:
    ORIGINAL = 0
    MASK = 1
    RESULT = 2

    def __init__(self, original):
        self._data = {
            self.ORIGINAL: original,
            self.MASK: None,
            self.RESULT: None
        }

    def get(self, image_name):
        image = self._data[image_name]
        if image is None:
            raise KeyError(f'No name {image_name} found in payload.')
        return image

    def set(self, image_type, image_name):
        self._data[image_type] = image_name

    def clear(self):
        for key in self._data.keys():
            if key == self.ORIGINAL:
                continue
            self._data[key] = None
