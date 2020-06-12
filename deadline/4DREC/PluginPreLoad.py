import sys


def __main__():
    resolve_path = '//storage03/Cache/4DREC/resolve/'

    if resolve_path not in sys.path:
        sys.path.insert(1, resolve_path)
