import yaml
import os
import platform
import glob


class SettingManager:
    """設定管理

    將 settings 資料夾的所有 yaml 設定檔整合
    取得設定資訊的方式是以 property 的方式，取代字典拿法的不便

    """

    def __init__(self):
        self._settings = {}  # 設定資料

        # 蒐集所有 settings 資料夾的 yaml 檔案
        files = glob.glob('settings/*.yaml')
        for file in files:
            with open(file, 'r') as f:
                self._settings.update(yaml.load(f, Loader=yaml.FullLoader))

        # 如果是 slave 就建立錄製資料夾
        if not self.is_master():
            self._make_record_folder()

    def __getattr__(self, attr):
        """取得設定檔資訊，是字典的話會以 SettingProperty 包裝回傳"""
        if attr not in self._settings:
            raise AttributeError(
                f'[{attr}] not found in settings'
            )

        value = self._settings[attr]

        # 判斷是否是字典
        if isinstance(value, dict):
            return SettingProperty(value)
        else:
            return value

    def _make_record_folder(self):
        """創建錄製用資料夾

        檢查電腦有沒有錄製用的資料夾，沒有的話就創建

        """
        for drive in self.record.drives:
            path = f'{drive}:/{self.record.folder_name}/'
            os.makedirs(path, exist_ok=True)

    @staticmethod
    def is_master():
        """確認是否是 master"""
        return os.environ['4DREC_TYPE'] == 'MASTER'

    def get_host_address(self):
        """取得 Master 連線地址"""
        return (
            self.host_address.ip,
            self.host_address.port
        )

    def get_deadline_address(self):
        """取得 Deadline Webservice 連線地址"""
        return (
            self.deadline_address.ip,
            self.deadline_address.port
        )

    def get_record_folder_path(self, camera_index):
        """取得錄製路徑

        藉由順序，輪流分配所設定的硬碟數量產生的路徑

        """
        drives = self.record.drives
        idx = camera_index % len(drives)
        drive = drives[idx]
        folder = self.record.folder_name
        return f'{drive}:/{folder}/'

    def get_camera_number_by_id(self, camera_id):
        """取得相機的編號

        從相機序號查找編號

        Args:
            camera_id: 相機序號

        """
        return self.cameras[camera_id]['number']

    def get_slave_cameras_count(self):
        camera_count = 0
        slave_index = self.get_slave_index()
        start_idx = slave_index * 3
        for camera_id in self.get_camera_numbers_by_position_order()[start_idx:start_idx + 3]:
            if camera_id is not None:
                camera_count += 1
        return camera_count

    def get_camera_id_by_number(self, find_number):
        for id, value in self.cameras.items():
            if find_number == value['number']:
                return id
        raise ValueError(f"can't find camera id by number {find_number}")

    def get_position_id_by_number(self, find_number):
        for position_letter, number_list in self.truss_positions.items():
            num = 0
            for number in number_list:
                if number == find_number:
                    return f'{position_letter}{num}'
                num += 1
        raise ValueError(f"can't find position id by number {find_number}")

    def get_working_camera_ids(self):
        if not hasattr(self, '__working_camera_ids'):
            self.__working_camera_ids = []
            for camera_number in self.get_camera_numbers_by_position_order():
                if camera_number is not None:
                    self.__working_camera_ids.append(
                        self.get_camera_id_by_number(camera_number)
                    )
        return self.__working_camera_ids

    def get_slave_index(self):
        return self.slaves.index(platform.node())

    def get_camera_numbers_by_position_order(self):
        camera_numbers = []
        for camera_number_list in self.truss_positions.values():
            camera_numbers += camera_number_list
        return camera_numbers

    def save_camera_parameters(self, parms):
        save_parms = {'camera_user_parameters': parms}
        with open('settings/user_parameters.yaml', 'w') as f:
            yaml.dump(save_parms, f)
        self._settings.update(save_parms)

    def has_user_parameters(self):
        return 'camera_user_parameters' in self._settings

    def apply(self, data):
        self._settings.update(data)


class SettingProperty(dict):
    """屬性包裝

    繼承字典，並將字典包裝起來以 property 的方式回傳

    Args:
        value: 值

    """

    def __init__(self, value):
        super().__init__()
        self.update(value)

    def __getattr__(self, attr):
        if attr not in self:
            raise AttributeError(
                f'{attr} not found in {self}'
            )

        value = self[attr]
        if isinstance(value, dict):
            return SettingProperty(value)
        else:
            return value


setting = SettingManager()  # 單例模式
