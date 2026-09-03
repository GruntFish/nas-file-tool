# core/app.py
from flask import Flask, send_from_directory, jsonify
import os
import signal
import sys

# ===== 新增导入 =====
from core.logger import get_logger
from core.health import register_health_routes
from core.undo import register_undo_routes
from core.async_tasks import start_worker, stop_worker

logger = get_logger(__name__)

_registered = False


def create_app():
    global _registered
    app = Flask(__name__, static_folder=None)
    
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    @app.route('/')
    def index():
        return send_from_directory(os.path.join(app_dir, 'templates'), 'index.html')
    
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app_dir, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    @app.route('/modules/<path:filename>')
    def modules(filename):
        return send_from_directory(os.path.join(app_dir, 'templates', 'modules'), filename)
    
    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory(os.path.join(app_dir, 'static'), filename)
    
    # ===== 注册健康检查路由 =====
    register_health_routes(app)
    
    # ===== 注册撤销路由 =====
    register_undo_routes(app)
    
    if not _registered:
        register_modules(app)
        _registered = True
    
    return app


def register_modules(app):
    from modules import register_all_routes
    register_all_routes(app)


# ===== 信号处理 =====
def signal_handler(signum, frame):
    logger.info(f'收到信号 {signum}，正在优雅关闭...')
    stop_worker()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ===== 启动异步工作线程 =====
start_worker()
logger.info('应用初始化完成')
