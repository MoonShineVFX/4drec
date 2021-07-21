def mask_image(image_file, export_path):
    import cv2
    import numpy as np
    from pathlib import Path

    lower_green = np.array([53, 36, 60])
    upper_green = np.array([74, 95, 180])

    img = cv2.imread(image_file)

    # convert hsv
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # mask
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # smooth
    okernel = np.ones((7, 7), np.uint8)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, okernel)
    ckernel = np.ones((6, 6), np.uint8)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, ckernel)

    # remove small area
    binary = (closed == 0).astype(np.uint8)
    num_labels, label_map, stats, centroids = cv2.connectedComponentsWithStats(
        binary, 4, cv2.CV_32S
    )

    keep_labels = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area > 5000:
            keep_labels.append(i)

    matte = np.in1d(label_map, keep_labels).reshape(label_map.shape)
    closed[~matte] = 255
    result = np.invert(closed)

    # export
    image_file = Path(image_file)
    frame = int(image_file.parent.stem) - 5980
    filename = image_file.stem
    cv2.imwrite(
        f'{export_path}\\{filename}_{frame}.png',
        result,
        [cv2.IMWRITE_PNG_COMPRESSION, 5]
    )

    return f'{filename}_{frame}'


if __name__ == '__main__':
    from pathlib import Path
    from concurrent.futures import ProcessPoolExecutor, as_completed

    # start
    folder = Path(r"Q:\metadata\4dsample")

    with ProcessPoolExecutor() as executor:
        future_list = []

        for image_file in folder.rglob(
                f'*.jpg'
        ):
            future = executor.submit(
                mask_image, str(image_file),
                r"Q:\metadata\4dsample_mask"
            )
            future_list.append(future)

        for future in as_completed(future_list):
            result = future.result()
            print(result)
