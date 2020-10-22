import OpenEXR
import Imath
import numpy as np
import cv2


mask_filename = r'C:\Users\moonshine\Desktop\002473\MaskImages\matte\19471991_002473.png'
mask_image = cv2.imread(mask_filename)


def apply_mask_to_exr(exr_path, mask_image, mask_value, output_path):
    load_file = OpenEXR.InputFile(exr_path)

    header = load_file.header()
    downscale = header['AliceVision:downscale']
    dw = header['dataWindow']
    size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)

    channel_type = header['channels']['Y'].type
    buf = load_file.channel('Y', channel_type)
    np_type = np.float32 if channel_type == Imath.PixelType(Imath.PixelType.FLOAT) else np.float16
    arr = np.frombuffer(buf, dtype=np_type).copy()
    arr.shape = (size[1], size[0])
    load_file.close()

    # load mask
    mask = cv2.resize(mask_image, None, fx=1 / downscale, fy=1 / downscale)
    mask = mask[:, :, 0]
    arr[mask == 255] = mask_value

    # save
    out_file = OpenEXR.OutputFile(output_path, header)
    out_file.writePixels({'Y': arr.tobytes()})
    out_file.close()


apply_mask_to_exr(
    r'C:\Users\moonshine\Desktop\002473\DepthMapEstimation\19471991_depthMap.exr',
    mask_image, -1,
    r'c:\Users\moonshine\Desktop\depth.exr'
)

apply_mask_to_exr(
    r'C:\Users\moonshine\Desktop\002473\DepthMapEstimation\19471991_simMap.exr',
    mask_image, 1,
    r'c:\Users\moonshine\Desktop\sim.exr'
)