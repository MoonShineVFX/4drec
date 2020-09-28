import OpenEXR
import Imath
import numpy as np
import cv2


image_filename = r'C:\Users\moonshine\Desktop\020632\DepthMapEstimation\19471991_depthMap.exr'
mask_filename = r'C:\Users\moonshine\Desktop\020632\MaskImages\matte\19471991_020632.png'

# load image
load_file = OpenEXR.InputFile(image_filename)

header = load_file.header()
downscale = header['AliceVision:downscale']
dw = header['dataWindow']
size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)

buf = load_file.channel('Y', Imath.PixelType(Imath.PixelType.FLOAT))
arr = np.fromstring(buf, dtype=np.float32)
arr.shape = (size[1], size[0])
load_file.close()

# load mask
mask = cv2.imread(mask_filename)
mask = cv2.resize(mask, None, fx=1 / downscale, fy=1 / downscale)
mask = mask[:, :, 0]
arr[mask == 255] = -1

# save
out_file = OpenEXR.OutputFile(r'c:\Users\moonshine\Desktop\test.exr', header)
out_file.writePixels({'Y': arr.tobytes()})
out_file.close()
