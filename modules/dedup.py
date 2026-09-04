# modules/dedup.py
from flask import jsonify, request
from pathlib import Path
import hashlib
import gc
import time
import os

from core.config import WORK_DIR, MAX_DEDUP_FILES, BATCH_SIZE
from core.decorators import with_memory_cleanup, log_operation, handle_errors
from core.logger import get_logger

logger = get_logger(__name__)


def register(app):
    """注册去重路由"""

    def scan_files_generator(directory, recursive=True):
        """生成器，逐个产生文件路径"""
        try:
            if recursive:
                for item in directory.rglob('*'):
                    if item.is_file():
                        yield item
            else:
                for item in directory.iterdir():
                    if item.is_file():
                        yield item
        except PermissionError:
            pass

    def get_file_hash_md5_chunked(file_path, chunk_size=8192):
        """分块计算 MD5"""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    md5.update(chunk)
                    if len(chunk) == chunk_size:
                        time.sleep(0.001)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f'计算 MD5 失败: {file_path} - {e}')
            return None

    def get_file_signature_safe(file_path):
        """内存安全的文件签名"""
        try:
            stat = file_path.stat()
            size = stat.st_size

            if size == 0:
                return f'{file_path.name}_0_empty'

            if size < 1024 * 1024:
                return get_file_hash_md5_chunked(file_path)

            sample_size = 4096
            if size < 100 * 1024 * 1024:
                points = 50
            else:
                points = 100

            signature = f'{file_path.name}_{size}_'

            try:
                with open(file_path, 'rb') as f:
                    step = (size - sample_size) / (points - 1) if points > 1 else 0
                    combined = bytearray()
                    for i in range(points):
                        pos = int(i * step)
                        f.seek(pos)
                        combined.extend(f.read(sample_size))
                        if i % 10 == 0:
                            time.sleep(0.001)
                    signature += hashlib.md5(bytes(combined)).hexdigest()
            except:
                signature += '0'

            return signature
        except Exception as e:
            logger.error(f'获取文件签名失败: {file_path} - {e}')
            return None

    @app.route('/api/dedup', methods=['POST'])
    @handle_errors('去重失败')
    @log_operation('文件去重')
    @with_memory_cleanup(app)
    def dedup():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        mode = data.get('mode', 'standard')
        action = data.get('action', 'find')
        recursive = data.get('recursive', False)
        base_path = data.get('path', '/')
        work_dir = WORK_DIR

        # ===== 日志收集 =====
        logs = []

        def add_log(message, status='info', file_path=None):
            """添加日志"""
            log_entry = {
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'message': message,
                'status': status
            }
            if file_path:
                log_entry['file'] = str(file_path)
            logs.append(log_entry)
            if status == 'success':
                logger.info(message)
            elif status == 'error':
                logger.error(message)
            elif status == 'warning':
                logger.warning(message)
            else:
                logger.info(message)

        add_log(f'开始去重扫描，模式: {mode}，包含子目录: {recursive}')

        if hasattr(app, 'memory'):
            mem_check = app.memory['check_limit']()
            if mem_check['exceeded']:
                return jsonify({'error': '内存使用超过限制，请稍后再试'}), 503

        if base_path == '/':
            target = Path(work_dir)
        else:
            clean = base_path.lstrip('/')
            target = Path(work_dir) / clean

        target = target.resolve()
        base = Path(work_dir).resolve()

        try:
            target.relative_to(base)
        except ValueError:
            return jsonify({'error': '只能操作 /data 目录内的文件'}), 403

        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        add_log(f'目标目录: {target}')

        try:
            has_files = False
            for _ in target.iterdir():
                if _.is_file():
                    has_files = True
                    break
            if not has_files:
                add_log('目录中没有文件', 'warning')
                return jsonify({'duplicates': [], 'deleted': 0, 'message': '目录为空', 'logs': logs})
        except PermissionError:
            return jsonify({'error': '无法读取目录'}), 403

        if mode == 'precise':
            file_count = 0
            for _ in scan_files_generator(target, recursive):
                file_count += 1
                if file_count > 500:
                    return jsonify({
                        'error': '精确模式最多支持500个文件，请改用 standard 模式'
                    }), 400

        total_files = 0
        for _ in scan_files_generator(target, recursive):
            total_files += 1
            if total_files > MAX_DEDUP_FILES:
                return jsonify({
                    'error': f'文件数量超过 {MAX_DEDUP_FILES}，请缩小范围',
                    'total': total_files
                }), 400

        add_log(f'共发现 {total_files} 个文件')

        groups = {}
        processed = 0
        batch_counter = 0
        BATCH_LIMIT = 100

        for file_path in scan_files_generator(target, recursive):
            try:
                if processed % 50 == 0 and hasattr(app, 'memory'):
                    mem_check = app.memory['check_limit']()
                    if mem_check['exceeded']:
                        groups.clear()
                        gc.collect()
                        return jsonify({'error': '内存使用超过限制，请缩小范围或使用快速模式'}), 503

                file_name = file_path.name
                file_size = file_path.stat().st_size

                if mode == 'fast':
                    key = file_size
                    add_log(f'快速模式: {file_name} ({file_size} bytes)', 'info', file_path)
                elif mode == 'precise':
                    add_log(f'计算 MD5: {file_name} ({file_size} bytes)', 'info', file_path)
                    key = get_file_hash_md5_chunked(file_path)
                    if key:
                        add_log(f'MD5: {key[:16]}... - {file_name}', 'info', file_path)
                else:
                    add_log(f'采样签名: {file_name} ({file_size} bytes)', 'info', file_path)
                    key = get_file_signature_safe(file_path)

                if key is None:
                    add_log(f'⚠️ 无法计算签名: {file_name}', 'warning', file_path)
                    processed += 1
                    continue

                if key not in groups:
                    groups[key] = []
                groups[key].append(str(file_path))
                processed += 1

                batch_counter += 1
                if batch_counter >= BATCH_LIMIT:
                    if len(groups) > 5000:
                        temp_groups = {}
                        for k, v in groups.items():
                            if len(v) > 1:
                                temp_groups[k] = v
                        groups = temp_groups
                        gc.collect()
                    batch_counter = 0

                if processed % 100 == 0:
                    time.sleep(0.05)
                    gc.collect()

            except Exception as e:
                logger.error(f'处理失败: {file_path} - {e}')
                add_log(f'❌ 处理失败: {file_path.name} - {str(e)}', 'error', file_path)
                processed += 1
                continue

        duplicates = [v for v in groups.values() if len(v) > 1]
        groups.clear()
        gc.collect()

        add_log(f'发现 {len(duplicates)} 组重复文件')

        for idx, group in enumerate(duplicates):
            add_log(f'重复组 #{idx + 1}: {len(group)} 个文件', 'info')
            for f in group:
                add_log(f'  └─ {Path(f).name}', 'info', f)

        mode_labels = {
            'fast': '快速（按大小）',
            'standard': '标准（动态采样）',
            'precise': '精确（MD5）'
        }

        result = {'duplicates': duplicates, 'deleted': 0, 'mode': mode_labels.get(mode, '标准'), 'logs': logs}

        if action != 'find':
            add_log(f'开始删除重复文件，策略: {action}')
            delete_batch = []
            delete_count = 0

            for group in duplicates:
                if action == 'delete_first':
                    to_delete = group[1:]
                    add_log(f'保留第一个: {Path(group[0]).name}', 'info', group[0])
                elif action == 'delete_last':
                    to_delete = group[:-1]
                    add_log(f'保留最后一个: {Path(group[-1]).name}', 'info', group[-1])
                elif action == 'delete_smallest':
                    sizes = [(f, Path(f).stat().st_size) for f in group]
                    sizes.sort(key=lambda x: x[1], reverse=True)
                    to_delete = [f for f, _ in sizes[1:]]
                    add_log(f'保留最大的: {Path(sizes[0][0]).name} ({sizes[0][1]} bytes)', 'info', sizes[0][0])
                elif action == 'delete_largest':
                    sizes = [(f, Path(f).stat().st_size) for f in group]
                    sizes.sort(key=lambda x: x[1])
                    to_delete = [f for f, _ in sizes[1:]]
                    add_log(f'保留最小的: {Path(sizes[0][0]).name} ({sizes[0][1]} bytes)', 'info', sizes[0][0])
                else:
                    to_delete = []

                for f in to_delete:
                    delete_batch.append(f)
                    if len(delete_batch) >= 50:
                        for df in delete_batch:
                            try:
                                Path(df).unlink()
                                delete_count += 1
                                add_log(f'🗑️ 删除: {Path(df).name}', 'success', df)
                            except Exception as e:
                                add_log(f'❌ 删除失败: {Path(df).name} - {str(e)}', 'error', df)
                        delete_batch = []
                        time.sleep(0.05)
                        gc.collect()

            for df in delete_batch:
                try:
                    Path(df).unlink()
                    delete_count += 1
                    add_log(f'🗑️ 删除: {Path(df).name}', 'success', df)
                except Exception as e:
                    add_log(f'❌ 删除失败: {Path(df).name} - {str(e)}', 'error', df)

            result['deleted'] = delete_count
            add_log(f'删除完成，共删除 {delete_count} 个文件')

        duplicates = None
        groups = None
        gc.collect()

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        add_log(f'去重完成')

        return jsonify(result)
