from flask import Flask, render_template, request, jsonify, send_from_directory
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

# ===== NAS 性能优化配置 =====
MAX_HISTORY = 50
MAX_FILES_PER_OPERATION = 100
MAX_DEDUP_FILES = 3000
BATCH_SIZE = 20
TREE_MAX_DEPTH = 3
SLEEP_BETWEEN_BATCH = 0.05

# ===== 获取内存使用 =====
def get_memory_info():
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    meminfo[key] = int(parts[1])
            total_mb = meminfo.get('MemTotal', 0) / 1024
            available_mb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0)) / 1024
            used_mb = total_mb - available_mb
            percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
            return {
                'total_mb': round(total_mb, 2),
                'available_mb': round(available_mb, 2),
                'used_mb': round(used_mb, 2),
                'percent': round(percent, 2)
            }
    except:
        return None

def get_process_memory_mb():
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) / 1024
    except:
        pass
    return 0

def check_memory_limit():
    mem = get_memory_info()
    if not mem:
        return {'exceeded': False}
    process_mb = get_process_memory_mb()
    percent = (process_mb / mem['total_mb']) * 100 if mem['total_mb'] > 0 else 0
    if percent > 20:
        gc.collect()
        process_mb2 = get_process_memory_mb()
        percent2 = (process_mb2 / mem['total_mb']) * 100 if mem['total_mb'] > 0 else 0
        if percent2 > 20:
            return {
                'exceeded': True,
                'current_percent': round(percent2, 2),
                'memory_mb': round(process_mb2, 2)
            }
    return {'exceeded': False}

def memory_cleanup():
    gc.collect()

# ===== 全局变量 =====
rename_history = deque(maxlen=MAX_HISTORY)

# ===== 定时自动清理（30分钟） =====
def auto_cleanup():
    while True:
        time.sleep(1800)
        memory_cleanup()

cleanup_thread = threading.Thread(target=auto_cleanup, daemon=True)
cleanup_thread.start()

# ===== 多点采样签名（动态采样） =====
def get_file_signature(file_path):
    """
    动态采样：小文件全文MD5，大文件多点采样
    - < 1MB：全文 MD5（100%准确）
    - 1-100MB：200点 × 4KB = 800KB
    - > 100MB：500点 × 4KB = 2MB
    """
    stat = file_path.stat()
    size = stat.st_size
    sample_size = 4096

    # 文件太小，直接全文 MD5
    if size < 1024 * 1024:
        try:
            with open(file_path, 'rb') as f:
                return f'{file_path.name}_{size}_' + hashlib.md5(f.read()).hexdigest()
        except:
            return f'{file_path.name}_{size}_0'

    # 根据文件大小决定采样点数
    if size < 100 * 1024 * 1024:
        points = 200
    else:
        points = 500

    signature = f'{file_path.name}_{size}_'

    try:
        with open(file_path, 'rb') as f:
            step = (size - sample_size) / (points - 1) if points > 1 else 0
            combined = b''
            for i in range(points):
                pos = int(i * step)
                f.seek(pos)
                combined += f.read(sample_size)
            signature += hashlib.md5(combined).hexdigest()
    except:
        signature += '0'

    return signature

@app.route('/')
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# ===== 获取目录树 =====
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

    def build_tree(path, depth=0):
        if depth > TREE_MAX_DEPTH:
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
                        'children': build_tree(item, depth + 1)
                    }
                    nodes.append(node)
        except PermissionError:
            pass
        return nodes

    tree = build_tree(target)
    return jsonify({'tree': tree, 'current': base_path})

# ===== 获取文件列表 =====
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

    return jsonify({'files': files, 'current': base_path})

# ===== 预览重命名 =====
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

