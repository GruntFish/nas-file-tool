# modules/dedup.py
from flask import jsonify, request
from pathlib import Path
import hashlib
import gc
import time

from core.config import WORK_DIR, MAX_DEDUP_FILES, BATCH_SIZE

def register(app):
    """注册去重路由"""

    def get_file_signature(file_path):
        """动态采样签名（性能优化版）"""
        stat = file_path.stat()
        size = stat.st_size
        sample_size = 4096

        if size < 1024 * 1024:
            try:
                with open(file_path, 'rb') as f:
                    return f'{file_path.name}_{size}_' + hashlib.md5(f.read()).hexdigest()
            except:
                return f'{file_path.name}_{size}_0'

        if size < 100 * 1024 * 1024:
            points = 200
        else:
            points = 500

        signature = f'{file_path.name}_{size}_'

        try:
            with open(file_path, 'rb') as f:
                step = (size - sample_size) / (points - 1) if points > 1 else 0
                # ===== 【修复】使用 bytearray 提高效率 =====
                combined = bytearray()
                for i in range(points):
                    pos = int(i * step)
                    f.seek(pos)
                    combined.extend(f.read(sample_size))
                signature += hashlib.md5(bytes(combined)).hexdigest()
        except:
            signature += '0'

        return signature

    @app.route('/api/dedup', methods=['POST'])
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

        # 检查目录是否为空
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

        # 收集文件
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
                    hash_md5 = hashlib.md5()
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hash_md5.update(chunk)
                    key = hash_md5.hexdigest()
                else:
                    key = get_file_signature(file_path)

                if key not in groups:
                    groups[key] = []
                groups[key].append(str(file_path))
                processed += 1

                if processed % 100 == 0:
                    gc.collect()

            except Exception as e:
                print(f'处理失败: {file_path} - {e}')
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
                    except:
                        pass
        elif action == 'delete_last':
            for group in duplicates:
                for f in group[:-1]:
                    try:
                        Path(f).unlink()
                        result['deleted'] += 1
                    except:
                        pass
        elif action == 'delete_smallest':
            for group in duplicates:
                sizes = [(f, Path(f).stat().st_size) for f in group]
                sizes.sort(key=lambda x: x[1], reverse=True)
                for f, _ in sizes[1:]:
                    try:
                        Path(f).unlink()
                        result['deleted'] += 1
                    except:
                        pass
        elif action == 'delete_largest':
            for group in duplicates:
                sizes = [(f, Path(f).stat().st_size) for f in group]
                sizes.sort(key=lambda x: x[1])
                for f, _ in sizes[1:]:
                    try:
                        Path(f).unlink()
                        result['deleted'] += 1
                    except:
                        pass

        return jsonify(result)
