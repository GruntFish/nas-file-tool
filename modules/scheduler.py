# modules/scheduler.py
from flask import jsonify, request
import json
import threading
import time
import subprocess
from pathlib import Path
from datetime import datetime
import queue

from core.config import WORK_DIR

# ===== 定时任务存储 =====
SCHEDULE_FILE = '/data/.scheduler_tasks.json'
task_queue = queue.Queue()
running_tasks = {}

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

def task_worker():
    while True:
        try:
            task = task_queue.get(timeout=5)
            if task is None:
                break
            execute_task(task)
        except queue.Empty:
            continue

def execute_task(task):
    task_id = task.get('id')
    running_tasks[task_id] = {'status': 'running', 'start': datetime.now().isoformat()}
    try:
        task_type = task.get('type')
        # ===== 【修复】使用正确的参数 =====
        if task_type == 'rename':
            params = task.get('params', {})
            pattern = params.get('pattern', '')
            replacement = params.get('replacement', '')
            result = subprocess.run(
                ['python3', '/app/processor.py', 'rename', '--pattern', pattern, '--replacement', replacement, '--dir', WORK_DIR],
                capture_output=True, text=True, timeout=300
            )
        elif task_type == 'dedup':
            result = subprocess.run(
                ['python3', '/app/processor.py', 'dedup', '--dir', WORK_DIR, '--delete'],
                capture_output=True, text=True, timeout=600
            )
        elif task_type == 'classify':
            # processor.py 暂时不支持 classify，用 Python 直接调用
            from modules.classify import register as classify_register
            # 简单实现：直接调用分类逻辑
            result = subprocess.run(
                ['python3', '-c', f'from modules.classify import classify_files; classify_files("{WORK_DIR}")'],
                capture_output=True, text=True, timeout=600
            )
        else:
            result = subprocess.run(
                ['echo', f'Unknown task type: {task_type}'],
                capture_output=True, text=True
            )

        running_tasks[task_id] = {
            'status': 'completed',
            'end': datetime.now().isoformat(),
            'output': result.stdout,
            'error': result.stderr
        }
    except subprocess.TimeoutExpired:
        running_tasks[task_id] = {'status': 'timeout', 'end': datetime.now().isoformat()}
    except Exception as e:
        running_tasks[task_id] = {'status': 'error', 'end': datetime.now().isoformat(), 'error': str(e)}

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
                        # ===== 【修复】正确使用 croniter =====
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
            print(f'Scheduler error: {e}')
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
            'last_run': None
        }
        tasks.append(new_task)
        save_tasks(tasks)

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
                task_queue.put(task)
                task['last_run'] = datetime.now().isoformat()
                save_tasks(tasks)
                return jsonify({'success': True, 'message': '任务已触发'})
        return jsonify({'error': '任务不存在'}), 404
