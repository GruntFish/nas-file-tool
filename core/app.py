# core/app.py
from flask import Flask, send_from_directory
import os

# ===== 【新增】防止重复注册 =====
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
    
    # ===== 【修复】防止重复注册 =====
    if not _registered:
        register_modules(app)
        _registered = True
    
    return app

def register_modules(app):
    from modules import register_all_routes
    register_all_routes(app)
