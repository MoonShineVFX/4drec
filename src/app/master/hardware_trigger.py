import serial
import serial.tools.list_ports

from utility.setting import setting
from utility.logger import get_prefix_log
from utility.define import UIEventType

from master.ui import ui


class HardwareTrigger():
    def __init__(self):
        self._log = get_prefix_log('<Arduino> ')

        try:
            self._ser = serial.Serial(
                self.get_arduino(), 9600
            )

            self.get_response()

            ui.dispatch_event(
                UIEventType.HAS_ARDUINO,
                True
            )
        except IOError as error:
            self._log.error('Not found!')
            return

    def get_arduino(self):
        for pinfo in serial.tools.list_ports.comports():
            if 'CH340' in pinfo.description:
                return pinfo.device
        raise IOError('Cound not find an arduino')

    def get_response(self):
        resp = self._ser.readline().decode()
        self._log.info('Resp: ' + resp)

    def trigger(self):
        self._log.info('Trigger')
        self._ser.write(b'0')
        self.get_response()

    def close(self):
        self._ser.close()


hardware_trigger = HardwareTrigger()
