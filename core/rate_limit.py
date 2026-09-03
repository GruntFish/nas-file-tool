# core/rate_limit.py
from functools import wraps
import time
import threading
from flask import jsonify, request
from core.logger import get_logger

logger = get_logger(__name__)

# 限流配置
RATE_LIMITS = {
    'default': {'max_calls': 30, 'time_window': 60},  # 每分钟30次
    'delete': {'max_calls': 10, 'time_window': 60},   # 每分钟10次
    'move_copy': {'max_calls': 20, 'time_window': 60}, # 每分钟20次
}

# 存储调用记录
_call_records = {}
_lock = threading.Lock()


def get_client_identifier():
    """获取客户端标识"""
    # 优先使用 X-Forwarded-For
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    # 其次使用 Remote-Addr
    return request.remote_addr or 'unknown'


def rate_limit(limit_key='default'):
    """限流装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RATE_LIMITS.get(limit_key, RATE_LIMITS['default'])
            max_calls = config['max_calls']
            time_window = config['time_window']
            
            # 获取客户端标识
            client_id = get_client_identifier()
            key = f'{func.__name__}:{client_id}'
            
            with _lock:
                now = time.time()
                if key not in _call_records:
                    _call_records[key] = []
                
                # 清理过期记录
                _call_records[key] = [t for t in _call_records[key] if now - t < time_window]
                
                if len(_call_records[key]) >= max_calls:
                    logger.warning(f'限流触发: {key} (已调用 {len(_call_records[key])} 次)')
                    return jsonify({
                        'error': f'请求过于频繁，请稍后再试 (限制: {max_calls}次/{time_window}秒)'
                    }), 429
                
                _call_records[key].append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_rate_limit_status():
    """获取限流状态（用于调试）"""
    with _lock:
        now = time.time()
        status = {}
        for key, records in _call_records.items():
            records = [t for t in records if now - t < 60]
            status[key] = len(records)
        return status
