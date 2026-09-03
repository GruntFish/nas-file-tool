# modules/file_manager.py
from flask import jsonify, request
from pathlib import Path
from core.config import WORK_DIR, TREE_MAX_DEPTH

def register(app):
    """注册文件管理路由"""

    @app.route('/api/tree', methods=['POST'])
    def get_tree():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        base_path = data.get('path', '/')
        work_dir = WORK_DIR

        if base_path == '/':
            target = Path(work_dir)
        else:
            clean = base_path.lstrip('/')
            target = Path(work_dir) / clean

        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        def build_tree(path, depth=0, visited=None):
            if visited is None:
                visited = set()
            
            # 防止软链接循环
            real_path = str(path.resolve())
            if real_path in visited:
                return []
            visited.add(real_path)
            
            if depth > TREE_MAX_DEPTH:
                return []
            
            nodes = []
            try:
                for item in sorted(path.iterdir()):
                    # 跳过软链接指向已访问目录的情况
                    if item.is_symlink():
                        try:
                            resolved = item.resolve()
                            if str(resolved) in visited:
                                continue
                        except:
                            continue
                    
                    if item.is_dir():
                        # ===== 【修复】统一路径格式：以 / 开头 =====
                        rel_path = str(item.relative_to(work_dir))
                        if not rel_path.startswith('/'):
                            rel_path = '/' + rel_path
                        node = {
                            'name': item.name,
                            'path': rel_path,
                            'is_dir': True,
                            'size': 0,
                            'children': build_tree(item, depth + 1, visited.copy())
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
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
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
                # 跳过软链接
                if item.is_symlink():
                    continue
                try:
                    stat = item.stat()
                    # ===== 【修复】统一路径格式：以 / 开头 =====
                    rel_path = str(item.relative_to(work_dir))
                    if not rel_path.startswith('/'):
                        rel_path = '/' + rel_path
                    files.append({
                        'name': item.name,
                        'path': rel_path,
                        'is_dir': item.is_dir(),
                        'size': stat.st_size if item.is_file() else 0,
                        'modified': stat.st_mtime if item.is_file() else None,
                    })
                except:
                    pass
        except PermissionError:
            pass

        return jsonify({'files': files, 'current': base_path})
