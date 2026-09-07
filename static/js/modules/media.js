// static/js/modules/media.js
const MediaModule = {
    name: 'media',

    init() {
        document.getElementById('mediaCompressBtn').addEventListener('click', () => this.compress());
        this.updateCount();
        document.addEventListener('selectionChanged', () => { this.updateCount(); });
        // ===== 监听模块切换，清除压缩预览数据 =====
        document.addEventListener('moduleChanged', () => {
            if (ModuleRegistry.currentModule !== 'media') {
                window.compressPreview = {};
                if (typeof renderFiles === 'function') {
                    renderFiles(window.fileList);
                }
            }
        });
    },

    destroy() {
        closeModal();
        selectedFiles.clear();
        updateSelectedInfo();
        // ===== 清除压缩预览数据 =====
        window.compressPreview = {};
        if (typeof renderFiles === 'function' && window.fileList) {
            renderFiles(window.fileList);
        }
    },

    updateCount() {
        const count = selectedFiles.size;
        const el = document.getElementById('mediaSelectedCount');
        if (el) el.textContent = count;
    },

    getImageFiles() {
        const exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif', '.ico', '.svg'];
        const selected = Array.from(selectedFiles);

        if (selected.length === 0) {
            return [];
        }

        const fileList = window.fileList || [];
        const imageFiles = [];

        selected.forEach(path => {
            const normalizedPath = path.startsWith('/') ? path : '/' + path;
            const normalizedPathNoSlash = path.replace(/^\//, '');

            let fileObj = fileList.find(f => f.path === path);
            if (!fileObj) {
                fileObj = fileList.find(f => f.path === normalizedPath);
            }
            if (!fileObj) {
                fileObj = fileList.find(f => f.path === normalizedPathNoSlash);
            }
            if (!fileObj) {
                const fileName = path.split('/').pop();
                fileObj = fileList.find(f => f.name === fileName && !f.is_dir);
            }

            if (fileObj && !fileObj.is_dir) {
                const ext = fileObj.name.substring(fileObj.name.lastIndexOf('.')).toLowerCase();
                if (exts.includes(ext)) {
                    imageFiles.push(path);
                }
            }
        });

        return imageFiles;
    },

    compress() {
        const files = this.getImageFiles();
        if (files.length === 0) {
            showLog('⚠️ 请先勾选图片文件（支持 JPG、PNG、GIF、BMP、WebP、TIFF 等格式）', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal" style="max-width:450px;">
            <h2>🖼️ 图片压缩</h2>
            <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                已选 <strong style="color:#e4e6eb;">${files.length}</strong> 张图片
                <div style="color:#4a4e62;font-size:10px;margin-top:2px;">💡 下方显示的是 <strong style="color:#f0c94d;">预估</strong> 压缩后大小，实际以执行为准</div>
            </div>
            <div class="form-group">
                <label>压缩质量 (1-100)</label>
                <input type="number" id="mediaQuality" value="85" min="1" max="100">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">值越高画质越好，文件越大</div>
            </div>
            <div style="color:#f6ad55;font-size:12px;margin-bottom:6px;padding:4px 8px;background:#1f1a1a;border-radius:4px;border:1px solid #3d2d1a;">
                <input type="checkbox" id="mediaOverwrite"> ⚠️ 覆盖原图（压缩后直接替换原文件，不可恢复！）
                <div style="color:#8b8fa3;font-size:10px;margin-top:2px;padding-left:20px;">勾选后原图将被压缩后的图片覆盖，建议先备份</div>
            </div>
            <div id="mediaPreviewArea" style="margin-top:8px;">
                <div style="color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:4px;">📊 预估压缩结果</div>
                <div class="preview-list" id="mediaPreviewList" style="max-height:200px;background:#14171f;border-radius:6px;padding:4px 8px;border:1px solid #2d313e;"></div>
                <div style="color:#68d391;font-size:12px;margin-top:4px;" id="mediaStats"></div>
            </div>
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="mediaCompressConfirm">✅ 执行压缩</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#mediaCompressConfirm').addEventListener('click', () => this.doCompress(files));
        overlay.querySelector('#mediaQuality').addEventListener('input', () => this.previewCompress(files));
        overlay.querySelector('#mediaOverwrite').addEventListener('change', () => this.previewCompress(files));
        setTimeout(() => this.previewCompress(files), 100);
    },

    // ===== 预览：显示预估压缩结果（只显示在弹窗中） =====
    async previewCompress(files) {
        if (!files || files.length === 0) {
            document.getElementById('mediaPreviewList').innerHTML = '<div style="color:#4a4e62;text-align:center;padding:8px;">没有图片</div>';
            document.getElementById('mediaStats').textContent = '';
            return;
        }

        const quality = parseInt(document.getElementById('mediaQuality').value) || 85;
        const overwrite = document.getElementById('mediaOverwrite')?.checked || false;

        try {
            const result = await apiCall('/api/media/compress', {
                files: files,
                quality: quality,
                dry_run: true,
                overwrite: overwrite
            });

            if (result.error) {
                showLog('❌ ' + result.error, 'error');
                return;
            }

            const previewList = document.getElementById('mediaPreviewList');
            const stats = document.getElementById('mediaStats');

            previewList.innerHTML = '';
            if (result.results && result.results.length > 0) {
                let totalSaved = 0;
                result.results.forEach(r => {
                    if (r.status === 'preview') {
                        const div = document.createElement('div');
                        const saved = r.estimated_ratio || 0;
                        const overwriteTag = r.overwrite ? ' [覆盖原图]' : '';

                        const originalSize = formatSize(r.original_size);
                        const estimatedSize = formatSize(r.estimated_size);

                        div.style.cssText = 'color:#b5b9c9;padding:3px 0;font-size:12px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1f222c;';
                        div.innerHTML = `
                            <span style="color:#b5b9c9;">📄 ${r.file}</span>
                            <span style="color:#8b8fa3;font-size:11px;">
                                ${originalSize} → <span style="color:#f0c94d;">${estimatedSize}</span>
                                <span style="color:#68d391;font-size:10px;margin-left:4px;">⬇ ${saved.toFixed(1)}%</span>
                                ${overwriteTag}
                            </span>
                        `;
                        previewList.appendChild(div);
                        totalSaved += saved;
                    }
                });
                const avg = result.results.length > 0 ? (totalSaved / result.results.length).toFixed(1) : 0;
                stats.textContent = '📊 共 ' + result.results.length + ' 张图片，平均预计节省 ' + avg + '%' + (overwrite ? ' ⚠️ 将覆盖原图' : '');
                stats.style.color = '#68d391';
            } else {
                previewList.innerHTML = '<div style="color:#4a4e62;text-align:center;padding:8px;">没有图片需要压缩</div>';
                stats.textContent = '';
            }

        } catch (e) {
            console.error('预览失败:', e);
        }
    },

    // ===== 执行压缩：真实压缩，完成后更新文件列表 =====
    async doCompress(files) {
        if (!files || files.length === 0) {
            showLog('⚠️ 没有可压缩的图片文件', 'warning');
            return;
        }

        const quality = parseInt(document.getElementById('mediaQuality').value) || 85;
        const overwrite = document.getElementById('mediaOverwrite')?.checked || false;

        if (overwrite) {
            if (!confirm('⚠️ 警告：你选择了「覆盖原图」模式，压缩后将直接替换原始文件，此操作不可恢复！\n\n确定要继续吗？')) {
                return;
            }
        }

        closeModal();
        clearLog();
        showLog('⏳ 开始压缩 ' + files.length + ' 张图片...' + (overwrite ? ' (覆盖原图模式)' : ''), 'info');

        try {
            await OperationManager.execute({
                title: `🖼️ 正在压缩 ${files.length} 张图片...`,
                completeMessage: `✅ 图片压缩完成`,
                execute: async (progress) => {
                    progress.setTotal(files.length);
                    const result = await apiCall('/api/media/compress', {
                        files: files,
                        quality: quality,
                        dry_run: false,
                        overwrite: overwrite
                    });

                    if (result.error) {
                        throw new Error(result.error);
                    }

                    // ===== 构建压缩结果数据，写入 window.compressPreview =====
                    const compressMap = {};

                    if (result.results) {
                        const success = result.results.filter(r => r.status === 'success');
                        let processed = 0;
                        success.forEach(r => {
                            const saved = r.ratio || 0;
                            const tag = r.overwrite ? ' [覆盖原图]' : '';
                            showLog('✅ ' + r.file + ' → ' + r.output + tag + ' (节省 ' + saved.toFixed(1) + '%)', 'success');
                            processed++;
                            progress.update(processed, `✅ ${r.file} 已压缩 (${processed}/${files.length})`);
                            // ===== 写入 compressPreview，用于文件列表显示 =====
                            compressMap[r.file] = {
                                original: formatSize(r.original_size),
                                new: formatSize(r.new_size),
                                ratio: saved,
                                isPreview: false,
                                output: r.output,
                                isCompressed: true  // 标记已压缩
                            };
                        });
                        const msg = result.stats.compressed + ' 张图片已压缩，节省 ' + formatSize(result.stats.saved_bytes || 0);
                        showLog('✅ ' + msg + (overwrite ? ' (已覆盖原图)' : ''), 'success');
                    }

                    // ===== 更新文件列表显示压缩结果 =====
                    window.compressPreview = compressMap;
                    if (typeof renderFiles === 'function') {
                        renderFiles(window.fileList);
                    }

                    await loadFiles(currentPath);
                }
            });
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(MediaModule);
}
