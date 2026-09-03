# modules/delete.py
from flask import jsonify, request
from pathlib import Path
import shutil
import time

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE, SLEEP_BETWEEN_BATCH

def register(app):
    """注册删除路由"""

    @app.route('/api/delete', methods=['POST'])
    def delete_files():
        data = request.json
        files = data.get('files', [])
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要删除的文件'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多删除 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        logs = []
        deleted = 0

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(SLEEP_BETWEEN_BATCH)

            target = Path(work_dir) / file_path_str
            if target.exists():
                try:
                    if target.is_file():
                        target.unlink()
                        logs.append({'text': f'🗑️ 删除文件: {target.name}', 'type': 'success'})
                        deleted += 1
                    elif target.is_dir():
                        shutil.rmtree(target)
                        logs.append({'text': f'🗑️ 删除目录: {target.name}', 'type': 'success'})
                        deleted += 1
                except Exception as e:
                    logs.append({'text': f'❌ 删除失败: {target.name} - {str(e)}', 'type': 'error'})
            else:
                logs.append({'text': f'⚠️ 不存在: {file_path_str}', 'type': 'warning'})

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({'logs': logs, 'deleted': deleted})
