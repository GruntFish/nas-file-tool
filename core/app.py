# core/app.py
from flask import Flask, send_from_directory
import os

def create_app():
    """Flask 应用工厂"""
    app = Flask(__name__)
    
    # ===== 根路由 =====
    @app.route('/')
    def index():
        return send_from_directory('templates', 'index.html')
    
    # ===== favicon 路由 =====
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory('.', 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    # ===== 注册所有模块 =====
    register_modules(app)
    
    return app

def register_modules(app):
    """自动注册所有功能模块"""
    from modules import register_all_routes
    register_all_routes(app)
