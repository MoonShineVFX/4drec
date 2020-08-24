from loguru import logger
import sys


def get_prefix_log(prefix):
    """取得綁訂前贅字詞的 logger"""
    return logger.bind(prefix=prefix)


# log 格式
log_format = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> '
    '|<level>{level}</level>| '
    '<cyan>{name}:{function}:{line}</cyan> - '
    '<level>{extra[prefix]}{message}</level> '
    '({process.name})'
)


# log 總設定
logger.configure(
    handlers=[
        {'sink': sys.stderr, 'format': log_format, 'colorize': True, 'enqueue': True}
    ],
    extra={'prefix': ''}
)
