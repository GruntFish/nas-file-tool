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

    # ===== 内存安全的文件扫描（生成器，不一次性加载所有文件） =====
    def scan_files_generator(directory, recursive=True):
        """生成器，逐个产生文件路径，不占用大量内存"""
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

    # ===== 分块计算 MD5（避免一次性读取整个文件） =====
    def get_file_hash_md5_chunked(file_path, chunk_size=8192):
        """分块计算 MD5，适合大文件"""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b''):
                    md5.update(chunk)
                    # ===== 每读取 10MB 让出 CPU =====
                    if len(chunk) == chunk_size:
                        time.sleep(0.001)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f'计算 MD5 失败: {file_path} - {e}')
            return None

    # ===== 内存安全的签名计算 =====
    def get_file_signature_safe(file_path):
        """内存安全的文件签名（采样 + 分块）"""
        try:
            stat = file_path.stat()
            size = stat.st_size

            # 空文件直接返回
            if size == 0:
                return f'{file_path.name}_0_empty'

            # 小文件（< 1MB）：直接计算 MD5
            if size < 1024 * 1024:
                return get_file_hash_md5_chunked(file_path)

            # 大文件：采样 + 少量读取
            sample_size = 4096
            if size < 100 * 1024 * 1024:
                points = 50  # 减少采样点
            else:
                points = 100  # 减少采样点

            signature = f'{file_path.name}_{size}_'

            try:
                with open(file_path, 'rb') as f:
                    step = (size - sample_size) / (points - 1) if points > 1 else 0
                    # ===== 使用 bytearray 避免内存碎片 =====
                    combined = bytearray()
                    for i in range(points):
                        pos = int(i * step)
                        f.seek(pos)
                        combined.extend(f.read(sample_size))
                        # 每读取 10 个采样点让出 CPU
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
        recursive = data.get('recursive', True)
        base_path = data.get('path', '/')
        work_dir = WORK_DIR

        # ===== 内存检查 =====
        if hasattr(app, 'memory'):
            mem_check = app.memory['check_limit']()
            if mem_check['exceeded']:
                return jsonify({'error': '内存使用超过限制，请稍后再试'}), 503

        if base_path == '/':
            target = Path(work_dir)
        else:
            clean = base_path.lstrip('/')
            target = Path(work_dir) / clean

        if not target.exists():
            return jsonify({'error': f'路径不存在: {target}'}), 404

        # ===== 快速检查目录是否为空 =====
        try:
            has_files = False
            for _ in target.iterdir():
                if _.is_file():
                    has_files = True
                    break
            if not has_files:
                return jsonify({'duplicates': [], 'deleted': 0, 'message': '目录为空'})
        except PermissionError:
            return jsonify({'error': '无法读取目录'}), 403

        # ===== 精确模式限制 =====
        if mode == 'precise':
            # 先快速统计文件数量
            file_count = 0
            for _ in scan_files_generator(target, recursive):
                file_count += 1
                if file_count > 500:
                    return jsonify({
                        'error': '精确模式最多支持500个文件，请改用 standard 模式'
                    }), 400
            # 重置扫描
            if file_count > 500:
                return jsonify({
                    'error': '精确模式最多支持500个文件，请改用 standard 模式'
                }), 400

        # ===== 使用生成器分批处理 =====
        groups = {}
        processed = 0
        total_files = 0
        duplicates = []
        deleted_count = 0

        # ===== 第一遍：快速统计（如果文件太多，提前警告） =====
        logger.info(f'开始扫描目录: {target}')
        for _ in scan_files_generator(target, recursive):
            total_files += 1
            if total_files > MAX_DEDUP_FILES:
                return jsonify({
                    'error': f'文件数量超过 {MAX_DEDUP_FILES}，请缩小范围',
                    'total': total_files
                }), 400

        # ===== 第二遍：处理（流式，分批提交） =====
        logger.info(f'开始去重处理，共 {total_files} 个文件')
        groups = {}
        processed = 0

        # 分批处理，每批 100 个文件后清理一次内存
        batch_counter = 0
        BATCH_LIMIT = 100

        for file_path in scan_files_generator(target, recursive):
            try:
                # ===== 内存检查（每处理 50 个文件检查一次） =====
                if processed % 50 == 0 and hasattr(app, 'memory'):
                    mem_check = app.memory['check_limit']()
                    if mem_check['exceeded']:
                        # 清理并返回错误
                        groups.clear()
                        gc.collect()
                        return jsonify({'error': '内存使用超过限制，请缩小范围或使用快速模式'}), 503

                # 计算签名
                if mode == 'fast':
                    key = file_path.stat().st_size
                elif mode == 'precise':
                    key = get_file_hash_md5_chunked(file_path)
                else:
                    key = get_file_signature_safe(file_path)

                if key is None:
                    processed += 1
                    continue

                if key not in groups:
                    groups[key] = []
                groups[key].append(str(file_path))
                processed += 1

                # 每批处理完，如果 group 太大，清理部分
                batch_counter += 1
                if batch_counter >= BATCH_LIMIT:
                    # 检查 groups 大小，如果太大则清理
                    if len(groups) > 5000:
                        # 只保留有重复的组
                        temp_groups = {}
                        for k, v in groups.items():
                            if len(v) > 1:
                                temp_groups[k] = v
                        groups = temp_groups
                        gc.collect()
                    batch_counter = 0

                # 每 100 个文件主动让出 CPU
                if processed % 100 == 0:
                    time.sleep(0.05)
                    gc.collect()

            except Exception as e:
                logger.error(f'处理失败: {file_path} - {e}')
                processed += 1
                continue

        # ===== 提取重复组 =====
        duplicates = [v for v in groups.values() if len(v) > 1]
        groups.clear()
        gc.collect()

        mode_labels = {
            'fast': '快速（按大小）',
            'standard': '标准（动态采样）',
            'precise': '精确（MD5）'
        }

        result = {'duplicates': duplicates, 'deleted': 0, 'mode': mode_labels.get(mode, '标准')}

        # ===== 删除操作（分批删除，避免卡顿） =====
        if action != 'find':
            logger.info(f'开始删除重复文件，共 {len(duplicates)} 组')
            delete_batch = []
            delete_count = 0

            for group in duplicates:
                # 根据策略选择要删除的文件
                if action == 'delete_first':
                    to_delete = group[1:]
                elif action == 'delete_last':
                    to_delete = group[:-1]
                elif action == 'delete_smallest':
                    sizes = [(f, Path(f).stat().st_size) for f in group]
                    sizes.sort(key=lambda x: x[1], reverse=True)
                    to_delete = [f for f, _ in sizes[1:]]
                elif action == 'delete_largest':
                    sizes = [(f, Path(f).stat().st_size) for f in group]
                    sizes.sort(key=lambda x: x[1])
                    to_delete = [f for f, _ in sizes[1:]]
                else:
                    to_delete = []

                for f in to_delete:
                    delete_batch.append(f)
                    # 每 50 个文件批量删除一次
                    if len(delete_batch) >= 50:
                        for df in delete_batch:
                            try:
                                Path(df).unlink()
                                delete_count += 1
                            except Exception as e:
                                logger.error(f'删除失败: {df} - {e}')
                        delete_batch = []
                        time.sleep(0.05)
                        gc.collect()

            # 删除剩余的
            for df in delete_batch:
                try:
                    Path(df).unlink()
                    delete_count += 1
                except Exception as e:
                    logger.error(f'删除失败: {df} - {e}')

            result['deleted'] = delete_count
            logger.info(f'删除完成，共删除 {delete_count} 个文件')

        # ===== 最终内存清理 =====
        duplicates = None
        groups = None
        gc.collect()

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        logger.info(f'去重完成: 发现 {len(result["duplicates"])} 组重复')
        return jsonify(result)
