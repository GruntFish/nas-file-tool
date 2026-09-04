# core/logger.py
import logging
import sys
from core.config import LOG_LEVEL

# ===== 日志格式 =====
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logger(name='nas-tool'):
    """设置日志记录器（仅控制台输出）"""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # ===== 仅控制台输出，不写文件 =====
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name):
    """获取日志记录器"""
    return setup_logger(name)
