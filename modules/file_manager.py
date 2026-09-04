# modules/file_manager.py
from flask import jsonify, request
from pathlib import Path
from core.config import WORK_DIR, ROOT_DIRS, TREE_MAX_DEPTH


def register(app):
    """注册文件管理路由"""

    def build_tree(path, depth=0, max_depth=3, visited=None):
        """构建目录树"""
        if visited is None:
            visited = set()
        
        try:
            real_path = str(path.resolve())
            if real_path in visited:
                return []
            visited.add(real_path)
        except:
            return []
        
        if depth > max_depth:
            return []
        
        nodes = []
        try:
            for item in sorted(path.iterdir()):
                if item.is_symlink():
                    continue
                if item.is_dir():
                    # 跳过系统目录
                    if item.name in ['logs', 'lost+found']:
                        continue
                    node = {
                        'name': item.name,
                        'path': str(item),
                        'is_dir': True,
                        'size': 0,
                        'is_root': False,
                        'children': build_tree(item, depth + 1, max_depth, visited.copy())
                    }
                    nodes.append(node)
        except PermissionError:
            pass
        return nodes

    @app.route('/api/tree', methods=['POST'])
    def get_tree():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        base_path = data.get('path', '/')
        
        # ===== 根目录：返回所有根目录 =====
        if base_path == '/':
            tree = []
            for root_dir in ROOT_DIRS:
                try:
                    root_path = Path(root_dir).resolve()
                    if root_path.exists() and root_path.is_dir():
                        node = {
                            'name': root_path.name,
                            'path': str(root_path),
                            'is_dir': True,
                            'size': 0,
                            'is_root': True,
                            'children': build_tree(root_path, depth=1, max_depth=TREE_MAX_DEPTH)
                        }
                        tree.append(node)
                except Exception as e:
                    print(f'无法访问根目录 {root_dir}: {e}')
            
            return jsonify({'tree': tree, 'current': '/'})

        # ===== 子目录处理 =====
        target = Path(base_path)
        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        tree = build_tree(target)
        return jsonify({'tree': tree, 'current': base_path})

    @app.route('/api/files', methods=['POST'])
    def get_files():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        base_path = data.get('path', '/')

        # ===== 根目录：显示所有根目录 =====
        if base_path == '/':
            all_files = []
            for root_dir in ROOT_DIRS:
                try:
                    root_path = Path(root_dir).resolve()
                    if root_path.exists() and root_path.is_dir():
                        all_files.append({
                            'name': root_path.name,
                            'path': str(root_path),
                            'is_dir': True,
                            'size': 0,
                            'modified': None,
                            'is_root': True
                        })
                except Exception as e:
                    pass
            return jsonify({'files': all_files, 'current': '/'})

        # ===== 子目录处理 =====
        target = Path(base_path)
        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        files = []
        try:
            for item in target.iterdir():
                if item.is_symlink():
                    continue
                if item.name in ['logs', 'lost+found']:
                    continue
                try:
                    stat = item.stat()
                    files.append({
                        'name': item.name,
                        'path': str(item),
                        'is_dir': item.is_dir(),
                        'size': stat.st_size if item.is_file() else 0,
                        'modified': stat.st_mtime if item.is_file() else None,
                        'is_root': False
                    })
                except:
                    pass
        except PermissionError:
            pass

        return jsonify({'files': files, 'current': base_path})
