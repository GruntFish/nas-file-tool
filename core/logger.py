# core/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

# 日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日志级别
LOG_LEVEL = logging.INFO

# 日志文件路径
LOG_DIR = '/data/logs'
LOG_FILE = os.path.join(LOG_DIR, 'nas-tool.log')


def setup_logger(name='nas-tool', log_file=None):
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # 如果已经有 handler，不再重复添加
    if logger.handlers:
        return logger
    
    # 创建日志目录
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件 handler（带轮转）
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(LOG_LEVEL)
            file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f'无法创建日志文件: {e}')
    
    return logger


def get_logger(name):
    """获取日志记录器（便捷函数）"""
    return setup_logger(name, LOG_FILE)
