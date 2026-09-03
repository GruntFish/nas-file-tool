# core/async_tasks.py
import threading
import queue
import time
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

# 任务队列
_task_queue = queue.Queue()
_task_results = {}
_task_status = {}
_task_lock = threading.Lock()

# 工作线程
_worker_thread = None
_worker_running = False


class TaskStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


def _worker_loop():
    """工作线程主循环"""
    global _worker_running
    logger.info('异步任务工作线程启动')
    
    while _worker_running:
        try:
            task = _task_queue.get(timeout=1)
            if task is None:
                continue
            
            task_id = task.get('id')
            func = task.get('func')
            args = task.get('args', ())
            kwargs = task.get('kwargs', {})
            
            with _task_lock:
                _task_status[task_id] = TaskStatus.RUNNING
                _task_results[task_id] = {
                    'start_time': datetime.now().isoformat(),
                    'status': TaskStatus.RUNNING
                }
            
            try:
                logger.info(f'执行异步任务: {task_id} - {func.__name__}')
                result = func(*args, **kwargs)
                with _task_lock:
                    _task_status[task_id] = TaskStatus.COMPLETED
                    _task_results[task_id] = {
                        'result': result,
                        'end_time': datetime.now().isoformat(),
                        'status': TaskStatus.COMPLETED
                    }
                logger.info(f'异步任务完成: {task_id}')
            except Exception as e:
                logger.error(f'异步任务失败: {task_id} - {e}', exc_info=True)
                with _task_lock:
                    _task_status[task_id] = TaskStatus.FAILED
                    _task_results[task_id] = {
                        'error': str(e),
                        'end_time': datetime.now().isoformat(),
                        'status': TaskStatus.FAILED
                    }
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f'工作线程异常: {e}')
    
    logger.info('异步任务工作线程停止')


def start_worker():
    """启动工作线程"""
    global _worker_thread, _worker_running
    
    if _worker_thread and _worker_thread.is_alive():
        return
    
    _worker_running = True
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    logger.info('异步任务工作线程已启动')


def stop_worker():
    """停止工作线程"""
    global _worker_running
    _worker_running = False
    if _worker_thread:
        _task_queue.put(None)
        _worker_thread.join(timeout=5)
    logger.info('异步任务工作线程已停止')


def submit_task(func, *args, **kwargs):
    """提交异步任务"""
    task_id = f'task_{int(time.time() * 1000)}_{threading.get_ident()}'
    
    with _task_lock:
        _task_status[task_id] = TaskStatus.PENDING
        _task_results[task_id] = {
            'submitted_time': datetime.now().isoformat(),
            'status': TaskStatus.PENDING
        }
    
    _task_queue.put({
        'id': task_id,
        'func': func,
        'args': args,
        'kwargs': kwargs
    })
    
    logger.info(f'提交异步任务: {task_id} - {func.__name__}')
    return task_id


def get_task_status(task_id):
    """获取任务状态"""
    with _task_lock:
        return {
            'id': task_id,
            'status': _task_status.get(task_id, 'unknown'),
            'result': _task_results.get(task_id)
        }


def get_task_result(task_id):
    """获取任务结果"""
    with _task_lock:
        if task_id in _task_results:
            return _task_results[task_id]
        return None


def cancel_task(task_id):
    """取消任务（仅对 PENDING 任务有效）"""
    with _task_lock:
        if _task_status.get(task_id) == TaskStatus.PENDING:
            _task_status[task_id] = TaskStatus.CANCELLED
            _task_results[task_id] = {
                'status': TaskStatus.CANCELLED,
                'end_time': datetime.now().isoformat()
            }
            logger.info(f'取消任务: {task_id}')
            return True
        return False


# 启动工作线程
start_worker()