# ===== 执行操作 =====
@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.json
    action = data.get('action')
    files = data.get('files', [])
    work_dir = '/data'

    mem_check = check_memory_limit()
    if mem_check['exceeded']:
        return jsonify({
            'error': f'内存使用超过限制，请稍后再试',
            'memory_mb': mem_check['memory_mb']
        }), 503

    logs = []
    stats = {'processed': 0, 'message': '成功'}
    history = []

    if len(files) > MAX_FILES_PER_OPERATION:
        return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

    try:
        if action in ['number', 'date']:
            all_files = data.get('all_files', [])
            if not all_files:
                all_files = [f['old_path'] for f in files]

            for idx, file_path in enumerate(all_files):
                if idx % BATCH_SIZE == 0:
                    memory_cleanup()
                    time.sleep(SLEEP_BETWEEN_BATCH)
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
            filters = data.get('filters', {})

            if not target_dir:
                return jsonify({'error': '目标目录不能为空'}), 400

            target_path = Path(work_dir) / target_dir.lstrip('/')
            if not target_path.exists():
                try:
                    target_path.mkdir(parents=True, exist_ok=True)
                    logs.append({'text': f'📁 创建目标目录: {target_dir}', 'type': 'info'})
                except Exception as e:
                    return jsonify({'error': f'无法创建目标目录: {str(e)}'}), 400

            all_file_paths = [Path(work_dir) / f['old_path'] for f in files]

            if filters and any(filters.values()):
                filtered_paths = apply_file_filters(all_file_paths, filters)
                filtered_set = set(filtered_paths)
                items_to_process = [f for f in files if str(Path(work_dir) / f['old_path']) in filtered_set]
                logs.append({'text': f'📋 过滤后匹配 {len(items_to_process)} 个文件（共 {len(files)} 个）', 'type': 'info'})
            else:
                items_to_process = files

            if not items_to_process:
                logs.append({'text': '⚠️ 没有文件匹配过滤条件', 'type': 'warning'})
                stats['message'] = '没有文件匹配过滤条件'
                return jsonify({'logs': logs, 'stats': stats})

            for i, item in enumerate(items_to_process):
                if i % BATCH_SIZE == 0:
                    memory_cleanup()
                    time.sleep(SLEEP_BETWEEN_BATCH)
                old_path = Path(work_dir) / item['old_path']
                old_name = old_path.name
                new_path = target_path / old_name

                if overwrite and new_path.exists():
                    new_path.unlink()

                try:
                    if action == 'move':
                        shutil.move(str(old_path), str(new_path))
                        logs.append({'text': f'📦 移动: {old_name} → {target_dir}', 'type': 'success'})
                    else:
                        shutil.copy2(str(old_path), str(new_path))
                        logs.append({'text': f'📋 复制: {old_name} → {target_dir}', 'type': 'success'})
                    stats['processed'] += 1
                    history.append({'old_path': str(old_path), 'new_path': str(new_path), 'old_name': old_name})
                except Exception as e:
                    logs.append({'text': f'❌ 处理失败: {old_name} - {str(e)}', 'type': 'error'})

            stats['message'] = f'成功处理 {stats["processed"]} 个文件'

        elif action in ['replace', 'regex', 'prefix', 'suffix', 'remove', 'removepos',
                        'lowercase', 'uppercase', 'capitalize', 'titlecase', 'camelcase', 'extension']:
            for i, item in enumerate(files):
                if i % BATCH_SIZE == 0:
                    memory_cleanup()
                    time.sleep(SLEEP_BETWEEN_BATCH)
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

        memory_cleanup()

        stats['message'] = f'成功处理 {stats["processed"]} 个文件'
        return jsonify({'logs': logs, 'stats': stats, 'history': history})

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f'execute error: {error_msg}')
        memory_cleanup()
        return jsonify({'error': str(e), 'trace': error_msg}), 500

def apply_file_filters(file_list, filters):
    filtered = []
    for file_path in file_list:
        file_path = Path(file_path)
        if filters.get('name_contains'):
            if filters['name_contains'].lower() not in file_path.name.lower():
                continue
        if filters.get('name_not_contains'):
            if filters['name_not_contains'].lower() in file_path.name.lower():
                continue
        ext = file_path.suffix.lower()
        if filters.get('extensions'):
            ext_list = [e.lower() if e.startswith('.') else f'.{e.lower()}' for e in filters['extensions']]
            if ext not in ext_list:
                continue
        if filters.get('extensions_not'):
            ext_list = [e.lower() if e.startswith('.') else f'.{e.lower()}' for e in filters['extensions_not']]
            if ext in ext_list:
                continue
        try:
            size = file_path.stat().st_size
            if filters.get('min_size') and size < filters['min_size'] * 1024:
                continue
            if filters.get('max_size') and size > filters['max_size'] * 1024:
                continue
        except:
            pass
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if filters.get('date_after'):
                try:
                    date_after = datetime.strptime(filters['date_after'], '%Y-%m-%d')
                    if mtime.date() < date_after.date():
                        continue
                except:
                    pass
            if filters.get('date_before'):
                try:
                    date_before = datetime.strptime(filters['date_before'], '%Y-%m-%d')
                    if mtime.date() > date_before.date():
                        continue
                except:
                    pass
        except:
            pass
        if filters.get('file_types'):
            file_type = get_file_type(file_path)
            if file_type != filters['file_types']:
                continue
        if filters.get('regex'):
            try:
                if not re.search(filters['regex'], file_path.name):
                    continue
            except:
                pass
        filtered.append(str(file_path))
    return filtered

def get_file_type(file_path):
    ext = file_path.suffix.lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif'}
    video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}
    audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}
    doc_exts = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.md'}
    archive_exts = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}
    if ext in image_exts: return 'image'
    if ext in video_exts: return 'video'
    if ext in audio_exts: return 'audio'
    if ext in doc_exts: return 'document'
    if ext in archive_exts: return 'archive'
    return 'other'

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

