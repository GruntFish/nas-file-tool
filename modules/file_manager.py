# modules/file_manager.py
from flask import jsonify, request
from pathlib import Path
from core.config import WORK_DIR, TREE_MAX_DEPTH

def register(app):
    """注册文件管理路由"""

    @app.route('/api/tree', methods=['POST'])
    def get_tree():
        data = request.json
        base_path = data.get('path', '/')
        work_dir = WORK_DIR

        if base_path == '/':
            target = Path(work_dir)
        else:
            clean = base_path.lstrip('/')
            target = Path(work_dir) / clean

        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        def build_tree(path, depth=0):
            if depth > TREE_MAX_DEPTH:
                return []
            nodes = []
            try:
                for item in sorted(path.iterdir()):
                    if item.is_dir():
                        node = {
                            'name': item.name,
                            'path': str(item.relative_to(work_dir)),
                            'is_dir': True,
                            'size': 0,
                            'children': build_tree(item, depth + 1)
                        }
                        nodes.append(node)
            except PermissionError:
                pass
            return nodes

        tree = build_tree(target)
        return jsonify({'tree': tree, 'current': base_path})

    @app.route('/api/files', methods=['POST'])
    def get_files():
        data = request.json
        base_path = data.get('path', '/')
        work_dir = WORK_DIR

        if base_path == '/':
            target = Path(work_dir)
        else:
            clean = base_path.lstrip('/')
            target = Path(work_dir) / clean

        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        files = []
        try:
            for item in target.iterdir():
                try:
                    stat = item.stat()
                    files.append({
                        'name': item.name,
                        'path': str(item.relative_to(work_dir)),
                        'is_dir': item.is_dir(),
                        'size': stat.st_size if item.is_file() else 0,
                        'modified': stat.st_mtime if item.is_file() else None,
                    })
                except:
                    pass
        except PermissionError:
            pass

        return jsonify({'files': files, 'current': base_path})
