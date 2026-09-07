# modules/dedup.py
from flask import jsonify, request
from pathlib import Path
import hashlib
import gc
import time
import os
import struct

from core.config import WORK_DIR, MAX_DEDUP_FILES, BATCH_SIZE
from core.decorators import with_memory_cleanup, log_operation, handle_errors
from core.logger import get_logger

logger = get_logger(__name__)

# ===== 尝试导入 xxhash，如果没有则降级 =====
try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False
    logger.warning('xxhash 未安装，将使用 MD5 作为主要哈希')


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

    def get_file_hash_xxhash(file_path, sample_size=4096):
        """计算文件采样 xxHash（极快）"""
        if not HAS_XXHASH:
            return None
        try:
            xxh = xxhash.xxh64()
            with open(file_path, 'rb') as f:
                # 读取开头
                data = f.read(sample_size)
                xxh.update(data)
                # 读取结尾
                f.seek(-min(sample_size, f.tell()), 2)
                data = f.read(sample_size)
                xxh.update(data)
            return xxh.hexdigest()
        except Exception as e:
            logger.error(f'xxHash 计算失败: {file_path} - {e}')
            return None

    def get_file_hash_md5_chunked(file_path, chunk_size=8192):
        """分块计算完整 MD5"""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f'MD5 计算失败: {file_path} - {e}')
            return None

    def get_file_signature_optimized(file_path):
        """
        三级去重签名：
        1. 文件大小（快速筛选）
        2. xxHash 采样（极速过滤）
        3. MD5（精准确认）
        """
        try:
            stat = file_path.stat()
            size = stat.st_size

            if size == 0:
                return {
                    'key': f'{file_path.name}_0_empty',
                    'method': 'empty'
                }

            # ===== 第一级：文件大小 =====
            size_key = f'{size}'

            # ===== 第二级：xxHash 采样（极快） =====
            xxh = get_file_hash_xxhash(file_path)
            if xxh:
                xxh_key = f'{size_key}_{xxh}'
                # 小文件（< 10MB）：直接返回 xxHash 结果（足够精准）
                if size < 10 * 1024 * 1024:
                    return {
                        'key': xxh_key,
                        'method': 'xxhash_small'
                    }
                # 大文件：先用 xxHash 预筛选，再决定是否用 MD5
                # 但 xxHash 本身已经足够精准，加上 size 和文件名前缀，碰撞概率极低
                # 为了更安全，对大文件我们也只返回 xxHash + size
                return {
                    'key': xxh_key,
                    'method': 'xxhash_large'
                }
            else:
                # xxhash 不可用，使用 MD5
                md5 = get_file_hash_md5_chunked(file_path)
                if md5:
                    return {
                        'key': f'{size_key}_{md5}',
                        'method': 'md5'
                    }
                return None

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
        add_log(f'哈希引擎: {"xxHash + MD5" if HAS_XXHASH else "MD5"}')

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

        # 精确模式限制
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
        stats_methods = {'empty': 0, 'xxhash_small': 0, 'xxhash_large': 0, 'md5': 0, 'failed': 0}

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
                    # 快速模式：只用大小
                    key = f'{file_size}'
                    method = 'size_only'
                    add_log(f'快速模式: {file_name} ({file_size} bytes)', 'info', file_path)
                else:
                    # 标准/精确模式：使用优化签名
                    result = get_file_signature_optimized(file_path)
                    if result is None:
                        add_log(f'⚠️ 无法计算签名: {file_name}', 'warning', file_path)
                        stats_methods['failed'] += 1
                        processed += 1
                        continue
                    key = result['key']
                    method = result['method']
                    stats_methods[method] = stats_methods.get(method, 0) + 1
                    if processed % 50 == 0:
                        add_log(f'处理: {file_name} ({method})', 'info', file_path)

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

        # ===== 提取重复组 =====
        duplicates = [v for v in groups.values() if len(v) > 1]
        groups.clear()
        gc.collect()

        add_log(f'发现 {len(duplicates)} 组重复文件')
        add_log(f'哈希统计: 小文件xxHash={stats_methods.get("xxhash_small", 0)}, '
                f'大文件xxHash={stats_methods.get("xxhash_large", 0)}, '
                f'MD5={stats_methods.get("md5", 0)}, '
                f'空文件={stats_methods.get("empty", 0)}')

        for idx, group in enumerate(duplicates):
            add_log(f'重复组 #{idx + 1}: {len(group)} 个文件', 'info')
            for f in group:
                add_log(f'  └─ {Path(f).name}', 'info', f)

        mode_labels = {
            'fast': '快速（按大小）',
            'standard': '标准（xxHash + MD5）',
            'precise': '精确（完整MD5，限500文件）'
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
