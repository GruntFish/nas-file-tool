#!/usr/bin/env python3
import os
import sys
import hashlib
import subprocess
import argparse
from pathlib import Path

def deduplicate_files(directory, delete=False):
    seen = {}
    removed = 0
    for file_path in Path(directory).rglob('*'):
        if not file_path.is_file():
            continue
        with open(file_path, 'rb') as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        if md5 in seen:
            if delete:
                os.remove(file_path)
                removed += 1
                print(f"🗑️ 删除重复: {file_path}")
            else:
                print(f"📋 重复文件: {file_path} (与 {seen[md5].name} 相同)")
        else:
            seen[md5] = file_path
    if not delete:
        print(f"✅ 查找完成，发现 {len(seen)} 个唯一文件")
    else:
        print(f"✅ 去重完成，共删除 {removed} 个重复文件")

def compress_images(directory, quality=80, output_format='original'):
    extensions = ('.jpg', '.jpeg', '.png')
    compressed = 0
    for file_path in Path(directory).rglob('*'):
        if not file_path.is_file() or file_path.suffix.lower() not in extensions:
            continue
        ext = file_path.suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            if output_format == 'webp':
                cmd = ['cwebp', '-q', str(quality), str(file_path), '-o', str(file_path.with_suffix('.webp'))]
            else:
                cmd = ['jpegoptim', '--max=' + str(quality), str(file_path)]
        elif ext == '.png':
            if output_format == 'webp':
                cmd = ['cwebp', '-q', str(quality), str(file_path), '-o', str(file_path.with_suffix('.webp'))]
            else:
                cmd = ['optipng', '-o2', str(file_path)]
        else:
            continue
        subprocess.run(cmd, capture_output=True)
        compressed += 1
        print(f"🖼️ 压缩: {file_path}")
    print(f"✅ 图片压缩完成，共处理 {compressed} 个文件")

def batch_rename(directory, pattern, replacement):
    renamed = 0
    for file_path in Path(directory).rglob('*'):
        if not file_path.is_file():
            continue
        new_name = file_path.name.replace(pattern, replacement)
        if new_name != file_path.name:
            new_path = file_path.with_name(new_name)
            os.rename(file_path, new_path)
            renamed += 1
            print(f"✏️ 重命名: {file_path.name} → {new_name}")
    print(f"✅ 重命名完成，共修改 {renamed} 个文件")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['rename', 'dedup', 'compress'])
    parser.add_argument('--dir', default='/data')
    parser.add_argument('--pattern')
    parser.add_argument('--replacement')
    parser.add_argument('--delete', action='store_true')
    parser.add_argument('--quality', type=int, default=80)
    parser.add_argument('--format', default='original')
    args = parser.parse_args()

    if args.action == 'rename':
        batch_rename(args.dir, args.pattern, args.replacement)
    elif args.action == 'dedup':
        deduplicate_files(args.dir, args.delete)
    elif args.action == 'compress':
        compress_images(args.dir, args.quality, args.format)