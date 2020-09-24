import cv2
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


lower_green = np.array([55, 32, 20])
upper_green = np.array([70, 62, 255])


def mask_image(image_file, export_path):
    img = cv2.imread(image_file)

    # convert hsv
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # mask
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # smooth
    kernel = np.ones((3,3), np.uint8)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

    #apply
    m = closed == 255
    result = img.copy()
    result[m] = 0

    # export
    export_filename = f'{export_path}\\{Path(image_file).stem}.png'
    cv2.imwrite(
        export_filename,
        result,
        [cv2.IMWRITE_PNG_COMPRESSION, 5]
    )

    return export_filename


if '__main__' == __name__:
    folder = Path(r'C:\Users\moonshine\Desktop\test')
    export_path = r'C:\Users\moonshine\Desktop\export'

    with ProcessPoolExecutor() as executor:
        future_list = []

        for image_file in folder.glob('*.jpg'):
            future = executor.submit(
                mask_image, str(image_file), export_path
            )
            future_list.append(future)

        for future in as_completed(future_list):
            result = future.result()
            print(result)
