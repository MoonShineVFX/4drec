import glob
import numpy
import cv2


margin = 100
res = [2480, 3508]

def get_coord(order, w, h):
    x = 0
    y = 0
    x = margin + order * (res[0] - w - 2 * margin)
    y = margin + order * int(res[1] / 2)
    return (x, y)


images = list(
    glob.glob(
        'C:/Users/moonshine/Desktop/'
        'marker_mapper_1.0.12w64/36h12/*.png'
    )
)
images.sort(key=lambda i: int(i.split('\\')[-1].split('.')[0]))


for r in range(124):
    canvas = numpy.ones((res[1], res[0], 3), dtype=numpy.uint8)
    canvas *= 255
    numbers = []
    for i in range(2):
        t = i + r * 2
        numbers.append(t)
        image: numpy.ndarray = cv2.imread(images[t])
        h, w, _ = image.shape
        image = cv2.resize(image, (int(h * 1.5), int(w * 1.5)), interpolation=cv2.INTER_CUBIC)
        h, w, _ = image.shape
        x, y = get_coord(i, w, h)

        canvas[y:y + h, x:x + w] = image

    numbers = '-'.join([f'{n:03d}' for n in numbers])
    cv2.putText(
        canvas,
        f'4DREC P{r:02d}_{numbers}',
        (1600, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 0, 0),
        2,
        cv2.LINE_AA
    )

    cv2.imwrite(
        'C:/Users/moonshine/Desktop/'
        f'marker_mapper_1.0.12w64/output_big/{r:02d}.png',
        canvas
    )