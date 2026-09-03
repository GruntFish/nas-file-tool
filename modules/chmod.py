# modules/chmod.py
from flask import jsonify, request
from pathlib import Path
import os
import time

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE

def register(app):
    """注册权限管理路由"""

    @app.route('/api/chmod', methods=['POST'])
    def chmod():
        data = request.json
        files = data.get('files', [])
        mode = data.get('mode', '755')
        recursive = data.get('recursive', False)
        dry_run = data.get('dry_run', True)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要修改权限的文件'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        # 解析权限模式
        try:
            if isinstance(mode, str):
                mode_num = int(mode, 8) if mode.startswith('0') else int(mode, 8)
            else:
                mode_num = mode
        except:
            return jsonify({'error': f'无效的权限模式: {mode}'}), 400

        MODE_NAMES = {
            0o755: '755 (rwxr-xr-x)',
            0o644: '644 (rw-r--r--)',
            0o777: '777 (rwxrwxrwx)',
            0o600: '600 (rw-------)',
            0o700: '700 (rwx------)',
            0o775: '775 (rwxrwxr-x)'
        }

        results = []
        stats = {'processed': 0, 'changed': 0, 'skipped': 0, 'errors': 0}

        all_items = []
        for file_path_str in files:
            target = Path(work_dir) / file_path_str
            if target.exists():
                if target.is_dir() and recursive:
                    for p in target.rglob('*'):
                        if p.exists():
                            all_items.append(str(p.relative_to(work_dir)))
                    all_items.append(file_path_str)
                else:
                    all_items.append(file_path_str)

        all_items = list(set(all_items))

        for i, item_path_str in enumerate(all_items):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            target = Path(work_dir) / item_path_str
            if not target.exists():
                stats['skipped'] += 1
                continue

            current_mode = target.stat().st_mode & 0o777

            if current_mode == mode_num:
                stats['skipped'] += 1
                results.append({
                    'path': item_path_str,
                    'status': 'skip',
                    'reason': '权限已相同',
                    'current': oct(current_mode)
                })
                continue

            if dry_run:
                results.append({
                    'path': item_path_str,
                    'status': 'preview',
                    'current': oct(current_mode),
                    'target': oct(mode_num),
                    'is_dir': target.is_dir()
                })
                stats['processed'] += 1
            else:
                try:
                    os.chmod(target, mode_num)
                    stats['changed'] += 1
                    stats['processed'] += 1
                    results.append({
                        'path': item_path_str,
                        'status': 'success',
                        'current': oct(mode_num),
                        'is_dir': target.is_dir()
                    })
                except Exception as e:
                    stats['errors'] += 1
                    results.append({
                        'path': item_path_str,
                        'status': 'error',
                        'reason': str(e)
                    })

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'mode': mode,
            'mode_name': MODE_NAMES.get(mode_num, oct(mode_num))
        })
