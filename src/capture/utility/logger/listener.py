import sys
from colorama import init
import ctypes

ctypes.windll.kernel32.SetConsoleTitleW('4DREC MASTER LOG')
sys.stdin.reconfigure(encoding='utf-8')
init()

while True:
    for line in sys.stdin:
        sys.stderr.write(line)
