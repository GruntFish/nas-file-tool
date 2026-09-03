# core/security.py
from pathlib import Path
import os
from core.logger import get_logger

logger = get_logger(__name__)

# 路径黑名单（不允许操作的路径）
PATH_BLACKLIST = [
    '/etc',
    '/bin',
    '/boot',
    '/dev',
    '/lib',
    '/proc',
    '/root',
    '/sbin',
    '/sys',
    '/usr',
    '/var',
]

# 不允许删除的文件扩展名
DELETE_BLACKLIST_EXTENSIONS = [
    '.exe', '.dll', '.so', '.dylib',
    '.sys', '.bin',
]


def is_safe_path(path, base_dir):
    """检查路径是否在 base_dir 内"""
    try:
        resolved = Path(path).resolve()
        base = Path(base_dir).resolve()
        result = str(resolved).startswith(str(base))
        if not result:
            logger.warning(f'路径安全检查失败: {path} 不在 {base_dir} 内')
        return result
    except Exception as e:
        logger.error(f'路径安全检查异常: {e}')
        return False


def is_path_blacklisted(path):
    """检查路径是否在黑名单中"""
    try:
        resolved = str(Path(path).resolve())
        for blacklisted in PATH_BLACKLIST:
            if resolved.startswith(blacklisted):
                logger.warning(f'路径在黑名单中: {resolved}')
                return True
        return False
    except Exception as e:
        logger.error(f'黑名单检查异常: {e}')
        return True  # 安全起见，出错时拒绝访问


def is_safe_delete(file_path):
    """检查文件是否可以删除"""
    try:
        ext = Path(file_path).suffix.lower()
        if ext in DELETE_BLACKLIST_EXTENSIONS:
            logger.warning(f'文件在黑名单中，拒绝删除: {file_path}')
            return False
        return True
    except Exception as e:
        logger.error(f'删除安全检查异常: {e}')
        return False


def sanitize_path(path):
    """清理路径，防止路径穿越"""
    try:
        # 移除 ../ 等危险字符
        parts = Path(path).parts
        safe_parts = []
        for part in parts:
            if part == '..':
                if safe_parts:
                    safe_parts.pop()
            elif part not in ('.', ''):
                safe_parts.append(part)
        return '/' + '/'.join(safe_parts) if safe_parts else '/'
    except Exception:
        return '/'


def validate_files_in_directory(file_paths, base_dir):
    """验证所有文件都在指定目录内"""
    for file_path in file_paths:
        full_path = Path(base_dir) / file_path.lstrip('/')
        if not is_safe_path(full_path, base_dir):
            return False, f'文件路径不安全: {file_path}'
    return True, None
