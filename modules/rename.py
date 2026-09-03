# modules/rename.py

@ app.route('/api/execute', methods=['POST'])
def execute():
    data = request.json
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400

    action = data.get('action')
    files = data.get('files', [])
    work_dir = WORK_DIR

    # ===== 【新增】打印调试日志 =====
    print(f'[重命名] action: {action}, 文件数量: {len(files)}')
    if files:
        print(f'[重命名] 第一个文件: {files[0]}')

    # 检查内存
    if hasattr(app, 'memory'):
        mem_check = app.memory['check_limit']()
        if mem_check['exceeded']:
            return jsonify({'error': '内存使用超过限制，请稍后再试'}), 503

    logs = []
    stats = {'processed': 0, 'message': '成功'}
    history = []

    if len(files) > MAX_FILES_PER_OPERATION:
        return jsonify({'error': f'一次最多处理 {MAX_FILES_PER_OPERATION} 个文件'}), 400

    try:
        for i, item in enumerate(files):
            if i % BATCH_SIZE == 0:
                if hasattr(app, 'memory'):
                    app.memory['cleanup']()
                time.sleep(SLEEP_BETWEEN_BATCH)

            old_path = Path(work_dir) / item['old_path'].lstrip('/')
            new_path = Path(work_dir) / item['new_path'].lstrip('/')

            # ===== 【新增】打印每个文件的路径 =====
            print(f'[重命名] 检查: {old_path} -> {new_path}')

            if old_path.exists() and not new_path.exists():
                old_path.rename(new_path)
                logs.append({
                    'text': f'✏️ 重命名: {item["old_name"]} → {item["new_name"]}',
                    'type': 'success'
                })
                history.append({
                    'old_path': str(old_path),
                    'new_path': str(new_path),
                    'old_name': item['old_name']
                })
                stats['processed'] += 1
            else:
                # ===== 【新增】记录跳过的原因 =====
                if not old_path.exists():
                    logs.append({
                        'text': f'⚠️ 文件不存在: {item["old_name"]}',
                        'type': 'warning'
                    })
                elif new_path.exists():
                    logs.append({
                        'text': f'⚠️ 目标文件已存在: {item["new_name"]}',
                        'type': 'warning'
                    })

        if hasattr(app, 'memory'):
            app.memory['cleanup']()

        stats['message'] = f'成功处理 {stats["processed"]} 个文件'
        print(f'[重命名] 完成: {stats}')

        # ===== 【新增】如果没有任何文件被处理，返回明确信息 =====
        if stats['processed'] == 0:
            return jsonify({
                'logs': logs if logs else [{'text': '没有文件被重命名，请检查文件是否存在', 'type': 'warning'}],
                'stats': stats,
                'history': history,
                'warning': '没有文件被处理'
            })

        return jsonify({'logs': logs, 'stats': stats, 'history': history})

    except Exception as e:
        import traceback
        print(f'[重命名] 异常: {traceback.format_exc()}')
        if hasattr(app, 'memory'):
            app.memory['cleanup']()
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
