# core/decorators.py
from functools import wraps
from flask import jsonify
import time
import threading
from core.logger import get_logger

logger = get_logger(__name__)

# ===== 文件操作锁 =====
_file_locks = {}
_lock = threading.Lock()


def get_file_lock(path):
    """获取文件路径对应的锁"""
    with _lock:
        if path not in _file_locks:
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


def with_memory_cleanup(app):
    """内存清理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            finally:
                if hasattr(app, 'memory'):
                    try:
                        app.memory['cleanup']()
                    except Exception as e:
                        logger.warning(f'内存清理失败: {e}')
        return wrapper
    return decorator


def file_operation_lock(file_path):
    """文件操作锁装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock = get_file_lock(file_path)
            with lock:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def log_operation(operation_name):
    """操作日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f'开始操作: {operation_name}')
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f'操作完成: {operation_name} (耗时: {elapsed:.2f}s)')
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f'操作失败: {operation_name} - {str(e)} (耗时: {elapsed:.2f}s)')
                raise
        return wrapper
    return decorator


def handle_errors(default_message='操作失败'):
    """统一错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                logger.warning(f'参数错误: {e}')
                return jsonify({'error': str(e)}), 400
            except PermissionError as e:
                logger.warning(f'权限错误: {e}')
                return jsonify({'error': f'权限不足: {str(e)}'}), 403
            except FileNotFoundError as e:
                logger.warning(f'文件不存在: {e}')
                return jsonify({'error': f'文件不存在: {str(e)}'}), 404
            except Exception as e:
                logger.error(f'内部错误: {e}', exc_info=True)
                return jsonify({'error': f'{default_message}: {str(e)}'}), 500
        return wrapper
    return decorator


def rate_limit(max_calls=10, time_window=60):
    """简单的限流装饰器（内存存储）"""
    _call_records = {}
    _lock = threading.Lock()
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取调用者标识（IP 或 session）
            # 这里简化处理，使用函数名
            key = func.__name__
            
            with _lock:
                now = time.time()
                if key not in _call_records:
                    _call_records[key] = []
                
                # 清理过期记录
                _call_records[key] = [t for t in _call_records[key] if now - t < time_window]
                
                if len(_call_records[key]) >= max_calls:
                    return jsonify({'error': f'请求过于频繁，请稍后再试'}), 429
                
                _call_records[key].append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
