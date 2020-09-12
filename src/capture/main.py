import sys
import os
import ctypes
import time


def start():
    """根據 bat 產生的 argument 去執行對應的程式(master / slave)"""

    # 檢查參數只有一個
    if len(sys.argv) < 2:
        print('>> Invalid argument count')
        return

    _4DREC_TYPE = sys.argv[1]

    if _4DREC_TYPE not in ('MASTER', 'SLAVE'):
        print('>> Invalid argument value')
        return

    # 將 4DREC_TYPE 寫到全域變數
    os.environ['4DREC_TYPE'] = sys.argv[1]
    ctypes.windll.kernel32.SetConsoleTitleW(
        '4DREC ' + _4DREC_TYPE + ' COMMAND'
    )
    print(f'>> Launch 4D REC <{_4DREC_TYPE}>')

    # 執行程式
    if _4DREC_TYPE == 'MASTER':
        from master.master import start_master
        start_master()
    elif _4DREC_TYPE == 'SLAVE':
        # delay from restart
        if len(sys.argv) >= 3:
            delay_seconds = int(sys.argv[2])
            print(f'Wait {delay_seconds}s from restart.')
            time.sleep(delay_seconds)
        from slave.slave import start_slave
        start_slave()


if __name__ == '__main__':
    start()
