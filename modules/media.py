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

    # ===== 【新增】获取图片尺寸（使用 vips） =====
    def get_image_size(image_path):
        """使用 vips 获取图片宽高"""
        try:
            result = subprocess.run(
                ['vips', 'header', str(image_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            # 解析 vips header 输出
            lines = result.stdout.strip().split('\n')
            width = None
            height = None
            for line in lines:
                if 'width' in line.lower():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        width = int(parts[1].strip())
                elif 'height' in line.lower():
                    parts = line.split(':')
                    if len(parts) >= 2:
                        height = int(parts[1].strip())
            return width, height
        except:
            return None, None

    @app.route('/api/media/compress', methods=['POST'])
    def compress_images():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        files = data.get('files', [])
        quality = data.get('quality', 85)
        format_type = data.get('format', 'original')
        dry_run = data.get('dry_run', True)
        overwrite = data.get('overwrite', False)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要压缩的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        if not dry_run:
            if format_type == 'original' or format_type in ('jpg', 'jpeg'):
                if not check_tool('jpegoptim'):
                    return jsonify({'error': '缺少 jpegoptim 工具'}), 503
            if format_type == 'png' or format_type == 'original':
                if not check_tool('optipng'):
                    return jsonify({'error': '缺少 optipng 工具'}), 503
            if format_type == 'webp':
                if not check_tool('cwebp'):
                    return jsonify({'error': '缺少 cwebp 工具'}), 503

        results = []
        stats = {'processed': 0, 'compressed': 0, 'skipped': 0, 'errors': 0, 'saved_bytes': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str.lstrip('/')
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            original_size = src.stat().st_size

            # 根据覆盖模式决定输出路径
            if overwrite:
                output_path = src
                output_name = src.name
                temp_backup = src.parent / f'.{src.name}.backup'
                try:
                    shutil.copy2(str(src), str(temp_backup))
                except:
                    pass
            else:
                output_ext = '.' + format_type if format_type != 'original' else src.suffix
                output_name = src.stem + '_compressed' + output_ext
                output_path = src.parent / output_name
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

                if overwrite:
                    # 覆盖模式：直接压缩原文件
                    if ext in ('.jpg', '.jpeg'):
                        subprocess.run(['jpegoptim', '--max=' + str(quality), str(src)], capture_output=True, check=False)
                    elif ext == '.png':
                        subprocess.run(['optipng', '-o2', str(src)], capture_output=True, check=False)
                    else:
                        # 其他格式转成 WebP 再替换
                        temp_output = src.parent / f'.{src.stem}_temp.webp'
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(temp_output)]
                        subprocess.run(cmd, capture_output=True, check=False)
                        if temp_output.exists():
                            os.remove(str(src))
                            temp_output.rename(src)
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
                return jsonify({'error': '缺少 cwebp 工具'}), 503
            if target_format in ('jpg', 'jpeg') and not check_tool('vips'):
                return jsonify({'error': '缺少 vips 工具'}), 503
            if target_format == 'png' and not check_tool('vips'):
                return jsonify({'error': '缺少 vips 工具'}), 503

        results = []
        stats = {'processed': 0, 'converted': 0, 'skipped': 0, 'errors': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str.lstrip('/')
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            if overwrite:
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
                if overwrite:
                    temp_output = src.parent / f'.{src.stem}_temp.{target_format}'
                    if target_format == 'webp':
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(temp_output)]
                    elif target_format in ('jpg', 'jpeg'):
                        # ===== 【修改】使用 vips 替代 convert =====
                        cmd = ['vips', 'copy', str(src), str(temp_output), '[Q=' + str(quality) + ']']
                    elif target_format == 'png':
                        cmd = ['vips', 'copy', str(src), str(temp_output)]
                    else:
                        return jsonify({'error': f'不支持的格式: {target_format}'}), 400
                    subprocess.run(cmd, capture_output=True, check=False)
                    if temp_output.exists():
                        os.remove(str(src))
                        temp_output.rename(src)
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    if target_format == 'webp':
                        cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(output_path)]
                    elif target_format in ('jpg', 'jpeg'):
                        cmd = ['vips', 'copy', str(src), str(output_path), '[Q=' + str(quality) + ']']
                    elif target_format == 'png':
                        cmd = ['vips', 'copy', str(src), str(output_path)]
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

        if not dry_run and not check_tool('vips'):
            return jsonify({'error': '缺少 vips 工具'}), 503

        results = []
        stats = {'processed': 0, 'resized': 0, 'skipped': 0, 'errors': 0}

        for i, file_path_str in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(0.05)

            src = Path(work_dir) / file_path_str.lstrip('/')
            if not src.exists():
                stats['skipped'] += 1
                results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            # 获取原始图片尺寸
            orig_width, orig_height = get_image_size(src)
            if orig_width is None or orig_height is None:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '无法读取图片尺寸'})
                continue

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
                temp_output = src.parent / f'.{src.stem}_temp{src.suffix}'

                # ===== 【修改】使用 vips 替代 convert =====
                if mode == 'fit':
                    # 适应：按比例缩放，不超出目标尺寸
                    scale = min(width / orig_width, height / orig_height)
                    cmd = ['vips', 'resize', str(src), str(temp_output), str(scale)]
                elif mode == 'fill':
                    # 填充：缩放后居中裁切
                    scale = max(width / orig_width, height / orig_height)
                    # 先缩放到覆盖目标尺寸
                    temp_scaled = src.parent / f'.{src.stem}_scaled{src.suffix}'
                    cmd_resize = ['vips', 'resize', str(src), str(temp_scaled), str(scale)]
                    subprocess.run(cmd_resize, capture_output=True, check=False)
                    # 然后裁切到目标尺寸
                    if temp_scaled.exists():
                        # 计算裁切位置（居中）
                        scaled_width, scaled_height = get_image_size(temp_scaled)
                        if scaled_width and scaled_height:
                            left = (scaled_width - width) // 2
                            top = (scaled_height - height) // 2
                            cmd_crop = ['vips', 'crop', str(temp_scaled), str(temp_output), 
                                       str(left), str(top), str(width), str(height)]
                            subprocess.run(cmd_crop, capture_output=True, check=False)
                        # 清理临时文件
                        if temp_scaled.exists():
                            temp_scaled.unlink()
                elif mode == 'stretch':
                    # 拉伸：直接缩放到目标尺寸（不保持比例）
                    # vips 的 resize 不支持直接拉伸到指定尺寸，分两步：先缩放到目标宽，再缩放到目标高
                    temp_stretch = src.parent / f'.{src.stem}_stretch{src.suffix}'
                    # 先缩放宽度
                    cmd_x = ['vips', 'resize', str(src), str(temp_stretch), str(width / orig_width)]
                    subprocess.run(cmd_x, capture_output=True, check=False)
                    # 再缩放高度
                    if temp_stretch.exists():
                        cmd_y = ['vips', 'resize', str(temp_stretch), str(temp_output), '1', '--vscale', str(height / orig_height)]
                        subprocess.run(cmd_y, capture_output=True, check=False)
                        if temp_stretch.exists():
                            temp_stretch.unlink()
                else:
                    # 默认适应
                    scale = min(width / orig_width, height / orig_height)
                    cmd = ['vips', 'resize', str(src), str(temp_output), str(scale)]

                # 执行命令（如果 mode 不是 fill 和 stretch 的特殊情况）
                if mode not in ('fill', 'stretch'):
                    subprocess.run(cmd, capture_output=True, check=False)

                # 如果是覆盖模式，替换原文件
                if overwrite:
                    if temp_output.exists():
                        os.remove(str(src))
                        temp_output.rename(src)
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    # 非覆盖模式，重命名临时文件到目标路径
                    if temp_output.exists():
                        temp_output.rename(output_path)

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
