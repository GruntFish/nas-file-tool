# modules/media.py（修改部分）

# ===== 替换 resize 功能（使用 vips） =====
@app.route('/api/media/resize', methods=['POST'])
def resize_images():
    # ... 前面的代码不变 ...

            try:
                # ===== 【修改】使用 vips 替代 convert =====
                if overwrite:
                    temp_output = src.parent / f'.{src.stem}_temp{src.suffix}'
                    
                    # vips resize 命令
                    # vips resize input.jpg output.jpg width height --vscale
                    if mode == 'fit':
                        # 适应：按比例缩放，不超出目标尺寸
                        cmd = ['vips', 'resize', str(src), str(temp_output), 
                               str(width/src.stat().st_width), '--vscale', str(height/src.stat().st_height)]
                    elif mode == 'fill':
                        # 填充：居中裁切
                        # 先用 vips resize 缩放到覆盖目标尺寸，再裁切
                        scale = max(width/src.stat().st_width, height/src.stat().st_height)
                        temp_crop = src.parent / f'.{src.stem}_crop{src.suffix}'
                        cmd_resize = ['vips', 'resize', str(src), str(temp_crop), str(scale)]
                        subprocess.run(cmd_resize, capture_output=True, check=False)
                        # 然后裁切
                        cmd_crop = ['vips', 'crop', str(temp_crop), str(temp_output), 
                                    '0', '0', str(width), str(height)]
                        subprocess.run(cmd_crop, capture_output=True, check=False)
                        if temp_crop.exists():
                            temp_crop.unlink()
                    elif mode == 'stretch':
                        # 拉伸：先缩放到目标尺寸再拉伸
                        # vips 的 resize 不支持直接拉伸，使用 thumbnail 或 sequential
                        # 更简单：使用 vips thumbnail 方式
                        # 先缩放到目标比例
                        scale_x = width/src.stat().st_width
                        scale_y = height/src.stat().st_height
                        # 用两次 resize 近似实现
                        # 实际可以用 vips affine
                        cmd = ['vips', 'resize', str(src), str(temp_output), str(scale_x)]
                        subprocess.run(cmd, capture_output=True, check=False)
                        # 然后调用 vips 再次 resize Y 轴
                        cmd2 = ['vips', 'resize', str(temp_output), str(temp_output), '1', '--vscale', str(scale_y)]
                        subprocess.run(cmd2, capture_output=True, check=False)
                    else:
                        # 默认适应
                        cmd = ['vips', 'resize', str(src), str(temp_output), 
                               str(width/src.stat().st_width), '--vscale', str(height/src.stat().st_height)]
                        subprocess.run(cmd, capture_output=True, check=False)
                    
                    if temp_output.exists():
                        os.remove(str(src))
                        temp_output.rename(src)
                    temp_backup = src.parent / f'.{src.name}.backup'
                    if temp_backup.exists():
                        temp_backup.unlink()
                else:
                    # 不覆盖：生成新文件
                    if mode == 'fit':
                        cmd = ['vips', 'resize', str(src), str(output_path), 
                               str(width/src.stat().st_width), '--vscale', str(height/src.stat().st_height)]
                    elif mode == 'fill':
                        scale = max(width/src.stat().st_width, height/src.stat().st_height)
                        temp_crop = src.parent / f'.{src.stem}_crop{src.suffix}'
                        cmd_resize = ['vips', 'resize', str(src), str(temp_crop), str(scale)]
                        subprocess.run(cmd_resize, capture_output=True, check=False)
                        cmd_crop = ['vips', 'crop', str(temp_crop), str(output_path), 
                                    '0', '0', str(width), str(height)]
                        subprocess.run(cmd_crop, capture_output=True, check=False)
                        if temp_crop.exists():
                            temp_crop.unlink()
                    elif mode == 'stretch':
                        scale_x = width/src.stat().st_width
                        scale_y = height/src.stat().st_height
                        cmd = ['vips', 'resize', str(src), str(output_path), str(scale_x)]
                        subprocess.run(cmd, capture_output=True, check=False)
                        cmd2 = ['vips', 'resize', str(output_path), str(output_path), '1', '--vscale', str(scale_y)]
                        subprocess.run(cmd2, capture_output=True, check=False)
                    else:
                        cmd = ['vips', 'resize', str(src), str(output_path), 
                               str(width/src.stat().st_width), '--vscale', str(height/src.stat().st_height)]
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
