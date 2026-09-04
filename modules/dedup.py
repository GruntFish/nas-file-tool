# modules/dedup.py
from flask import jsonify, request
from pathlib import Path
import hashlib
import gc
import time

from core.config import WORK_DIR, MAX_DEDUP_FILES, BATCH_SIZE
from core.decorators import with_memory_cleanup, log_operation, handle_errors
from core.logger import get_logger

logger = get_logger(__name__)


def register(app):
    """注册去重路由"""

    def get_file_hash_md5(file_path):
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f'计算 MD5 失败: {file_path} - {e}')
            return None

    def get_file_signature_optimized(file_path):
        try:
            stat = file_path.stat()
            size = stat.st_size
            sample_size = 4096

            if size < 1024 * 1024:
                return get_file_hash_md5(file_path)

            if size < 100 * 1024 * 1024:
                points = 200
            else:
                points = 500

            signature = f'{file_path.name}_{size}_'

            try:
                with open(file_path, 'rb') as f:
                    step = (size - sample_size) / (points - 1) if points > 1 else 0
                    combined = bytearray()
                    for i in range(points):
                        pos = int(i * step)
                        f.seek(pos)
                        combined.extend(f.read(sample_size))
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
                    key = get_file_hash_md5(file_path)
                else:
                    key = get_file_signature_optimized(file_path)

                if key is None:
                    continue

                if key not in groups:
                    groups[key] = []
                groups[key].append(str(file_path))
                processed += 1

                if processed % 100 == 0:
                    gc.collect()

            except Exception as e:
                logger.error(f'处理失败: {file_path} - {e}')
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
                    except Exception as e:
                        logger.error(f'删除失败: {f} - {e}')
        elif action == 'delete_last':
            for group in duplicates:
                for f in group[:-1]:
                    try:
                        Path(f).unlink()
                        result['deleted'] += 1
                    except Exception as e:
                        logger.error(f'删除失败: {f} - {e}')
        elif action == 'delete_smallest':
            for group in duplicates:
                sizes = [(f, Path(f).stat().st_size) for f in group]
                sizes.sort(key=lambda x: x[1], reverse=True)
                for f, _ in sizes[1:]:
                    try:
                        Path(f).unlink()
                        result['deleted'] += 1
                    except Exception as e:
                        logger.error(f'删除失败: {f} - {e}')
        elif action == 'delete_largest':
            for group in duplicates:
                sizes = [(f, Path(f).stat().st_size) for f in group]
                sizes.sort(key=lambda x: x[1])
                for f, _ in sizes[1:]:
                    try:
                        Path(f).unlink()
                        result['deleted'] += 1
                    except Exception as e:
                        logger.error(f'删除失败: {f} - {e}')

        logger.info(f'去重完成: 发现 {len(duplicates)} 组重复，删除 {result["deleted"]} 个文件')
        return jsonify(result)
