import yaml
import os


_location = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__))
)


class CameraStructure:
    def __init__(self):
        self._yaml = {}  # 設定資料

        filename = 'camera_structure.yaml'
        local_file = f'../settings_local/{filename}'

        if os.path.isfile(local_file):
            yaml_file = local_file
        else:
            yaml_file = os.path.join(_location, filename)

        with open(yaml_file, 'r') as f:
            self._yaml = yaml.load(f, Loader=yaml.FullLoader)

    def get_camera_number_by_id(self, camera_id):
        """取得相機的編號

        從相機序號查找編號

        Args:
            camera_id: 相機序號

        """
        return self._yaml['cameras'][camera_id]['number']

    def get_camera_id_by_number(self, find_number):
        for _id, value in self._yaml['cameras'].items():
            if find_number == value['number']:
                return _id
        raise ValueError(f"can't find camera id by number {find_number}")

    def get_camera_id_by_position(self, position):
        letter, num = list(position)
        num = int(num)
        number = self._yaml['truss_positions'][letter][num]
        return self.get_camera_id_by_number(number)

    def get_position_id_by_number(self, find_number):
        for position_letter, number_list in self._yaml['truss_positions'].items():
            num = 0
            for number in number_list:
                if number == find_number:
                    return f'{position_letter}{num}'
                num += 1
        raise ValueError(f"can't find position id by number {find_number}")

    def get_working_camera_ids(self):
        if not hasattr(self, '_working_camera_ids'):
            self._working_camera_ids = []
            for camera_number in self.get_camera_numbers_by_position_order():
                if camera_number is not None:
                    self._working_camera_ids.append(
                        self.get_camera_id_by_number(camera_number)
                    )
        return self._working_camera_ids

    def get_camera_numbers_by_position_order(self):
        camera_numbers = []
        for camera_number_list in self._yaml['truss_positions'].values():
            camera_numbers += camera_number_list
        return camera_numbers

    def get_position_letters(self):
        return self._yaml['truss_positions'].keys()


camera_structure = CameraStructure()  # 單例模式
