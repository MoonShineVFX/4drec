import os
import sys


def restart():
    os.system(f'start cmd /c {sys.executable} {" ".join(sys.argv)} 5')
    os._exit(0)
