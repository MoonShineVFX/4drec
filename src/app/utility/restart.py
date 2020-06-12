import os
import sys


def restart():
    os.system(f'start cmd /c {sys.executable} {" ".join(sys.argv)}')
    os._exit(0)
