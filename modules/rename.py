# modules/rename.py
from flask import jsonify, request
from pathlib import Path
import os
import re
import time
from datetime import datetime

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE, SLEEP_BETWEEN_BATCH
from core.decorators import with_memory_cleanup, log_operation, handle_errors
from core.logger import get_logger

logger = get_logger(__name__)


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
            else:
                new_name = old_name
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
            else:
                new_name = old_name
        elif action == 'number':
            new_name = old_name
        elif action == 'date':
            new_name = old_name
        elif action == 'move' or action == 'copy':
            new_name = old_name
        else:
            new_name = old_name
        return new_name

    def apply_numbering(old_name, index, data):
        name, ext = os.path.splitext(old_name)
        start = data.get('start', 1)
        step = data.get('step', 1)
        digits = data.get('digits', 2)
        position = data.get('position', 'suffix')

        num = start + (index - 1) * step
        num_str = str(num).zfill(digits)

        if position == 'prefix':
            return num_str + '_' + old_name
        else:
            return name + '_' + num_str + ext

    def apply_date(old_name, file_path, data):
        name, ext = os.path.splitext(old_name)
        date_type = data.get('date_type', 'modified')
        date_format = data.get('date_format', 'YYYY-MM-DD')
        position = data.get('date_pos', 'prefix')

        try:
            if date_type == 'modified':
                timestamp = os.path.getmtime(file_path)
            elif date_type == 'created':
                timestamp = os.path.getctime(file_path)
            else:
                timestamp = time.time()
        except:
            timestamp = time.time()

        dt = datetime.fromtimestamp(timestamp)

        fmt_map = {
            'YYYY-MM-DD': '%Y-%m-%d',
            'YYYYMMDD': '%Y%m%d',
            'YYMMDD': '%y%m%d'
        }
        fmt = fmt_map.get(date_format, '%Y-%m-%d')
        date_str = dt.strftime(fmt)

        if position == 'prefix':
            return date_str + '_' + old_name
        else:
            return name + '_' + date_str + ext

    # ===== 【修复】所有路由使用传入的 app =====

    @app.route('/api/preview', methods=['POST'])
    def preview():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        action = data.get('action')
        files = data.get('files', [])

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多预览 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        results = []

        if action == 'number':
            target_files = [f for f in files if Path(f).is_file()]
            for idx, file_path in enumerate(target_files, 1):
                old_name = Path(file_path).name
                new_name = apply_numbering(old_name, idx, data)
                if new_name != old_name:
                    results.append({
                        'old_path': file_path,
                        'new_path': str(Path(file_path).parent / new_name),
                        'old_name': old_name,
                        'new_name': new_name,
                    })
            return jsonify({'files': results})

        if action == 'date':
            target_files = [f for f in files if Path(f).is_file()]
            for file_path in target_files:
                old_name = Path(file_path).name
                new_name = apply_date(old_name, file_path, data)
                if new_name != old_name:
                    results.append({
                        'old_path': file_path,
                        'new_path': str(Path(file_path).parent / new_name),
                        'old_name': old_name,
                        'new_name': new_name,
                    })
            return jsonify({'files': results})

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
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        action = data.get('action')
        files = data.get('files', [])
        work_dir = WORK_DIR

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

                old_path = Path(work_dir) / item['old_path'].lstrip('/')
                new_path = Path(work_dir) / item['new_path'].lstrip('/')

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
                else:
                    if not old_path.exists():
                        logs.append({
                            'text': f'⚠️ 文件不存在: {item["old_name"]}',
                            'type': 'warning'
                        })
                    elif new_path.exists():
                        logs.append({
                            'text': f'⚠️ 目标文件已存在: {item["new_name"]}',
                            'type': 'warning'
                        })

            if hasattr(app, 'memory'):
                app.memory['cleanup']()

            stats['message'] = f'成功处理 {stats["processed"]} 个文件'

            if stats['processed'] == 0:
                return jsonify({
                    'logs': logs if logs else [{'text': '没有文件被重命名，请检查文件是否存在', 'type': 'warning'}],
                    'stats': stats,
                    'history': history,
                    'warning': '没有文件被处理'
                })

            return jsonify({'logs': logs, 'stats': stats, 'history': history})

        except Exception as e:
            import traceback
            logger.error(f'重命名异常: {traceback.format_exc()}')
            if hasattr(app, 'memory'):
                app.memory['cleanup']()
            return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
