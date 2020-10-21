import cv2
from PyQt5.Qt import QImage, QPixmap

from .state import state


def update_process():
    state.get('image_processor').render()
    state.set('update_process', None)


def convert_pixmap_from_cvimage(image):
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    height, width, _ = image.shape
    q_image = QImage(
        image.data,
        width,
        height,
        3 * width,
        QImage.Format_RGB888
    )
    return QPixmap.fromImage(q_image)