from flask import Flask, render_template, request, jsonify
import os
import re
import hashlib
import subprocess
from pathlib import Path

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/preview', methods=['POST'])
def preview():
    data = request.json
    pattern = data.get('pattern', '')
    replacement = data.get('replacement', '')
    work_dir = '/data'

    if not pattern:
        return jsonify({'error': '匹配模式不能为空'}), 400

    files = []
    try:
        for file_path in Path(work_dir).iterdir():
            if not file_path.is_file():
                continue
            old_name = file_path.name
            new_name = re.sub(pattern, replacement, old_name)
            files.append({
                'old_name': old_name,
                'new_name': new_name
            })
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute', methods=['POST'])
def execute():
    data = request.json
    tool = data.get('tool')
    logs = []
    stats = {'processed': 0, 'message': '成功'}
    work_dir = '/data'

    try:
        if tool == 'rename':
            pattern = data.get('pattern', '')
            replacement = data.get('replacement', '')
            files_to_rename = data.get('files', [])

            if not files_to_rename:
                return jsonify({'error': '没有文件需要重命名'}), 400

            renamed_count = 0
            for file_info in files_to_rename:
                old_path = Path(work_dir) / file_info['old_name']
                new_path = Path(work_dir) / file_info['new_name']
                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)
                    renamed_count += 1
                    logs.append({'text': f'✏️ 重命名: {file_info["old_name"]} → {file_info["new_name"]}', 'type': 'success'})

            stats['processed'] = renamed_count
            stats['message'] = f'成功重命名 {renamed_count} 个文件'

        elif tool == 'dedup':
            delete = data.get('delete', False)
            cmd = ['python3', '/app/processor.py', 'dedup', '--dir', work_dir]
            if delete:
                cmd.append('--delete')
            result = subprocess.run(cmd, capture_output=True, text=True)
            logs = [{'text': line, 'type': 'info'} for line in result.stdout.split('\n') if line.strip()]
            stats['processed'] = len([l for l in result.stdout.split('\n') if '删除' in l])
            stats['message'] = '去重完成'

        elif tool == 'compress':
            quality = data.get('quality', 80)
            format_type = data.get('format', 'original')
            cmd = ['python3', '/app/processor.py', 'compress', '--dir', work_dir, '--quality', str(quality)]
            if format_type != 'original':
                cmd.extend(['--format', format_type])
            result = subprocess.run(cmd, capture_output=True, text=True)
            logs = [{'text': line, 'type': 'info'} for line in result.stdout.split('\n') if line.strip()]
            stats['processed'] = len([l for l in result.stdout.split('\n') if '压缩' in l])
            stats['message'] = '压缩完成'

        else:
            return jsonify({'error': f'未知工具: {tool}'}), 400

        if result.stderr:
            logs.append({'text': f'⚠️ {result.stderr}', 'type': 'error'})

        return jsonify({'logs': logs, 'stats': stats})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)