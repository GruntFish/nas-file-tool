# modules/undo.py
from flask import jsonify, request
from pathlib import Path
from collections import deque

from core.config import MAX_HISTORY

# ===== 全局历史记录 =====
rename_history = deque(maxlen=MAX_HISTORY)

def register(app):
    """注册撤销路由"""

    @app.route('/api/undo', methods=['POST'])
    def undo():
        global rename_history
        if not rename_history:
            return jsonify({'error': '没有可撤销的操作'}), 400
        
        last = rename_history.pop()
        try:
            old_path = Path(last['old_path'])
            new_path = Path(last['new_path'])
            if new_path.exists() and not old_path.exists():
                new_path.rename(old_path)
                return jsonify({'message': f'已撤销: {last["old_name"]}'})
            else:
                return jsonify({'error': '文件已不存在，无法撤销'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # 导出 history 供其他模块使用
    app.undo_history = rename_history
