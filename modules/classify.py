# modules/classify.py
from flask import jsonify, request
from pathlib import Path
import shutil
import time
from datetime import datetime

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE, FILE_TYPES

def register(app):
    """注册分类整理路由"""

    def get_file_type(ext):
        ext = ext.lower()
        for type_name, exts in FILE_TYPES.items():
            if ext in exts:
                return type_name
        return '其他'

    @app.route('/api/classify', methods=['POST'])
    def classify():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        files = data.get('files', [])
        method = data.get('method', 'type')
        target_base = data.get('target_base', '分类整理')
        copy_mode = data.get('copy_mode', False)
        dry_run = data.get('dry_run', True)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要分类的文件'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        # ===== 【修复】使用第一个文件的父目录作为基准 =====
        # 而不是直接使用 WORK_DIR
        first_file = Path(work_dir) / files[0].lstrip('/')
        base_dir = first_file.parent if first_file.parent != Path(work_dir) else Path(work_dir)
        # 如果所有文件都在同一目录下，使用该目录
        # 如果文件分散在不同目录，使用它们共同的父目录
        common_parent = None
        for file_path_str in files:
            p = Path(work_dir) / file_path_str.lstrip('/')
            if common_parent is None:
                common_parent = p.parent
            else:
                # 找共同父目录
                p_parent = p.parent
                while p_parent != common_parent and p_parent != p_parent.parent:
                    if str(p_parent).startswith(str(common_parent)):
                        break
                    common_parent = common_parent.parent
                if common_parent == Path(work_dir):
                    break
        
        # 如果找不到共同父目录，使用第一个文件的父目录
        if common_parent is None or common_parent == Path(work_dir):
            common_parent = first_file.parent
        
        target_path = common_parent / target_base
        
        results = []
        stats = {'processed': 0, 'moved': 0, 'copied': 0, 'skipped': 0, 'errors': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str.lstrip('/')
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.is_dir():
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '是目录'})
                continue

            # 确定分类目标
            if method == 'type':
                ext = src.suffix
                category = get_file_type(ext)
                dest_dir = target_path / category
            elif method == 'date':
                mtime = datetime.fromtimestamp(src.stat().st_mtime)
                category = mtime.strftime('%Y-%m')
                dest_dir = target_path / category
            elif method == 'size':
                size = src.stat().st_size
                if size < 1024 * 1024:
                    category = '小于1MB'
                elif size < 10 * 1024 * 1024:
                    category = '1-10MB'
                elif size < 100 * 1024 * 1024:
                    category = '10-100MB'
                else:
                    category = '大于100MB'
                dest_dir = target_path / category
            else:
                return jsonify({'error': f'未知分类方式: {method}'}), 400

            dest = dest_dir / src.name

            # 处理重名
            if dest.exists():
                stem = src.stem
                ext = src.suffix
                counter = 1
                while True:
                    new_name = f'{stem}_{counter}{ext}'
                    new_dest = dest_dir / new_name
                    if not new_dest.exists():
                        dest = new_dest
                        break
                    counter += 1

            if dry_run:
                stats['processed'] += 1
                results.append({
                    'file': src.name,
                    'from': str(src.relative_to(work_dir)),
                    'to': str(dest.relative_to(work_dir)),
                    'category': category,
                    'status': 'preview'
                })
            else:
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    if copy_mode:
                        shutil.copy2(str(src), str(dest))
                        stats['copied'] += 1
                    else:
                        shutil.move(str(src), str(dest))
                        stats['moved'] += 1
                    stats['processed'] += 1
                    results.append({
                        'file': src.name,
                        'from': str(src.relative_to(work_dir)),
                        'to': str(dest.relative_to(work_dir)),
                        'category': category,
                        'status': 'success'
                    })
                except Exception as e:
                    stats['errors'] += 1
                    results.append({
                        'file': src.name,
                        'status': 'error',
                        'reason': str(e)
                    })

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'method': method,
            'target_base': target_base,
            'base_dir': str(common_parent.relative_to(work_dir)) if common_parent != Path(work_dir) else '/'
        })
