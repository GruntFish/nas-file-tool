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


def get_files_in_directory(directory, pattern='.*'):
    """获取目录下匹配正则的文件"""
    try:
        path = Path(directory)
        if not path.exists():
            return []
        regex = re.compile(pattern)
        files = []
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
    task_type = task.get('type')

    add_task_log(task_id, f'任务 "{task_name}" 开始执行', 'info')
    running_tasks[task_id] = {'status': 'running', 'start': datetime.now().isoformat()}

    try:
        # ===== 获取匹配的文件列表 =====
        files = get_files_in_directory(target_path, file_pattern)
        add_task_log(task_id, f'找到 {len(files)} 个匹配的文件', 'info')

        if not files:
            add_task_log(task_id, f'没有文件匹配模式: {file_pattern}', 'warning')
            running_tasks[task_id] = {'status': 'completed', 'end': datetime.now().isoformat()}
            return

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

        elif task_type == 'dedup':
            from modules.dedup import register as dedup_register
            # 直接调用去重逻辑
            deleted = 0
            seen = {}
            for file_path_str in files:
                src = Path(file_path_str)
                try:
                    # 简单去重：按文件大小 + 名称判断
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

        elif task_type == 'classify':
            from modules.classify import register as classify_register
            # 按扩展名分类
            classified = 0
            for file_path_str in files:
                src = Path(file_path_str)
                ext = src.suffix.lower()
                if ext:
                    # 去掉开头的点
                    category = ext[1:] if ext.startswith('.') else ext
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
            # 确保 logs 字段存在
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
                # 清空旧日志
                task_logs[task_id] = []
                task['logs'] = []
                task_queue.put(task)
                task['last_run'] = datetime.now().isoformat()
                save_tasks(tasks)
                add_task_log(task_id, '手动触发执行', 'info')
                return jsonify({'success': True, 'message': '任务已触发'})
        return jsonify({'error': '任务不存在'}), 404
