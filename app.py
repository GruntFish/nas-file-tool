from flask import Flask, render_template, request, jsonify
import os
import re
import hashlib
import subprocess
import shutil
import gc
import threading
import time
from pathlib import Path
from datetime import datetime
from collections import deque

app = Flask(__name__)

# ===== 内存限制配置 =====
MAX_HISTORY = 100
MAX_LOG_LINES = 200
CACHE_EXPIRE_TIME = 300
AUTO_CLEANUP_INTERVAL = 3600  # 自动清理间隔（秒），默认1小时

# ===== 全局变量 =====
rename_history = deque(maxlen=MAX_HISTORY)
log_cache = deque(maxlen=MAX_LOG_LINES)
file_cache = {}
cache_timestamps = {}
last_cleanup_time = datetime.now()

# ===== 获取内存使用 =====
def get_memory_usage():
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except:
        return 0

# ===== 自动清理函数 =====
def auto_cleanup():
    """自动清理内存（后台线程运行）"""
    global file_cache, cache_timestamps, log_cache, last_cleanup_time
    
    while True:
        try:
            time.sleep(AUTO_CLEANUP_INTERVAL)
            
            # 清理文件缓存
            file_cache.clear()
            cache_timestamps.clear()
            
            # 清理日志缓存
            log_cache.clear()
            
            # 强制垃圾回收
            gc.collect()
            
            last_cleanup_time = datetime.now()
            memory_usage = get_memory_usage()
            
            print(f"[自动清理] 内存已清理，当前使用: {memory_usage}MB, 时间: {last_cleanup_time}")
            
        except Exception as e:
            print(f"[自动清理] 错误: {e}")

# ===== 启动后台清理线程 =====
cleanup_thread = threading.Thread(target=auto_cleanup, daemon=True)
cleanup_thread.start()

# ===== 根路由 =====
@app.route('/')
def index():
    return render_template('index.html')

# ===== 手动清理内存 =====
@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    global file_cache, cache_timestamps, log_cache, last_cleanup_time
    
    file_cache.clear()
    cache_timestamps.clear()
    log_cache.clear()
    gc.collect()
    
    last_cleanup_time = datetime.now()
    memory_usage = get_memory_usage()
    
    return jsonify({
        'message': '内存已清理',
        'memory_mb': memory_usage,
        'history_count': len(rename_history),
        'cache_count': len(file_cache),
        'last_cleanup': last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S')
    })

# ===== 内存状态监控 =====
@app.route('/api/memory', methods=['GET'])
def memory_status():
    """查看内存使用状态"""
    return jsonify({
        'memory_mb': get_memory_usage(),
        'history_count': len(rename_history),
        'cache_count': len(file_cache),
        'max_history': MAX_HISTORY,
        'max_log_lines': MAX_LOG_LINES,
        'cache_expire_time': CACHE_EXPIRE_TIME,
        'auto_cleanup_interval': AUTO_CLEANUP_INTERVAL,
        'last_cleanup_time': last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S') if last_cleanup_time else '从未'
    })

# ===== 获取目录树（带缓存） =====
@app.route('/api/tree', methods=['POST'])
def get_tree():
    data = request.json
    base_path = data.get('path', '/')
    work_dir = '/data'

    if base_path == '/':
        target = Path(work_dir)
    else:
        clean = base_path.lstrip('/')
        target = Path(work_dir) / clean

    if not target.exists():
        return jsonify({'error': f'路径不存在: {target}'}), 404

    cache_key = f"tree_{base_path}"
    if cache_key in file_cache:
        cached_time = cache_timestamps.get(cache_key, 0)
        if (datetime.now().timestamp() - cached_time) < CACHE_EXPIRE_TIME:
            return jsonify({'tree': file_cache[cache_key], 'current': base_path, 'cached': True})

    def build_tree(path, max_depth=5):
        if max_depth <= 0:
            return []
        nodes = []
        try:
            for item in sorted(path.iterdir()):
                if item.is_dir():
                    node = {
                        'name': item.name,
                        'path': str(item.relative_to(work_dir)),
                        'is_dir': True,
                        'size': 0,
                        'children': build_tree(item, max_depth - 1)
                    }
                    nodes.append(node)
        except PermissionError:
            pass
        return nodes

    tree = build_tree(target, max_depth=5)
    
    file_cache[cache_key] = tree
    cache_timestamps[cache_key] = datetime.now().timestamp()
    
    return jsonify({'tree': tree, 'current': base_path, 'cached': False})

