# modules/delete.py
from flask import jsonify, request
from pathlib import Path
import shutil
import time

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE, SLEEP_BETWEEN_BATCH
from core.decorators import with_memory_cleanup, log_operation, handle_errors
from core.security import is_safe_path, is_safe_delete
from core.logger import get_logger
from core.undo import add_undo_record, UndoAction

logger = get_logger(__name__)


def register(app):
    """注册删除路由"""

    @app.route('/api/delete', methods=['POST'])
    @handle_errors('删除失败')
    @log_operation('删除文件')
    @with_memory_cleanup(app)
    def delete_files():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        files = data.get('files', [])
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要删除的文件'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多删除 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        logs = []
        deleted = 0
        failed = 0

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(SLEEP_BETWEEN_BATCH)

            target = Path(work_dir) / file_path_str.lstrip('/')

            if not is_safe_path(target, work_dir):
                logs.append({'text': f'⚠️ 不安全路径: {file_path_str}', 'type': 'warning'})
                failed += 1
                continue

            if not is_safe_delete(target):
                logs.append({'text': f'⚠️ 文件在保护列表中: {target.name}', 'type': 'warning'})
                failed += 1
                continue

            if target.exists():
                try:
                    backup_path = target.parent / f'.{target.name}.deleted_backup'
                    if target.is_file():
                        shutil.copy2(str(target), str(backup_path))
                        target.unlink()
                        logs.append({'text': f'🗑️ 删除文件: {target.name}', 'type': 'success'})
                        deleted += 1
                    elif target.is_dir():
                        shutil.rmtree(target)
                        logs.append({'text': f'🗑️ 删除目录: {target.name}', 'type': 'success'})
                        deleted += 1
                    add_undo_record(
                        UndoAction.DELETE,
                        str(target),
                        None,
                        target.name,
                        None,
                        {'backup_path': str(backup_path)}
                    )
                except Exception as e:
                    failed += 1
                    logger.error(f'删除失败: {target.name} - {e}')
                    logs.append({'text': f'❌ 删除失败: {target.name} - {str(e)}', 'type': 'error'})
            else:
                logs.append({'text': f'⚠️ 不存在: {file_path_str}', 'type': 'warning'})

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        logger.info(f'删除完成: 成功 {deleted} 个，失败 {failed} 个')
        return jsonify({'logs': logs, 'deleted': deleted, 'failed': failed})
