# modules/move_copy.py - move_copy 函数

@ app.route('/api/move_copy', methods=['POST'])
@handle_errors('移动/复制失败')
@log_operation('移动/复制')
@with_memory_cleanup(app)
def move_copy():
    data = request.json
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400

    action = data.get('action', 'move')
    files = data.get('files', [])
    target_dir = data.get('target_dir', '')
    overwrite = data.get('overwrite', False)
    filters = data.get('filters', {})
    dry_run = data.get('dry_run', True)
    include_dirs = data.get('include_dirs', True)  # ===== 默认 True，允许操作目录 =====
    work_dir = WORK_DIR

    if not files:
        return jsonify({'error': '请选择要操作的文件或目录'}), 400

    if len(files) > MAX_FILES_PER_OPERATION:
        return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

    if not target_dir:
        return jsonify({'error': '目标目录不能为空'}), 400

    if target_dir.startswith('/'):
        target_path = Path(work_dir) / target_dir.lstrip('/')
    else:
        target_path = Path(work_dir) / target_dir
    target_path = target_path.resolve()

    if not is_safe_path(target_path, work_dir):
        return jsonify({'error': '目标目录不安全'}), 403

    results = []
    stats = {'processed': 0, 'moved': 0, 'copied': 0, 'skipped': 0, 'errors': 0}

    # ===== 【修改】收集所有要操作的项目（文件+目录） =====
    items_to_process = []
    for file_path_str in files:
        src = Path(work_dir) / file_path_str.lstrip('/')
        if src.exists():
            items_to_process.append({
                'path': file_path_str,
                'src': src,
                'is_dir': src.is_dir()
            })
        else:
            stats['skipped'] += 1
            results.append({'file': file_path_str, 'status': 'skip', 'reason': '文件不存在'})

    if not items_to_process:
        return jsonify({
            'results': results,
            'stats': stats,
            'dry_run': dry_run,
            'action': action,
            'target_dir': str(target_path)
        })

    # ===== 应用过滤（只对文件过滤，目录不过滤） =====
    if filters and any(filters.values()):
        filtered_paths = []
        for item in items_to_process:
            if item['is_dir']:
                # 目录直接保留
                filtered_paths.append(item['path'])
            else:
                # 文件应用过滤
                src_str = str(item['src'])
                if src_str in apply_file_filters([src_str], filters):
                    filtered_paths.append(item['path'])
        items_to_process = [item for item in items_to_process if item['path'] in filtered_paths]

    if not items_to_process:
        return jsonify({
            'results': [],
            'stats': {'filtered': 0, 'message': '没有文件匹配过滤条件'},
            'dry_run': dry_run
        })

    for i, item in enumerate(items_to_process):
        if i % BATCH_SIZE == 0:
            if hasattr(app, 'memory'):
                app.memory['cleanup']()
            time.sleep(SLEEP_BETWEEN_BATCH)

        src = item['src']
        dest = target_path / src.name

        # 处理重名
        if dest.exists() and not overwrite:
            if item['is_dir']:
                # 目录重名：加 _数字 后缀
                stem = src.stem
                counter = 1
                while True:
                    new_name = f'{stem}_{counter}'
                    new_dest = target_path / new_name
                    if not new_dest.exists():
                        dest = new_dest
                        break
                    counter += 1
            else:
                stem = src.stem
                ext = src.suffix
                counter = 1
                while True:
                    new_name = f'{stem}_{counter}{ext}'
                    new_dest = target_path / new_name
                    if not new_dest.exists():
                        dest = new_dest
                        break
                    counter += 1

        if dry_run:
            stats['processed'] += 1
            try:
                from_path = str(src.relative_to(work_dir))
            except ValueError:
                from_path = str(src)
            try:
                to_path = str(dest.relative_to(work_dir))
            except ValueError:
                to_path = str(dest)
            results.append({
                'file': src.name,
                'from': from_path,
                'to': to_path,
                'is_dir': item['is_dir'],
                'status': 'preview'
            })
            continue

        try:
            target_path.mkdir(parents=True, exist_ok=True)
            import shutil
            if action == 'move':
                if item['is_dir']:
                    shutil.move(str(src), str(dest))
                    stats['moved'] += 1
                else:
                    shutil.move(str(src), str(dest))
                    stats['moved'] += 1
            else:
                if item['is_dir']:
                    shutil.copytree(str(src), str(dest))
                    stats['copied'] += 1
                else:
                    shutil.copy2(str(src), str(dest))
                    stats['copied'] += 1
            stats['processed'] += 1
            try:
                to_path = str(dest.relative_to(work_dir))
            except ValueError:
                to_path = str(dest)
            results.append({
                'file': src.name,
                'to': to_path,
                'is_dir': item['is_dir'],
                'status': 'success'
            })
        except Exception as e:
            stats['errors'] += 1
            logger.error(f'操作失败: {src} -> {dest} - {e}')
            results.append({
                'file': src.name,
                'status': 'error',
                'reason': str(e),
                'is_dir': item['is_dir']
            })

    if hasattr(app, 'memory'):
        app.memory['cleanup']()

    return jsonify({
        'results': results,
        'stats': stats,
        'dry_run': dry_run,
        'action': action,
        'target_dir': str(target_path)
    })