# ===== 获取文件列表（带缓存） =====
@app.route('/api/files', methods=['POST'])
def get_files():
    data = request.json
    base_path = data.get('path', '/')
    work_dir = '/data'

    if base_path == '/':
        target = Path(work_dir)
    else:
        clean = base_path.lstrip('/')
        target = Path(work_dir) / clean

    if not target.exists():
        return jsonify({'error': f'路径不存在: {target}'}), 404

    cache_key = f"files_{base_path}"
    if cache_key in file_cache:
        cached_time = cache_timestamps.get(cache_key, 0)
        if (datetime.now().timestamp() - cached_time) < CACHE_EXPIRE_TIME:
            return jsonify({'files': file_cache[cache_key], 'current': base_path, 'cached': True})

    files = []
    try:
        for item in target.iterdir():
            try:
                stat = item.stat()
                files.append({
                    'name': item.name,
                    'path': str(item.relative_to(work_dir)),
                    'is_dir': item.is_dir(),
                    'size': stat.st_size if item.is_file() else 0,
                    'modified': stat.st_mtime if item.is_file() else None,
                })
            except:
                pass
    except PermissionError:
        pass

    file_cache[cache_key] = files
    cache_timestamps[cache_key] = datetime.now().timestamp()

    return jsonify({'files': files, 'current': base_path, 'cached': False})

# ===== 预览重命名 =====
@app.route('/api/preview', methods=['POST'])
def preview():
    data = request.json
    action = data.get('action')
    files = data.get('files', [])
    work_dir = '/data'

    results = []

    for file_path in files:
        old_name = Path(file_path).name
        new_name = old_name

        try:
            new_name = apply_rename_action(old_name, action, data)
        except Exception as e:
            print(f'Error processing {old_name}: {e}')
            new_name = old_name

        if new_name != old_name:
            results.append({
                'old_path': file_path,
                'new_path': str(Path(file_path).parent / new_name),
                'old_name': old_name,
                'new_name': new_name,
            })

    return jsonify({'files': results})

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

# ===== 执行重命名 =====
@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.json
    action = data.get('action')
    files = data.get('files', [])
    work_dir = '/data'

    logs = []
    stats = {'processed': 0, 'message': '成功'}
    history = []

    MAX_FILES_PER_OPERATION = 500
    if len(files) > MAX_FILES_PER_OPERATION:
        return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

    if action in ['number', 'date']:
        all_files = data.get('all_files', [])
        if not all_files:
            all_files = [f['old_path'] for f in files]

        for idx, file_path in enumerate(all_files):
            old_name = Path(file_path).name
            new_name = old_name

            if action == 'number':
                start = int(data.get('start', 1))
                step = int(data.get('step', 1))
                digits = int(data.get('digits', 2))
                position = data.get('position', 'suffix')
                num = str(start + idx * step).zfill(digits)
                name, ext = os.path.splitext(old_name)
                if position == 'prefix':
                    new_name = num + '_' + name + ext
                else:
                    new_name = name + '_' + num + ext

            elif action == 'date':
                date_type = data.get('date_type', 'created')
                date_format = data.get('date_format', 'YYYY-MM-DD')
                date_pos = data.get('date_pos', 'prefix')
                file_path_obj = Path(work_dir) / file_path
                if date_type == 'created':
                    dt = datetime.fromtimestamp(file_path_obj.stat().st_ctime)
                elif date_type == 'modified':
                    dt = datetime.fromtimestamp(file_path_obj.stat().st_mtime)
                else:
                    dt = datetime.now()
                fmt = date_format.replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d')
                date_str = dt.strftime(fmt)
                name, ext = os.path.splitext(old_name)
                if date_pos == 'prefix':
                    new_name = date_str + '_' + name + ext
                else:
                    new_name = name + '_' + date_str + ext

            if new_name != old_name:
                old_path = Path(work_dir) / file_path
                new_path = Path(work_dir) / str(Path(file_path).parent / new_name)
                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)
                    logs.append({'text': f'✏️ {action}: {old_name} → {new_name}', 'type': 'success'})
                    history.append({'old_path': str(old_path), 'new_path': str(new_path), 'old_name': old_name})
                    stats['processed'] += 1

    elif action in ['move', 'copy']:
        target_dir = data.get('target_dir', '')
        overwrite = data.get('overwrite', False)
        if not target_dir:
            return jsonify({'error': '目标目录不能为空'}), 400
        target_path = Path(work_dir) / target_dir.lstrip('/')
        target_path.mkdir(parents=True, exist_ok=True)
        for item in files:
            old_path = Path(work_dir) / item['old_path']
            new_path = target_path / item['old_name']
            if overwrite and new_path.exists():
                new_path.unlink()
            if action == 'move':
                shutil.move(str(old_path), str(new_path))
                logs.append({'text': f'📦 移动: {item["old_name"]} → {target_dir}', 'type': 'success'})
            else:
                shutil.copy2(str(old_path), str(new_path))
                logs.append({'text': f'📋 复制: {item["old_name"]} → {target_dir}', 'type': 'success'})
            stats['processed'] += 1
            history.append({'old_path': str(old_path), 'new_path': str(new_path), 'old_name': item['old_name']})

    elif action in ['replace', 'regex', 'prefix', 'suffix', 'remove', 'removepos',
                    'lowercase', 'uppercase', 'capitalize', 'titlecase', 'camelcase', 'extension']:
        for item in files:
            old_path = Path(work_dir) / item['old_path']
            new_path = Path(work_dir) / item['new_path']
            if old_path.exists() and not new_path.exists():
                old_path.rename(new_path)
                logs.append({'text': f'✏️ 重命名: {item["old_name"]} → {item["new_name"]}', 'type': 'success'})
                history.append({'old_path': str(old_path), 'new_path': str(new_path), 'old_name': item['old_name']})
                stats['processed'] += 1

    else:
        return jsonify({'error': f'未知操作: {action}'}), 400

    for h in history:
        rename_history.append(h)

    if len(log_cache) > MAX_LOG_LINES:
        log_cache.clear()

    gc.collect()

    stats['message'] = f'成功处理 {stats["processed"]} 个文件'
    return jsonify({'logs': logs, 'stats': stats, 'history': history})

