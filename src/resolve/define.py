from enum import Enum


class ResolveStep(Enum):
    FEATURE = 'feature'
    CALIBRATE = 'calibrate'
    SFM = 'sfm'
    DEPTH = 'depth'
    MESH = 'mesh'


class ResolveEvent(Enum):
    COMPLETE = 0
    FAIL = 1
    LOG_INFO = 2
    LOG_STDOUT = 3
    LOG_WARNING = 4
    PROGRESS = 5
