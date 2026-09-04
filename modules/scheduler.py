# modules/scheduler.py
from flask import jsonify, request
import json
import threading
import time
import subprocess
from pathlib import Path
from datetime import datetime
import queue
import os
import re
import shutil

from core.config import WORK_DIR
from core.logger import get_logger

logger = get_logger(__name__)

# ===== 定时任务存储 =====
SCHEDULE_FILE = '/data/.scheduler_tasks.json'
task_queue = queue.Queue()
running_tasks = {}

# ===== 任务日志存储 =====
task_logs = {}


def load_tasks():
    try:
        if Path(SCHEDULE_FILE).exists():
            with open(SCHEDULE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []


def save_tasks(tasks):
    try:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
    except:
        pass


def add_task_log(task_id, message, status='info'):
    """添加任务日志"""
    if task_id not in task_logs:
        task_logs[task_id] = []
    task_logs[task_id].append({
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message': message,
        'status': status
    })
    # 保留最近50条日志
    if len(task_logs[task_id]) > 50:
        task_logs[task_id] = task_logs[task_id][-50:]
    # 保存到任务数据中
    tasks = load_tasks()
    for task in tasks:
        if task.get('id') == task_id:
            task['logs'] = task_logs[task_id]
            save_tasks(tasks)
            break


def get_files_in_directory(directory, pattern='.*', recursive=False):
    """获取目录下匹配正则的文件"""
    try:
        path = Path(directory)
        if not path.exists():
            return []
        regex = re.compile(pattern)
        files = []
        if recursive:
            # 递归遍历所有子目录
            for item in path.rglob('*'):
                if item.is_file():
                    if regex.search(item.name):
                        files.append(str(item))
        else:
            # 只遍历当前目录
            for item in path.iterdir():
                if item.is_file():
                    if regex.search(item.name):
                        files.append(str(item))
        return files
    except Exception as e:
        logger.error(f'获取文件列表失败: {e}')
        return []


def execute_task(task):
    task_id = task.get('id')
    task_name = task.get('name', '未知任务')
    params = task.get('params', {})
    target_path = params.get('target_path', '/data')
    file_pattern = params.get('file_pattern', '.*')
    recursive = params.get('recursive', False)
    task_type = task.get('type')

    add_task_log(task_id, f'任务 "{task_name}" 开始执行', 'info')
    running_tasks[task_id] = {'status': 'running', 'start': datetime.now().isoformat()}

    try:
        # ===== 获取匹配的文件列表 =====
        files = get_files_in_directory(target_path, file_pattern, recursive)
        add_task_log(task_id, f'找到 {len(files)} 个匹配的文件', 'info')

        if not files:
            add_task_log(task_id, f'没有文件匹配模式: {file_pattern}', 'warning')
            running_tasks[task_id] = {'status': 'completed', 'end': datetime.now().isoformat()}
            return

        # ===== 重命名 =====
        if task_type == 'rename':
            find_str = params.get('find', '')
            replace_str = params.get('replace', '')
            if not find_str:
                add_task_log(task_id, '重命名操作缺少查找内容', 'error')
                running_tasks[task_id] = {'status': 'error', 'end': datetime.now().isoformat()}
                return
            renamed = 0
            for file_path_str in files:
                src = Path(file_path_str)
                new_name = src.name.replace(find_str, replace_str)
                if new_name != src.name:
                    new_path = src.parent / new_name
                    try:
                        src.rename(new_path)
                        renamed += 1
                        add_task_log(task_id, f'重命名: {src.name} → {new_name}', 'success')
                    except Exception as e:
                        add_task_log(task_id, f'重命名失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'重命名完成，共处理 {renamed} 个文件', 'success')

        # ===== 去重 =====
        elif task_type == 'dedup':
            deleted = 0
            seen = {}
            for file_path_str in files:
                src = Path(file_path_str)
                try:
                    key = f'{src.stat().st_size}_{src.name}'
                    if key in seen:
                        src.unlink()
                        deleted += 1
                        add_task_log(task_id, f'删除重复: {src.name}', 'success')
                    else:
                        seen[key] = True
                except Exception as e:
                    add_task_log(task_id, f'去重失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'去重完成，删除 {deleted} 个重复文件', 'success')

        # ===== 分类整理 =====
        elif task_type == 'classify':
            classified = 0
            for file_path_str in files:
                src = Path(file_path_str)
                ext = src.suffix.lower()
                category = ext[1:] if ext.startswith('.') else (ext or '其他')
                if not category:
                    category = '其他'
                dest_dir = Path(target_path) / '分类整理' / category
                dest = dest_dir / src.name
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():
                        src.rename(dest)
                        classified += 1
                        add_task_log(task_id, f'分类: {src.name} → {category}/', 'success')
                except Exception as e:
                    add_task_log(task_id, f'分类失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'分类完成，共分类 {classified} 个文件', 'success')

        # ===== 删除 =====
        elif task_type == 'delete':
            deleted = 0
            for file_path_str in files:
                src = Path(file_path_str)
                try:
                    src.unlink()
                    deleted += 1
                    add_task_log(task_id, f'删除: {src.name}', 'success')
                except Exception as e:
                    add_task_log(task_id, f'删除失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'删除完成，共删除 {deleted} 个文件', 'success')

        # ===== 移动/复制 =====
        elif task_type == 'move_copy':
            move_action = params.get('move_action', 'move')
            move_target = params.get('move_target', '')
            move_overwrite = params.get('move_overwrite', False)
            if not move_target:
                add_task_log(task_id, '移动/复制缺少目标目录', 'error')
                running_tasks[task_id] = {'status': 'error', 'end': datetime.now().isoformat()}
                return
            dest_base = Path(move_target)
            processed = 0
            for file_path_str in files:
                src = Path(file_path_str)
                dest = dest_base / src.name
                try:
                    dest_base.mkdir(parents=True, exist_ok=True)
                    if dest.exists() and not move_overwrite:
                        stem = src.stem
                        ext = src.suffix
                        counter = 1
                        while True:
                            new_name = f'{stem}_{counter}{ext}'
                            new_dest = dest_base / new_name
                            if not new_dest.exists():
                                dest = new_dest
                                break
                            counter += 1
                    if move_action == 'move':
                        src.rename(dest)
                        add_task_log(task_id, f'移动: {src.name} → {dest.parent.name}/', 'success')
                    else:
                        shutil.copy2(str(src), str(dest))
                        add_task_log(task_id, f'复制: {src.name} → {dest.parent.name}/', 'success')
                    processed += 1
                except Exception as e:
                    add_task_log(task_id, f'{move_action}失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'{move_action}完成，共处理 {processed} 个文件', 'success')

        # ===== 权限修改 =====
        elif task_type == 'chmod':
            chmod_mode = int(params.get('chmod_mode', '755'), 8)
            chmod_recursive = params.get('chmod_recursive', False)
            processed = 0
            for file_path_str in files:
                src = Path(file_path_str)
                try:
                    os.chmod(src, chmod_mode)
                    processed += 1
                    add_task_log(task_id, f'权限修改: {src.name} → {oct(chmod_mode)}', 'success')
                except Exception as e:
                    add_task_log(task_id, f'权限修改失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'权限修改完成，共处理 {processed} 个文件', 'success')

        # ===== 图片压缩 =====
        elif task_type == 'compress':
            compress_quality = params.get('compress_quality', 85)
            compress_format = params.get('compress_format', 'original')
            compress_overwrite = params.get('compress_overwrite', False)
            compressed = 0
            image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
            for file_path_str in files:
                src = Path(file_path_str)
                ext = src.suffix.lower()
                if ext not in image_exts:
                    continue
                try:
                    if compress_overwrite:
                        output_path = src
                    else:
                        output_ext = '.' + compress_format if compress_format != 'original' else src.suffix
                        output_name = src.stem + '_compressed' + output_ext
                        output_path = src.parent / output_name
                        if output_path.exists():
                            output_name = src.stem + f'_compressed_{int(time.time())}' + output_ext
                            output_path = src.parent / output_name

                    if ext in ('.jpg', '.jpeg'):
                        if compress_format == 'webp':
                            import subprocess
                            cmd = ['cwebp', '-q', str(compress_quality), str(src), '-o', str(output_path)]
                            subprocess.run(cmd, capture_output=True, check=False)
                        else:
                            import subprocess
                            if compress_overwrite:
                                cmd = ['jpegoptim', '--max=' + str(compress_quality), str(src)]
                            else:
                                shutil.copy2(str(src), str(output_path))
                                cmd = ['jpegoptim', '--max=' + str(compress_quality), str(output_path)]
                            subprocess.run(cmd, capture_output=True, check=False)
                    elif ext == '.png':
                        if compress_format == 'webp':
                            import subprocess
                            cmd = ['cwebp', '-q', str(compress_quality), str(src), '-o', str(output_path)]
                            subprocess.run(cmd, capture_output=True, check=False)
                        else:
                            import subprocess
                            if compress_overwrite:
                                cmd = ['optipng', '-o2', str(src)]
                            else:
                                shutil.copy2(str(src), str(output_path))
                                cmd = ['optipng', '-o2', str(output_path)]
                            subprocess.run(cmd, capture_output=True, check=False)
                    else:
                        # 其他格式转 WebP
                        import subprocess
                        cmd = ['cwebp', '-q', str(compress_quality), str(src), '-o', str(output_path)]
                        subprocess.run(cmd, capture_output=True, check=False)

                    if compress_overwrite:
                        compressed += 1
                        add_task_log(task_id, f'压缩: {src.name} (覆盖原图)', 'success')
                    elif output_path.exists():
                        compressed += 1
                        add_task_log(task_id, f'压缩: {src.name} → {output_path.name}', 'success')
                except Exception as e:
                    add_task_log(task_id, f'压缩失败: {src.name} - {str(e)}', 'error')
            add_task_log(task_id, f'压缩完成，共压缩 {compressed} 张图片', 'success')

        else:
            add_task_log(task_id, f'未知任务类型: {task_type}', 'error')

        running_tasks[task_id] = {
            'status': 'completed',
            'end': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f'任务执行失败: {task_id} - {e}', exc_info=True)
        add_task_log(task_id, f'任务执行失败: {str(e)}', 'error')
        running_tasks[task_id] = {
            'status': 'error',
            'end': datetime.now().isoformat(),
            'error': str(e)
        }


def task_worker():
    while True:
        try:
            task = task_queue.get(timeout=5)
            if task is None:
                break
            execute_task(task)
        except queue.Empty:
            continue


def scheduler_loop():
    while True:
        try:
            tasks = load_tasks()
            now = datetime.now()
            for task in tasks:
                if not task.get('enabled', True):
                    continue
                last_run = task.get('last_run')
                cron = task.get('cron')
                if cron:
                    try:
                        import croniter
                        if croniter.is_valid(cron):
                            iter = croniter.croniter(cron, datetime.now())
                            next_run = iter.get_next(datetime)
                            if last_run:
                                prev = datetime.fromisoformat(last_run) if isinstance(last_run, str) else last_run
                                if now >= next_run and prev < next_run:
                                    task_queue.put(task)
                                    task['last_run'] = now.isoformat()
                                    save_tasks(tasks)
                            else:
                                task_queue.put(task)
                                task['last_run'] = now.isoformat()
                                save_tasks(tasks)
                    except Exception as e:
                        print(f'Cron error: {e}')
                elif task.get('interval'):
                    interval = task.get('interval')
                    if last_run:
                        prev = datetime.fromisoformat(last_run) if isinstance(last_run, str) else last_run
                        if (now - prev).total_seconds() >= interval:
                            task_queue.put(task)
                            task['last_run'] = now.isoformat()
                            save_tasks(tasks)
                    else:
                        task_queue.put(task)
                        task['last_run'] = now.isoformat()
                        save_tasks(tasks)
        except Exception as e:
            logger.error(f'Scheduler error: {e}')
        time.sleep(60)


# ===== 启动调度线程 =====
threading.Thread(target=scheduler_loop, daemon=True).start()
threading.Thread(target=task_worker, daemon=True).start()


def register(app):
    """注册定时任务路由"""

    @app.route('/api/scheduler/list', methods=['GET'])
    def list_tasks():
        tasks = load_tasks()
        for task in tasks:
            task_id = task.get('id')
            if task_id in running_tasks:
                task['run_status'] = running_tasks[task_id]
            else:
                task['run_status'] = None
            if 'logs' not in task:
                task['logs'] = task_logs.get(task_id, [])
        return jsonify({'tasks': tasks})

    @app.route('/api/scheduler/create', methods=['POST'])
    def create_task():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        name = data.get('name', '未命名任务')
        task_type = data.get('type', 'rename')
        cron = data.get('cron', '')
        interval = data.get('interval', 3600)
        enabled = data.get('enabled', True)
        params = data.get('params', {})

        tasks = load_tasks()
        task_id = str(int(time.time() * 1000))
        new_task = {
            'id': task_id,
            'name': name,
            'type': task_type,
            'cron': cron,
            'interval': interval,
            'enabled': enabled,
            'params': params,
            'created': datetime.now().isoformat(),
            'last_run': None,
            'logs': []
        }
        tasks.append(new_task)
        save_tasks(tasks)
        task_logs[task_id] = []

        return jsonify({'success': True, 'task': new_task})

    @app.route('/api/scheduler/delete', methods=['POST'])
    def delete_task():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        task_id = data.get('id')
        tasks = load_tasks()
        tasks = [t for t in tasks if t.get('id') != task_id]
        save_tasks(tasks)
        if task_id in task_logs:
            del task_logs[task_id]
        return jsonify({'success': True})

    @app.route('/api/scheduler/toggle', methods=['POST'])
    def toggle_task():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        task_id = data.get('id')
        tasks = load_tasks()
        for task in tasks:
            if task.get('id') == task_id:
                task['enabled'] = not task.get('enabled', True)
                break
        save_tasks(tasks)
        return jsonify({'success': True})

    @app.route('/api/scheduler/run', methods=['POST'])
    def run_task_now():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        task_id = data.get('id')
        tasks = load_tasks()
        for task in tasks:
            if task.get('id') == task_id:
                task_logs[task_id] = []
                task['logs'] = []
                task_queue.put(task)
                task['last_run'] = datetime.now().isoformat()
                save_tasks(tasks)
                add_task_log(task_id, '手动触发执行', 'info')
                return jsonify({'success': True, 'message': '任务已触发'})
        return jsonify({'error': '任务不存在'}), 404
