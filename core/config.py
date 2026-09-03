# core/config.py
import os
from pathlib import Path

# ===== 环境变量支持 =====
def get_env(key, default):
    """获取环境变量，支持类型转换"""
    value = os.environ.get(key)
    if value is None:
        return default
    
    # 布尔类型
    if isinstance(default, bool):
        return value.lower() in ('true', '1', 'yes', 'on')
    
    # 整数类型
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    
    # 浮点数类型
    if isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    
    return value


# ===== NAS 性能优化配置 =====
MAX_HISTORY = get_env('MAX_HISTORY', 50)
MAX_FILES_PER_OPERATION = get_env('MAX_FILES_PER_OPERATION', 0)  # 0 = 不限制
MAX_DEDUP_FILES = get_env('MAX_DEDUP_FILES', 3000)
BATCH_SIZE = get_env('BATCH_SIZE', 20)
TREE_MAX_DEPTH = get_env('TREE_MAX_DEPTH', 3)
SLEEP_BETWEEN_BATCH = get_env('SLEEP_BETWEEN_BATCH', 0.05)
SAMPLE_POINTS = get_env('SAMPLE_POINTS', 100)
SAMPLE_SIZE = get_env('SAMPLE_SIZE', 4096)

# ===== 工作目录 =====
WORK_DIR = get_env('WORK_DIR', '/data')

# ===== 内存阈值 =====
MAX_MEMORY_PERCENT = get_env('MAX_MEMORY_PERCENT', 20)
AUTO_CLEANUP_INTERVAL = get_env('AUTO_CLEANUP_INTERVAL', 1800)

# ===== 日志配置 =====
LOG_LEVEL = get_env('LOG_LEVEL', 'INFO')
LOG_FILE = get_env('LOG_FILE', '/data/logs/nas-tool.log')

# ===== 异步任务配置 =====
ASYNC_WORKER_COUNT = get_env('ASYNC_WORKER_COUNT', 2)

# ===== 文件类型映射 =====
FILE_TYPES = {
    '图片': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif', '.heic'},
    '视频': {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.mts'},
    '音频': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.ape'},
    '文档': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.md', '.odt', '.ods'},
    '压缩包': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso', '.tgz'},
    '代码': {'.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.sh', '.bat', '.go', '.rs', '.c', '.cpp'},
    '安装包': {'.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.apk', '.appimage'},
    '数据库': {'.db', '.sqlite', '.sql', '.mdb', '.accdb'},
}


def get_file_type(ext):
    """根据扩展名获取文件类型分类"""
    ext = ext.lower()
    for type_name, exts in FILE_TYPES.items():
        if ext in exts:
            return type_name
    return '其他'
