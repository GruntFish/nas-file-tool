# core/undo.py
from collections import deque
from pathlib import Path
import shutil
import os
from datetime import datetime
from core.logger import get_logger
from core.config import MAX_HISTORY

logger = get_logger(__name__)

# ===== 全局历史记录 =====
_undo_history = deque(maxlen=MAX_HISTORY)


class UndoAction:
    RENAME = 'rename'
    DELETE = 'delete'
    MOVE = 'move'
    COPY = 'copy'


def add_undo_record(action, old_path, new_path=None, old_name=None, new_name=None, extra=None):
    """添加撤销记录"""
    record = {
        'id': f'undo_{int(datetime.now().timestamp() * 1000)}',
        'action': action,
        'old_path': old_path,
        'new_path': new_path,
        'old_name': old_name,
        'new_name': new_name,
        'extra': extra or {},
        'timestamp': datetime.now().isoformat()
    }
    _undo_history.append(record)
    logger.info(f'添加撤销记录: {action} - {old_path} -> {new_path}')
    return record


def get_undo_history(limit=10):
    """获取撤销历史"""
    return list(_undo_history)[-limit:]


def clear_undo_history():
    """清空撤销历史"""
    _undo_history.clear()
    logger.info('撤销历史已清空')


def undo_last():
    """撤销最后一个操作"""
    if not _undo_history:
        return {'error': '没有可撤销的操作'}, 400
    
    record = _undo_history.pop()
    action = record.get('action')
    old_path = record.get('old_path')
    new_path = record.get('new_path')
    
    try:
        if action == UndoAction.RENAME:
            # 撤销重命名：将新文件名改回旧文件名
            if new_path and Path(new_path).exists() and not Path(old_path).exists():
                Path(new_path).rename(old_path)
                logger.info(f'撤销重命名: {new_path} -> {old_path}')
                return {'message': f'已撤销重命名: {record.get("old_name")}', 'success': True}
            else:
                return {'error': '文件已不存在，无法撤销', 'success': False}, 400
        
        elif action == UndoAction.DELETE:
            # 撤销删除：恢复文件（如果有备份）
            backup_path = record.get('extra', {}).get('backup_path')
            if backup_path and Path(backup_path).exists():
                Path(backup_path).rename(old_path)
                logger.info(f'撤销删除: {backup_path} -> {old_path}')
                return {'message': f'已撤销删除: {record.get("old_name")}', 'success': True}
            else:
                return {'error': '没有备份文件，无法恢复', 'success': False}, 400
        
        elif action == UndoAction.MOVE:
            # 撤销移动：将文件移回原位置
            if new_path and Path(new_path).exists() and not Path(old_path).exists():
                Path(new_path).rename(old_path)
                logger.info(f'撤销移动: {new_path} -> {old_path}')
                return {'message': f'已撤销移动: {record.get("old_name")}', 'success': True}
            else:
                return {'error': '文件已不存在，无法撤销', 'success': False}, 400
        
        else:
            return {'error': f'不支持的撤销操作: {action}', 'success': False}, 400
            
    except Exception as e:
        logger.error(f'撤销操作失败: {e}', exc_info=True)
        return {'error': str(e), 'success': False}, 500


def register_undo_routes(app):
    """注册撤销路由"""
    
    @app.route('/api/undo', methods=['POST'])
    def undo():
        result, status_code = undo_last()
        return jsonify(result), status_code
    
    @app.route('/api/undo/history', methods=['GET'])
    def undo_history():
        limit = request.args.get('limit', 10, type=int)
        return jsonify({'history': get_undo_history(limit)})
    
    @app.route('/api/undo/clear', methods=['POST'])
    def undo_clear():
        clear_undo_history()
        return jsonify({'message': '撤销历史已清空'})
    
    logger.info('撤销路由已注册')