# ===== 去重（动态采样版） =====
@app.route('/api/dedup', methods=['POST'])
def dedup():
    data = request.json
    mode = data.get('mode', 'standard')
    action = data.get('action', 'find')
    recursive = data.get('recursive', True)
    base_path = data.get('path', '/')
    work_dir = '/data'

    mem_check = check_memory_limit()
    if mem_check['exceeded']:
        return jsonify({'error': f'内存使用超过限制，请稍后再试'}), 503

    if base_path == '/':
        target = Path(work_dir)
    else:
        clean = base_path.lstrip('/')
        target = Path(work_dir) / clean

    if not target.exists():
        return jsonify({'error': f'路径不存在: {target}'}), 404

    # 快速检查目录是否为空
    try:
        has_files = False
        for item in target.iterdir():
            if item.is_file():
                has_files = True
                break
        if not has_files:
            return jsonify({'duplicates': [], 'deleted': 0, 'message': '目录为空'})
    except PermissionError:
        return jsonify({'error': '无法读取目录'}), 403

    # 收集文件
    all_files = []
    try:
        if recursive:
            for item in target.rglob('*'):
                if item.is_file():
                    if len(all_files) >= MAX_DEDUP_FILES:
                        return jsonify({
                            'error': f'文件数量超过 {MAX_DEDUP_FILES}，请缩小范围',
                            'total': len(all_files)
                        }), 400
                    all_files.append(item)
        else:
            for item in target.iterdir():
                if item.is_file():
                    if len(all_files) >= MAX_DEDUP_FILES:
                        return jsonify({
                            'error': f'文件数量超过 {MAX_DEDUP_FILES}，请缩小范围',
                            'total': len(all_files)
                        }), 400
                    all_files.append(item)
    except PermissionError:
        return jsonify({'error': '无法读取目录'}), 403

    if not all_files:
        return jsonify({'duplicates': [], 'deleted': 0, 'message': '没有文件'})

    groups = {}
    processed = 0

    for file_path in all_files:
        try:
            if mode == 'fast':
                key = file_path.stat().st_size
            elif mode == 'precise':
                if len(all_files) > 500:
                    return jsonify({
                        'error': '精确模式最多支持500个文件，请改用 standard 模式'
                    }), 400
                hash_md5 = hashlib.md5()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hash_md5.update(chunk)
                key = hash_md5.hexdigest()
            else:
                # standard 模式：动态采样
                key = get_file_signature(file_path)

            if key not in groups:
                groups[key] = []
            groups[key].append(str(file_path))
            processed += 1

            if processed % 100 == 0:
                gc.collect()

        except Exception as e:
            print(f'处理失败: {file_path} - {e}')
            continue

    duplicates = [v for v in groups.values() if len(v) > 1]
    groups.clear()
    gc.collect()

    mode_labels = {
        'fast': '快速（按大小）',
        'standard': '标准（动态采样）',
        'precise': '精确（MD5）'
    }

    result = {'duplicates': duplicates, 'deleted': 0, 'mode': mode_labels.get(mode, '标准')}

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

# ===== 删除 =====
@app.route('/api/delete', methods=['POST'])
def delete_files():
    data = request.json
    files = data.get('files', [])
    work_dir = '/data'

    if len(files) > MAX_FILES_PER_OPERATION:
        return jsonify({'error': f'一次最多删除 {MAX_FILES_PER_OPERATION} 个文件'}), 400

    logs = []
    deleted = 0

    for i, file_path in enumerate(files):
        if i % BATCH_SIZE == 0:
            memory_cleanup()
            time.sleep(SLEEP_BETWEEN_BATCH)
        target = Path(work_dir) / file_path
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
            logs.append({'text': f'⚠️ 不存在: {file_path}', 'type': 'warning'})

    memory_cleanup()
    return jsonify({'logs': logs, 'deleted': deleted})

# ===== 过滤预览 =====
@app.route('/api/filter_preview', methods=['POST'])
def filter_preview():
    data = request.json
    files = data.get('files', [])
    filters = data.get('filters', {})
    work_dir = '/data'

    if len(files) > MAX_FILES_PER_OPERATION:
        return jsonify({'error': f'一次最多预览 {MAX_FILES_PER_OPERATION} 个文件'}), 400

    all_file_paths = [Path(work_dir) / f for f in files]
    filtered_paths = apply_file_filters(all_file_paths, filters)

    return jsonify({
        'total': len(files),
        'matched': len(filtered_paths),
        'matched_files': [str(p) for p in filtered_paths]
    })

# ===== 内存状态 =====
@app.route('/api/memory', methods=['GET'])
def memory_status():
    mem = get_memory_info()
    process_mb = get_process_memory_mb()
    percent = (process_mb / mem['total_mb']) * 100 if mem and mem['total_mb'] > 0 else 0
    return jsonify({
        'system': mem,
        'process_memory_mb': round(process_mb, 2),
        'process_percent': round(percent, 2),
        'history_count': len(rename_history),
        'max_history': MAX_HISTORY
    })

# ===== 清理内存 =====
@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    memory_cleanup()
    mem = get_memory_info()
    process_mb = get_process_memory_mb()
    return jsonify({
        'message': '内存已清理',
        'process_memory_mb': round(process_mb, 2)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
