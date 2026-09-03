# core/config.py
import os
from pathlib import Path

# ===== NAS 性能优化配置 =====
MAX_HISTORY = 50
MAX_FILES_PER_OPERATION = 100
MAX_DEDUP_FILES = 3000
BATCH_SIZE = 20
TREE_MAX_DEPTH = 3
SLEEP_BETWEEN_BATCH = 0.05
SAMPLE_POINTS = 100
SAMPLE_SIZE = 4096

WORK_DIR = '/data'

# ===== 内存阈值 =====
MAX_MEMORY_PERCENT = 20
AUTO_CLEANUP_INTERVAL = 1800

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
