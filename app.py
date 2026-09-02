from flask import Flask, render_template, request, jsonify
import os
import re
import subprocess
from pathlib import Path

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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

    def build_tree(path, depth=0, max_depth=2):
        if depth > max_depth:
            return []
        nodes = []
        try:
            for item in sorted(path.iterdir()):
                node = {
                    'name': item.name,
                    'path': str(item.relative_to(work_dir)),
                    'is_dir': item.is_dir(),
                    'size': item.stat().st_size if item.is_file() else 0,
                }
                if item.is_dir() and depth < max_depth:
                    node['children'] = build_tree(item, depth + 1, max_depth)
                else:
                    node['children'] = []
                nodes.append(node)
        except PermissionError:
            pass
        return nodes

    tree = build_tree(target, 0, 2)
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
    pattern = data.get('pattern', '')
    replacement = data.get('replacement', '')
    files = data.get('files', [])
    work_dir = '/data'

    if not pattern:
        return jsonify({'error': '匹配模式不能为空'}), 400

    results = []
    for file_path in files:
        old_name = Path(file_path).name
        try:
            new_name = re.sub(pattern, replacement, old_name)
        except re.error:
            # 如果不是有效的正则，当作普通字符串替换
            new_name = old_name.replace(pattern, replacement)
        if new_name != old_name:
            results.append({
                'old_path': file_path,
                'new_path': str(Path(file_path).parent / new_name),
                'old_name': old_name,
                'new_name': new_name,
            })

    return jsonify({'files': results})

# ===== 执行操作 =====
@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.json
    action = data.get('action')
    work_dir = '/data'

    logs = []
    stats = {'processed': 0, 'message': '成功'}

    if action == 'rename':
        files = data.get('files', [])
        renamed = 0
        for file_info in files:
            old_path = Path(work_dir) / file_info['old_path']
            new_path = Path(work_dir) / file_info['new_path']
            if old_path.exists() and not new_path.exists():
                old_path.rename(new_path)
                renamed += 1
                logs.append({
                    'text': f'✏️ 重命名: {file_info["old_name"]} → {file_info["new_name"]}',
                    'type': 'success'
                })
        stats['processed'] = renamed
        stats['message'] = f'成功重命名 {renamed} 个文件'

    elif action == 'dedup':
        delete = data.get('delete', False)
        cmd = ['python3', '/app/processor.py', 'dedup', '--dir', work_dir]
        if delete:
            cmd.append('--delete')
        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line.strip():
                logs.append({'text': line, 'type': 'info'})
        stats['processed'] = len([l for l in result.stdout.split('\n') if '删除' in l])
        stats['message'] = '去重完成'

    elif action == 'compress':
        quality = data.get('quality', 80)
        format_type = data.get('format', 'original')
        cmd = ['python3', '/app/processor.py', 'compress', '--dir', work_dir, '--quality', str(quality)]
        if format_type != 'original':
            cmd.extend(['--format', format_type])
        result = subprocess.run(cmd, capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line.strip():
                logs.append({'text': line, 'type': 'info'})
        stats['processed'] = len([l for l in result.stdout.split('\n') if '压缩' in l])
        stats['message'] = '压缩完成'

    else:
        return jsonify({'error': f'未知操作: {action}'}), 400

    if result.stderr:
        logs.append({'text': f'⚠️ {result.stderr}', 'type': 'error'})

    return jsonify({'logs': logs, 'stats': stats})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
