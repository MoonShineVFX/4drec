import cv2
from common.jpeg_coder import jpeg_coder
from time import perf_counter

test_file = r"C:\Users\moonshine\Desktop\test.ppm"
image = cv2.imread(test_file)

t = perf_counter()
jpeg_coder.encode(image, quality=90)
print(perf_counter() - t)
