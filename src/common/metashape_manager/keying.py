from pathlib import Path


def keying_work(image_file, export_path):
    import cv2
    import numpy as np
    from pathlib import Path

    # path define
    image_file = Path(image_file)
    export_path = Path(export_path)
    filename = f'{image_file.stem}.png'
    export_file = export_path / filename

    # check exist
    if export_file.exists():
        return 'EXIST', export_file.__str__()

    # start
    lower_green = np.array([53, 36, 60])
    upper_green = np.array([74, 95, 180])

    img = cv2.imread(image_file.__str__())

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
    cv2.imwrite(
        export_file.__str__(),
        result,
        [cv2.IMWRITE_PNG_COMPRESSION, 5]
    )

    return 'DONE', export_file.__str__()


def keying_images(shot_path: Path, export_path: Path, frame):
    from concurrent.futures import ProcessPoolExecutor, as_completed

    export_path.mkdir(parents=True, exist_ok=True)

    with ProcessPoolExecutor() as executor:
        future_list = []
        mask_path_list = []

        for image_file in shot_path.glob(
                f'*_{frame:06d}.jpg'
        ):
            future = executor.submit(
                keying_work,
                image_file.__str__(),
                export_path.__str__()
            )
            future_list.append(future)

        for future in as_completed(future_list):
            result, mask_path = future.result()
            print(f'[{result}] {mask_path}')
            mask_path_list.append(mask_path)

    mask_path_list.sort()
    return mask_path_list
