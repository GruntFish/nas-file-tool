# modules/media.py
from flask import jsonify, request
from pathlib import Path
import subprocess
import time
import shutil
import os

from core.config import WORK_DIR, MAX_FILES_PER_OPERATION, BATCH_SIZE
from core.decorators import with_memory_cleanup, log_operation, handle_errors
from core.logger import get_logger

logger = get_logger(__name__)


def register(app):
    """注册媒体处理路由"""

    IMAGE_EXTS = {'.jpg', '.jpeg', '.png'}

    def check_tool(tool_name):
        try:
            subprocess.run([tool_name, '--version'], capture_output=True, timeout=5)
            return True
        except:
            return False

    @app.route('/api/media/compress', methods=['POST'])
    @handle_errors('压缩失败')
    @log_operation('图片压缩')
    @with_memory_cleanup(app)
    def compress_images():
        data = request.json
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        files = data.get('files', [])
        quality = data.get('quality', 85)
        dry_run = data.get('dry_run', True)
        overwrite = data.get('overwrite', False)
        work_dir = WORK_DIR

        if not files:
            return jsonify({'error': '请选择要压缩的图片'}), 400

        if len(files) > MAX_FILES_PER_OPERATION:
            return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

        if not dry_run:
            has_jpeg = False
            has_png = False
            for f in files:
                src = Path(work_dir) / f.lstrip('/')
                if src.suffix.lower() in ('.jpg', '.jpeg'):
                    has_jpeg = True
                elif src.suffix.lower() == '.png':
                    has_png = True
            if has_jpeg and not check_tool('jpegoptim'):
                return jsonify({'error': '缺少 jpegoptim 工具'}), 503
            if has_png and not check_tool('optipng'):
                return jsonify({'error': '缺少 optipng 工具'}), 503

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

            ext = src.suffix.lower()
            if ext not in IMAGE_EXTS:
                stats['skipped'] += 1
                results.append({'file': src.name, 'status': 'skip', 'reason': '不支持的格式，仅支持 JPG 和 PNG'})
                continue

            original_size = src.stat().st_size

            if overwrite:
                output_path = src
                temp_backup = src.parent / f'.{src.name}.backup'
                try:
                    shutil.copy2(str(src), str(temp_backup))
                except:
                    pass
            else:
                output_name = src.stem + '_compressed' + src.suffix
                output_path = src.parent / output_name
                if output_path.exists():
                    output_name = src.stem + f'_compressed_{int(time.time())}' + src.suffix
                    output_path = src.parent / output_name

            if dry_run:
                estimated_ratio = 0.6 if quality < 80 else 0.8
                if ext == '.png':
                    estimated_ratio = 0.7 if quality < 80 else 0.9
                estimated_size = int(original_size * estimated_ratio)
                stats['processed'] += 1
                results.append({
                    'file': src.name,
                    'output': output_path.name,
                    'original_size': original_size,
                    'estimated_size': estimated_size,
                    'estimated_ratio': round((1 - estimated_size/original_size) * 100, 1) if original_size > 0 else 0,
                    'status': 'preview',
                    'overwrite': overwrite
                })
                continue

            try:
                if overwrite:
                    if ext in ('.jpg', '.jpeg'):
                        subprocess.run(['jpegoptim', '--max=' + str(quality), str(src)], capture_output=True, check=False)
                    elif ext == '.png':
                        subprocess.run(['optipng', '-o2', str(src)], capture_output=True, check=False)
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    shutil.copy2(str(src), str(output_path))
                    if ext in ('.jpg', '.jpeg'):
                        subprocess.run(['jpegoptim', '--max=' + str(quality), str(output_path)], capture_output=True, check=False)
                    elif ext == '.png':
                        subprocess.run(['optipng', '-o2', str(output_path)], capture_output=True, check=False)

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
                logger.error(f'压缩失败: {src} - {e}')
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
            'overwrite': overwrite
        })
