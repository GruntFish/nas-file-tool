# modules/media.py
from flask import jsonify, request
from pathlib import Path
import subprocess
import time
import hashlib

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE

def register(app):
    """注册媒体处理路由"""

    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}

    @app.route('/api/media/compress', methods=['POST'])
    def compress_images():
        data = request.json
        files = data.get('files', [])
        quality = data.get('quality', 85)
        format_type = data.get('format', 'original')
        dry_run = data.get('dry_run', True)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要压缩的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

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
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

            output_ext = '.' + format_type if format_type != 'original' else src.suffix
            output_name = src.stem + '_compressed' + output_ext
            output_path = src.parent / output_name

            if dry_run or output_path.exists():
                output_name = src.stem + f'_compressed_{int(time.time())}' + output_ext
                output_path = src.parent / output_name

            original_size = src.stat().st_size

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
                    'status': 'preview'
                })
                continue

            try:
                ext = src.suffix.lower()
                if ext in ('.jpg', '.jpeg'):
                    import shutil
                    shutil.copy2(str(src), str(output_path))
                    subprocess.run(['jpegoptim', '--max=' + str(quality), str(output_path)], capture_output=True)
                elif ext == '.png':
                    import shutil
                    shutil.copy2(str(src), str(output_path))
                    subprocess.run(['optipng', '-o2', str(output_path)], capture_output=True)
                else:
                    cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(output_path)]
                    subprocess.run(cmd, capture_output=True)

                new_size = output_path.stat().st_size if output_path.exists() else src.stat().st_size
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
                    'status': 'success'
                })
            except Exception as e:
                stats['errors'] += 1
                results.append({
                    'file': src.name,
                    'status': 'error',
                    'reason': str(e)
                })

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'quality': quality,
            'format': format_type
        })

    @app.route('/api/media/convert', methods=['POST'])
    def convert_images():
        data = request.json
        files = data.get('files', [])
        target_format = data.get('target_format', 'webp')
        quality = data.get('quality', 85)
        dry_run = data.get('dry_run', True)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要转换的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

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
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

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
                    'status': 'preview'
                })
                continue

            try:
                if target_format == 'webp':
                    cmd = ['cwebp', '-q', str(quality), str(src), '-o', str(output_path)]
                elif target_format in ('jpg', 'jpeg'):
                    cmd = ['convert', str(src), '-quality', str(quality), str(output_path)]
                elif target_format == 'png':
                    cmd = ['convert', str(src), str(output_path)]
                else:
                    return jsonify({'error': f'不支持的格式: {target_format}'}), 400

                subprocess.run(cmd, capture_output=True)
                if output_path.exists():
                    stats['converted'] += 1
                    stats['processed'] += 1
                    results.append({
                        'file': src.name,
                        'output': output_path.name,
                        'from': src.suffix.lower(),
                        'to': target_format,
                        'size': output_path.stat().st_size,
                        'status': 'success'
                    })
                else:
                    stats['errors'] += 1
                    results.append({'file': src.name, 'status': 'error', 'reason': '转换失败'})
            except Exception as e:
                stats['errors'] += 1
                results.append({'file': src.name, 'status': 'error', 'reason': str(e)})

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'target_format': target_format,
            'quality': quality
        })

    @app.route('/api/media/resize', methods=['POST'])
    def resize_images():
        data = request.json
        files = data.get('files', [])
        width = data.get('width', 1920)
        height = data.get('height', 1080)
        mode = data.get('mode', 'fit')
        dry_run = data.get('dry_run', True)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要调整的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

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
                continue

            if src.suffix.lower() not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不是图片'})
                continue

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
                    'status': 'preview'
                })
                continue

            try:
                if mode == 'fit':
                    resize_arg = f'{width}x{height}>'
                elif mode == 'fill':
                    resize_arg = f'{width}x{height}^'
                elif mode == 'stretch':
                    resize_arg = f'{width}x{height}!'
                else:
                    resize_arg = f'{width}x{height}'

                cmd = ['convert', str(src), '-resize', resize_arg, str(output_path)]
                subprocess.run(cmd, capture_output=True)

                if output_path.exists():
                    stats['resized'] += 1
                    stats['processed'] += 1
                    results.append({
                        'file': src.name,
                        'output': output_path.name,
                        'original_size': src.stat().st_size,
                        'new_size': output_path.stat().st_size,
                        'status': 'success'
                    })
                else:
                    stats['errors'] += 1
                    results.append({'file': src.name, 'status': 'error', 'reason': '调整失败'})
            except Exception as e:
                stats['errors'] += 1
                results.append({'file': src.name, 'status': 'error', 'reason': str(e)})

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'width': width,
            'height': height,
            'mode': mode
        })
