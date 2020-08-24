import cv2
import numpy as np

from utility.jpeg_coder import jpeg_coder


class CameraImage():
    """相機圖像

    將 PySpin 相機取出的二進制陣列做一個包裝管理，方便做進階的操作

    Args:
        data: 二進制陣列
        width: 圖像寬
        height: 圖像高

    """

    def __init__(self, data, width, height):
        self._data = data  # 二進制陣列
        self._width = width  # 圖像寬
        self._height = height  # 圖像高

    def _raw_to_cv2(self):
        """將二進制陣列轉成 cv2 的圖像"""
        im = np.frombuffer(self._data, dtype=np.uint8)
        im = im.reshape((self._height, self._width))
        im = cv2.cvtColor(im, cv2.COLOR_BAYER_RG2RGB)
        return im

    def _rescale(self, image, scale_length):
        """縮放圖像

        縮放圖像，最長邊會等於指定的長度

        Args:
            image: 圖像
            scale_length: 最長邊長度

        """
        if self._width > self._height:
            sw = scale_length
            sh = int(scale_length * self._height / self._width)
        else:
            sh = scale_length
            sw = int(scale_length * self._width / self._height)
        return cv2.resize(image, (sw, sh))

    def convert_jpeg(self, quality, scale_length=None):
        """轉成JPEG

        傳送到 master 前的壓縮，scale_length 指定的話就會縮放影像

        Args:
            quality: JPEG品質
            scale_length: 最長邊長度

        """
        im = self._raw_to_cv2()
        if scale_length is not None:
            im = self._rescale(im, scale_length)

        return jpeg_coder.encode(im, quality=quality)

    def save_png(self, path):
        im = self._raw_to_cv2()
        cv2.imwrite(path, im)

    def write(self, file):
        """寫入檔案

        將自身資料寫入到指定檔案裏頭

        """
        np.save(file, self._data, False, False)

    def get_size(self):
        """取得圖像尺寸"""
        return (self._width, self._height)
