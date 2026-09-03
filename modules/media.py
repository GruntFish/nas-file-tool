# modules/media.py
from flask import jsonify, request
from pathlib import Path
import subprocess
import time
import hashlib
import shutil
import os

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE

def register(app):
    """注册媒体处理路由"""

    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}

    def check_tool(tool_name):
        try:
            subprocess.run([tool_name, '--version'], capture_output=True, timeout=5)
            return True
        except:
            return False

    @app.route('/api/media/compress', methods=['POST'])
    def compress_images():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        files = data.get('files', [])
        quality = data.get('quality', 85)
        format_type = data.get('format', 'original')
        dry_run = data.get('dry_run', True)
        # ===== 【新增】覆盖模式 =====
        overwrite = data.get('overwrite', False)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要压缩的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        if not dry_run:
            if format_type == 'original':
                if not check_tool('jpegoptim') or not check_tool('optipng'):
                    return jsonify({'error': '缺少压缩工具，请安装 jpegoptim 和 optipng'}), 503
            elif format_type == 'webp':
                if not check_tool('cwebp'):
                    return jsonify({'error': '缺少 cwebp 工具，请安装 webp'}), 503

        results = []
        stats = {'processed': 0, 'compressed': 0, 'skipped': 0, 'errors': 0, 'saved_bytes': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            original_size = src.stat().st_size

            # ===== 【修改】根据覆盖模式决定输出路径 =====
            if overwrite:
                # 覆盖模式：直接使用原文件路径
                output_path = src
                output_name = src.name
                # 先备份原文件到临时位置（防止压缩失败丢失数据）
                temp_backup = src.parent / f'.{src.name}.backup'
                try:
                    shutil.copy2(str(src), str(temp_backup))
                except:
                    pass
            else:
                # 不覆盖：生成新文件
                output_ext = '.' + format_type if format_type != 'original' else src.suffix
                output_name = src.stem + '_compressed' + output_ext
                output_path = src.parent / output_name
                # 如果已存在，加时间戳
                if output_path.exists():
                    output_name = src.stem + f'_compressed_{int(time.time())}' + output_ext
                    output_path = src.parent / output_name

            if dry_run:
                estimated_ratio = 0.6 if quality < 80 else 0.8
                if src.suffix.lower() == '.png':
                    estimated_ratio = 0.7 if quality < 80 else 0.9
                estimated_size = int(original_size * estimated_ratio)
                stats['processed'] += 1
                results.append({
                    'file': src.name,
                    'output': output_name,
                    'original_size': original_size,
                    'estimated_size': estimated_size,
                    'estimated_ratio': round((1 - estimated_size/original_size) * 100, 1) if original_size > 0 else 0,
                    'status': 'preview',
                    'overwrite': overwrite
                })
                continue

            try:
                ext = src.suffix.lower()
                
                # ===== 【修改】根据覆盖模式处理 =====
                if overwrite:
                    # 覆盖模式：直接压缩原文件
                    if ext in ('.jpg', '.jpeg'):
                        result = subprocess.run(['jpegoptim', '--max=' + str(quality), str(src)], capture_output=True, check=False)
                    elif ext == '.png':
                        result = subprocess.run(['optipng', '-o2', str(src)], capture_output=True, check=False)
                    else:
                        # 其他格式先转成临时文件再替换
                        temp_output = src.parent / f'.{src.stem}_temp.{format_type if format_type != "original" else "webp"}'
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(temp_output)]
                        subprocess.run(cmd, capture_output=True, check=False)
                        if temp_output.exists():
                            # 用压缩后的文件替换原文件
                            os.remove(str(src))
                            temp_output.rename(src)
                    # 删除备份
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    # 不覆盖：生成新文件
                    if ext in ('.jpg', '.jpeg'):
                        shutil.copy2(str(src), str(output_path))
                        subprocess.run(['jpegoptim', '--max=' + str(quality), str(output_path)], capture_output=True, check=False)
                    elif ext == '.png':
                        shutil.copy2(str(src), str(output_path))
                        subprocess.run(['optipng', '-o2', str(output_path)], capture_output=True, check=False)
                    else:
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(output_path)]
                        subprocess.run(cmd, capture_output=True, check=False)

                # 获取压缩后大小
                if output_path.exists():
                    new_size = output_path.stat().st_size
                else:
                    new_size = src.stat().st_size
                saved = original_size - new_size
                stats['saved_bytes'] += saved if saved > 0 else 0

                stats['compressed'] += 1
                stats['processed'] += 1
                results.append({
                    'file': src.name,
                    'output': output_path.name if output_path.exists() else src.name,
                    'original_size': original_size,
                    'new_size': new_size,
                    'saved': saved,
                    'ratio': round((1 - new_size/original_size) * 100, 1) if original_size > 0 else 0,
                    'status': 'success',
                    'overwrite': overwrite
                })
            except Exception as e:
                stats['errors'] += 1
                # 如果压缩失败且是覆盖模式，尝试恢复备份
                if overwrite:
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        if src.exists():
                            os.remove(str(src))
                        temp_backup.rename(src)
                results.append({
                    'file': src.name,
                    'status': 'error',
                    'reason': str(e),
                    'overwrite': overwrite
                })

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'quality': quality,
            'format': format_type,
            'overwrite': overwrite
        })

    # ===== 【修改】convert 和 resize 也添加 overwrite 支持 =====
    @app.route('/api/media/convert', methods=['POST'])
    def convert_images():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        files = data.get('files', [])
        target_format = data.get('target_format', 'webp')
        quality = data.get('quality', 85)
        dry_run = data.get('dry_run', True)
        overwrite = data.get('overwrite', False)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要转换的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        if not dry_run:
            if target_format == 'webp' and not check_tool('cwebp'):
                return jsonify({'error': '缺少 cwebp 工具，请安装 webp'}), 503
            if target_format in ('jpg', 'jpeg', 'png') and not check_tool('convert'):
                return jsonify({'error': '缺少 ImageMagick 工具，请安装 imagemagick'}), 503

        results = []
        stats = {'processed': 0, 'converted': 0, 'skipped': 0, 'errors': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            # ===== 【修改】根据覆盖模式决定输出路径 =====
            if overwrite:
                # 覆盖模式：先备份原文件
                output_path = src
                output_name = src.name
                temp_backup = src.parent / f'.{src.name}.backup'
                try:
                    shutil.copy2(str(src), str(temp_backup))
                except:
                    pass
            else:
                output_name = src.stem + '.' + target_format
                output_path = src.parent / output_name
                if output_path == src:
                    output_name = src.stem + '_converted.' + target_format
                    output_path = src.parent / output_name

            if dry_run:
                stats['processed'] += 1
                results.append({
                    'file': src.name,
                    'output': output_name,
                    'from': src.suffix.lower(),
                    'to': target_format,
                    'status': 'preview',
                    'overwrite': overwrite
                })
                continue

            try:
                # ===== 【修改】根据覆盖模式处理 =====
                if overwrite:
                    # 覆盖模式：转换后替换原文件
                    temp_output = src.parent / f'.{src.stem}_temp.{target_format}'
                    if target_format == 'webp':
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(temp_output)]
                    elif target_format in ('jpg', 'jpeg'):
                        cmd = ['convert', str(src), '-quality', str(quality), str(temp_output)]
                    elif target_format == 'png':
                        cmd = ['convert', str(src), str(temp_output)]
                    else:
                        return jsonify({'error': f'不支持的格式: {target_format}'}), 400
                    subprocess.run(cmd, capture_output=True, check=False)
                    if temp_output.exists():
                        os.remove(str(src))
                        temp_output.rename(src)
                    # 删除备份
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    if target_format == 'webp':
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(output_path)]
                    elif target_format in ('jpg', 'jpeg'):
                        cmd = ['convert', str(src), '-quality', str(quality), str(output_path)]
                    elif target_format == 'png':
                        cmd = ['convert', str(src), str(output_path)]
                    else:
                        return jsonify({'error': f'不支持的格式: {target_format}'}), 400
                    subprocess.run(cmd, capture_output=True, check=False)

                if output_path.exists():
                    stats['converted'] += 1
                    stats['processed'] += 1
                    results.append({
                        'file': src.name,
                        'output': output_path.name,
                        'from': src.suffix.lower(),
                        'to': target_format,
                        'size': output_path.stat().st_size,
                        'status': 'success',
                        'overwrite': overwrite
                    })
                else:
                    stats['errors'] += 1
                    results.append({'file': src.name, 'status': 'error', 'reason': '转换失败', 'overwrite': overwrite})
            except Exception as e:
                stats['errors'] += 1
                # 如果失败且是覆盖模式，尝试恢复备份
                if overwrite:
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        if src.exists():
                            os.remove(str(src))
                        temp_backup.rename(src)
                results.append({'file': src.name, 'status': 'error', 'reason': str(e), 'overwrite': overwrite})

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'target_format': target_format,
            'quality': quality,
            'overwrite': overwrite
        })

    @app.route('/api/media/resize', methods=['POST'])
    def resize_images():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        files = data.get('files', [])
        width = data.get('width', 1920)
        height = data.get('height', 1080)
        mode = data.get('mode', 'fit')
        dry_run = data.get('dry_run', True)
        overwrite = data.get('overwrite', False)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要调整的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        if not dry_run and not check_tool('convert'):
            return jsonify({'error': '缺少 ImageMagick 工具，请安装 imagemagick'}), 503

        results = []
        stats = {'processed': 0, 'resized': 0, 'skipped': 0, 'errors': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            # ===== 【修改】根据覆盖模式决定输出路径 =====
            if overwrite:
                output_path = src
                output_name = src.name
                temp_backup = src.parent / f'.{src.name}.backup'
                try:
                    shutil.copy2(str(src), str(temp_backup))
                except:
                    pass
            else:
                output_name = src.stem + f'_{width}x{height}' + src.suffix
                output_path = src.parent / output_name

            if dry_run:
                stats['processed'] += 1
                results.append({
                    'file': src.name,
                    'output': output_name,
                    'width': width,
                    'height': height,
                    'mode': mode,
                    'status': 'preview',
                    'overwrite': overwrite
                })
                continue

            try:
                # ===== 【修改】根据覆盖模式处理 =====
                if overwrite:
                    temp_output = src.parent / f'.{src.stem}_temp{src.suffix}'
                    if mode == 'fit':
                        resize_arg = f'{width}x{height}>'
                    elif mode == 'fill':
                        resize_arg = f'{width}x{height}^'
                    elif mode == 'stretch':
                        resize_arg = f'{width}x{height}!'
                    else:
                        resize_arg = f'{width}x{height}'
                    cmd = ['convert', str(src), '-resize', resize_arg, str(temp_output)]
                    subprocess.run(cmd, capture_output=True, check=False)
                    if temp_output.exists():
                        os.remove(str(src))
                        temp_output.rename(src)
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    if mode == 'fit':
                        resize_arg = f'{width}x{height}>'
                    elif mode == 'fill':
                        resize_arg = f'{width}x{height}^'
                    elif mode == 'stretch':
                        resize_arg = f'{width}x{height}!'
                    else:
                        resize_arg = f'{width}x{height}'
                    cmd = ['convert', str(src), '-resize', resize_arg, str(output_path)]
                    subprocess.run(cmd, capture_output=True, check=False)

                if output_path.exists():
                    stats['resized'] += 1
                    stats['processed'] += 1
                    results.append({
                        'file': src.name,
                        'output': output_path.name,
                        'original_size': src.stat().st_size,
                        'new_size': output_path.stat().st_size,
                        'status': 'success',
                        'overwrite': overwrite
                    })
                else:
                    stats['errors'] += 1
                    results.append({'file': src.name, 'status': 'error', 'reason': '调整失败', 'overwrite': overwrite})
            except Exception as e:
                stats['errors'] += 1
                if overwrite:
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        if src.exists():
                            os.remove(str(src))
                        temp_backup.rename(src)
                results.append({'file': src.name, 'status': 'error', 'reason': str(e), 'overwrite': overwrite})

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'width': width,
            'height': height,
            'mode': mode,
            'overwrite': overwrite
        })
