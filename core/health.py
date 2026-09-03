# core/health.py
from flask import jsonify
import time
import os
import psutil
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

_start_time = time.time()


def get_system_status():
    """获取系统状态"""
    try:
        # 内存信息
        mem = psutil.virtual_memory()
        # 磁盘信息
        disk = psutil.disk_usage('/')
        # CPU 信息
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        return {
            'status': 'ok',
            'uptime': time.time() - _start_time,
            'timestamp': datetime.now().isoformat(),
            'system': {
                'memory': {
                    'total_mb': round(mem.total / 1024 / 1024, 2),
                    'available_mb': round(mem.available / 1024 / 1024, 2),
                    'used_mb': round(mem.used / 1024 / 1024, 2),
                    'percent': mem.percent
                },
                'disk': {
                    'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                    'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                    'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                    'percent': disk.percent
                },
                'cpu': {
                    'percent': cpu_percent
                },
                'pid': os.getpid()
            }
        }
    except Exception as e:
        logger.error(f'获取系统状态失败: {e}')
        return {
            'status': 'degraded',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def register_health_routes(app):
    """注册健康检查路由"""
    
    @app.route('/health')
    def health():
        """基础健康检查"""
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - _start_time
        })
    
    @app.route('/health/detailed')
    def health_detailed():
        """详细健康检查"""
        status = get_system_status()
        return jsonify(status)
    
    @app.route('/health/ready')
    def health_ready():
        """就绪检查"""
        # 检查数据目录是否可写
        try:
            test_file = '/data/.health_check'
            with open(test_file, 'w') as f:
                f.write('ok')
            os.remove(test_file)
            return jsonify({'status': 'ready'})
        except Exception as e:
            logger.error(f'就绪检查失败: {e}')
            return jsonify({'status': 'not_ready', 'error': str(e)}), 503
    
    logger.info('健康检查路由已注册')