# ===== 撤销 =====
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

# ===== 去重 =====
@app.route('/api/dedup', methods=['POST'])
def dedup():
    data = request.json
    method = data.get('method', 'md5')
    action = data.get('action', 'find')
    recursive = data.get('recursive', True)
    base_path = data.get('path', '/')
    work_dir = '/data'

    if base_path == '/':
        target = Path(work_dir)
    else:
        clean = base_path.lstrip('/')
        target = Path(work_dir) / clean

    if not target.exists():
        return jsonify({'error': f'路径不存在: {target}'}), 404

    all_files = []
    if recursive:
        for item in target.rglob('*'):
            if item.is_file():
                all_files.append(item)
    else:
        for item in target.iterdir():
            if item.is_file():
                all_files.append(item)

    groups = {}
    for file_path in all_files:
        try:
            if method == 'md5':
                with open(file_path, 'rb') as f:
                    key = hashlib.md5(f.read()).hexdigest()
            elif method == 'name':
                key = file_path.name
            elif method == 'size':
                key = file_path.stat().st_size
            elif method == 'name_size':
                key = f'{file_path.name}_{file_path.stat().st_size}'
            else:
                key = file_path.name
            if key not in groups:
                groups[key] = []
            groups[key].append(str(file_path))
        except:
            pass

    duplicates = [v for v in groups.values() if len(v) > 1]
    result = {'duplicates': duplicates, 'deleted': 0}

    if action == 'find':
        pass
    elif action == 'delete_first':
        for group in duplicates:
            for f in group[1:]:
                try:
                    Path(f).unlink()
                    result['deleted'] += 1
                except:
                    pass
    elif action == 'delete_last':
        for group in duplicates:
            for f in group[:-1]:
                try:
                    Path(f).unlink()
                    result['deleted'] += 1
                except:
                    pass
    elif action == 'delete_smallest':
        for group in duplicates:
            sizes = [(f, Path(f).stat().st_size) for f in group]
            sizes.sort(key=lambda x: x[1], reverse=True)
            for f, _ in sizes[1:]:
                try:
                    Path(f).unlink()
                    result['deleted'] += 1
                except:
                    pass
    elif action == 'delete_largest':
        for group in duplicates:
            sizes = [(f, Path(f).stat().st_size) for f in group]
            sizes.sort(key=lambda x: x[1])
            for f, _ in sizes[1:]:
                try:
                    Path(f).unlink()
                    result['deleted'] += 1
                except:
                    pass

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
