"""LOG模組

所有系統的 log 管理，如果是 master 的話會用額外的 sink handler
因為主視窗要留給 nubia 的 CLI，log 必須額外開一個 shell 去輸出

"""
from .logger import logger as log
from .logger import get_prefix_log
