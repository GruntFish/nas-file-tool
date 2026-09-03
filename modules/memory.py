# modules/memory.py
import gc
import time
import threading
from flask import jsonify

from core.config import MAX_MEMORY_PERCENT, AUTO_CLEANUP_INTERVAL

def register(app):
    """注册内存管理路由"""

    # ===== 获取内存信息 =====
    def get_memory_info():
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':')
                        meminfo[key] = int(parts[1])
                total_mb = meminfo.get('MemTotal', 0) / 1024
                available_mb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0)) / 1024
                used_mb = total_mb - available_mb
                percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
                return {
                    'total_mb': round(total_mb, 2),
                    'available_mb': round(available_mb, 2),
                    'used_mb': round(used_mb, 2),
                    'percent': round(percent, 2)
                }
        except:
            return None

    def get_process_memory_mb():
        try:
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1]) / 1024
        except:
            pass
        return 0

    def memory_cleanup():
        gc.collect()

    def check_memory_limit():
        mem = get_memory_info()
        if not mem:
            return {'exceeded': False}
        process_mb = get_process_memory_mb()
        percent = (process_mb / mem['total_mb']) * 100 if mem['total_mb'] > 0 else 0
        if percent > MAX_MEMORY_PERCENT:
            gc.collect()
            process_mb2 = get_process_memory_mb()
            percent2 = (process_mb2 / mem['total_mb']) * 100 if mem['total_mb'] > 0 else 0
            if percent2 > MAX_MEMORY_PERCENT:
                return {
                    'exceeded': True,
                    'current_percent': round(percent2, 2),
                    'memory_mb': round(process_mb2, 2)
                }
        return {'exceeded': False}

    # ===== 导出函数供其他模块使用 =====
    app.memory = {
        'get_info': get_memory_info,
        'get_process': get_process_memory_mb,
        'cleanup': memory_cleanup,
        'check_limit': check_memory_limit
    }

    # ===== 定时自动清理 =====
    def auto_cleanup():
        while True:
            time.sleep(AUTO_CLEANUP_INTERVAL)
            memory_cleanup()

    cleanup_thread = threading.Thread(target=auto_cleanup, daemon=True)
    cleanup_thread.start()

    # ===== API 路由 =====
    @app.route('/api/memory', methods=['GET'])
    def memory_status():
        mem = get_memory_info()
        process_mb = get_process_memory_mb()
        percent = (process_mb / mem['total_mb']) * 100 if mem and mem['total_mb'] > 0 else 0
        return jsonify({
            'system': mem,
            'process_memory_mb': round(process_mb, 2),
            'process_percent': round(percent, 2)
        })

    @app.route('/api/cleanup', methods=['POST'])
    def cleanup():
        memory_cleanup()
        mem = get_memory_info()
        process_mb = get_process_memory_mb()
        return jsonify({
            'message': '内存已清理',
            'process_memory_mb': round(process_mb, 2)
        })
