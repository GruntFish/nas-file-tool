# modules/rename.py
from flask import jsonify, request
from pathlib import Path
import os
import re
import time

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE, SLEEP_BETWEEN_BATCH

def register(app):
    """注册重命名路由"""

    def apply_rename_action(old_name, action, data):
        name, ext = os.path.splitext(old_name)
        
        if action == 'replace':
            find_str = data.get('find', '')
            replace_str = data.get('replace', '')
            if find_str:
                if data.get('case_sensitive', False):
                    new_name = old_name.replace(find_str, replace_str)
                else:
                    new_name = old_name.lower().replace(find_str.lower(), replace_str)
            else:
                new_name = old_name
        elif action == 'regex':
            find_str = data.get('find', '')
            replace_str = data.get('replace', '')
            if find_str:
                try:
                    flags = 0 if data.get('case_sensitive', False) else re.IGNORECASE
                    new_name = re.sub(find_str, replace_str, old_name, flags=flags)
                except:
                    new_name = old_name
            else:
                new_name = old_name
        elif action == 'prefix':
            prefix = data.get('replace', '')
            new_name = prefix + old_name
        elif action == 'suffix':
            suffix = data.get('replace', '')
            new_name = name + suffix + ext
        elif action == 'remove':
            remove_str = data.get('find', '')
            if remove_str:
                new_name = old_name.replace(remove_str, '')
        elif action == 'removepos':
            start = data.get('start', 1) - 1
            length = data.get('length', 1)
            from_end = data.get('from_end', False)
            if from_end:
                start = len(name) - start - length + 1
            if start >= 0 and start < len(name):
                new_name = name[:start] + name[start+length:] + ext
            else:
                new_name = old_name
        elif action == 'lowercase':
            new_name = old_name.lower()
        elif action == 'uppercase':
            new_name = old_name.upper()
        elif action == 'capitalize':
            new_name = name.capitalize() + ext
        elif action == 'titlecase':
            new_name = name.title() + ext
        elif action == 'camelcase':
            parts = name.replace('_', ' ').replace('-', ' ').split()
            if parts:
                new_name = parts[0].lower() + ''.join(p.title() for p in parts[1:]) + ext
            else:
                new_name = old_name
        elif action == 'extension':
            ext_action = data.get('ext_action', '')
            ext_value = data.get('ext_value', '')
            if ext_action == 'change':
                new_name = name + '.' + ext_value if ext_value else name
            elif ext_action == 'add':
                new_name = old_name + '.' + ext_value if ext_value else old_name
            elif ext_action == 'remove':
                new_name = name
            elif ext_action == 'replace':
                new_name = name + '.' + ext_value if ext_value else name
        elif action == 'number':
            new_name = old_name
        elif action == 'date':
            new_name = old_name
        elif action == 'move' or action == 'copy':
            new_name = old_name
        else:
            new_name = old_name
        return new_name

    @app.route('/api/preview', methods=['POST'])
    def preview():
        data = request.json
        action = data.get('action')
        files = data.get('files', [])

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多预览 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        results = []
        for file_path in files:
            old_name = Path(file_path).name
            new_name = old_name
            try:
                new_name = apply_rename_action(old_name, action, data)
            except Exception as e:
                new_name = old_name
            if new_name != old_name:
                results.append({
                    'old_path': file_path,
                    'new_path': str(Path(file_path).parent / new_name),
                    'old_name': old_name,
                    'new_name': new_name,
                })

        return jsonify({'files': results})

    @app.route('/api/execute', methods=['POST'])
    def execute():
        data = request.json
        action = data.get('action')
        files = data.get('files', [])
        work_dir = WORK_DIR

        # 检查内存
        if hasattr(app, 'memory'):
            mem_check = app.memory['check_limit']()
            if mem_check['exceeded']:
                return jsonify({'error': '内存使用超过限制，请稍后再试'}), 503

        logs = []
        stats = {'processed': 0, 'message': '成功'}
        history = []

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        try:
            for i, item in enumerate(files):
                if i % BATCH_SIZE == 0:
                    if hasattr(app, 'memory'):
                        app.memory['cleanup']()
                    time.sleep(SLEEP_BETWEEN_BATCH)
                
                old_path = Path(work_dir) / item['old_path']
                new_path = Path(work_dir) / item['new_path']
                
                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)
                    logs.append({
                        'text': f'✏️ 重命名: {item["old_name"]} → {item["new_name"]}',
                        'type': 'success'
                    })
                    history.append({
                        'old_path': str(old_path),
                        'new_path': str(new_path),
                        'old_name': item['old_name']
                    })
                    stats['processed'] += 1

            if hasattr(app, 'memory'):
                app.memory['cleanup']()

            stats['message'] = f'成功处理 {stats["processed"]} 个文件'
            return jsonify({'logs': logs, 'stats': stats, 'history': history})

        except Exception as e:
            import traceback
            if hasattr(app, 'memory'):
                app.memory['cleanup']()
            return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
