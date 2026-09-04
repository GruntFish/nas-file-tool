// static/js/modules/media.js
const MediaModule = {
    name: 'media',

    init() {
        document.getElementById('mediaCompressBtn').addEventListener('click', () => this.compress());
        this.updateCount();
        document.addEventListener('selectionChanged', () => { this.updateCount(); });
    },

    destroy() {
        closeModal();
        selectedFiles.clear();
        updateSelectedInfo();
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
        const exts = ['.jpg', '.jpeg', '.png'];
        return Array.from(selectedFiles).filter(f => {
            const ext = f.substring(f.lastIndexOf('.')).toLowerCase();
            return exts.includes(ext);
        });
    },

    compress() {
        const files = this.getImageFiles();
        if (files.length === 0) {
            showLog('⚠️ 请选择 JPG 或 PNG 图片文件', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal" style="max-width:450px;">
            <h2>🖼️ 图片压缩</h2>
            <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                已选 <strong style="color:#e4e6eb;">${files.length}</strong> 张图片
            </div>
            <div class="form-group">
                <label>压缩质量 (1-100)</label>
                <input type="number" id="mediaQuality" value="85" min="1" max="100">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">值越高画质越好，文件越大</div>
            </div>
            <div style="color:#8b8fa3;font-size:12px;margin-bottom:6px;">
                <input type="checkbox" id="mediaDryRun" checked> 预览模式（不实际压缩）
            </div>
            <div style="color:#f6ad55;font-size:12px;margin-bottom:6px;padding:4px 8px;background:#1f1a1a;border-radius:4px;border:1px solid #3d2d1a;">
                <input type="checkbox" id="mediaOverwrite"> ⚠️ 覆盖原图（压缩后直接替换原文件，不可恢复！）
                <div style="color:#8b8fa3;font-size:10px;margin-top:2px;padding-left:20px;">勾选后原图将被压缩后的图片覆盖，建议先备份</div>
            </div>
            <div id="mediaPreviewArea" style="display:none;margin-top:8px;">
                <div class="preview-list" id="mediaPreviewList" style="max-height:200px;"></div>
                <div style="color:#68d391;font-size:12px;margin-top:4px;" id="mediaStats"></div>
            </div>
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="mediaCompressConfirm">执行压缩</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#mediaCompressConfirm').addEventListener('click', () => this.doCompress(files));
        overlay.querySelector('#mediaQuality').addEventListener('input', () => this.previewCompress(files));
        overlay.querySelector('#mediaDryRun').addEventListener('change', () => this.previewCompress(files));
        overlay.querySelector('#mediaOverwrite').addEventListener('change', () => this.previewCompress(files));
        setTimeout(() => this.previewCompress(files), 100);
    },

    async previewCompress(files) {
        const quality = parseInt(document.getElementById('mediaQuality').value) || 85;
        const overwrite = document.getElementById('mediaOverwrite')?.checked || false;

        try {
            const result = await apiCall('/api/media/compress', {
                files: files,
                quality: quality,
                dry_run: true,
                overwrite: overwrite
            });

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }

            const previewList = document.getElementById('mediaPreviewList');
            const stats = document.getElementById('mediaStats');
            const previewArea = document.getElementById('mediaPreviewArea');

            previewList.innerHTML = '';
            if (result.results && result.results.length > 0) {
                let totalSaved = 0;
                result.results.forEach(r => {
                    if (r.status === 'preview') {
                        const div = document.createElement('div');
                        const saved = r.estimated_ratio || 0;
                        const overwriteTag = r.overwrite ? ' [覆盖原图]' : '';
                        div.style.cssText = 'color:#68d391;padding:2px 0;font-size:12px;';
                        div.textContent = '📄 ' + r.file + ' → ' + r.output + overwriteTag + ' (预计节省 ' + saved.toFixed(1) + '%)';
                        previewList.appendChild(div);
                        totalSaved += saved;
                    }
                });
                const avg = result.results.length > 0 ? (totalSaved / result.results.length).toFixed(1) : 0;
                stats.textContent = '📊 共 ' + result.results.length + ' 张图片，平均预计节省 ' + avg + '%' + (overwrite ? ' ⚠️ 将覆盖原图' : '');
                previewArea.style.display = 'block';
            } else {
                previewList.innerHTML = '<div style="color:#4a4e62;">没有图片需要压缩</div>';
                previewArea.style.display = 'block';
            }
        } catch (e) {}
    },

    async doCompress(files) {
        const quality = parseInt(document.getElementById('mediaQuality').value) || 85;
        const dryRun = document.getElementById('mediaDryRun').checked;
        const overwrite = document.getElementById('mediaOverwrite')?.checked || false;

        if (overwrite && !dryRun) {
            if (!confirm('⚠️ 警告：你选择了「覆盖原图」模式，压缩后将直接替换原始文件，此操作不可恢复！\n\n确定要继续吗？')) {
                return;
            }
        }

        closeModal();
        clearLog();
        showLog('⏳ 开始压缩图片...' + (overwrite ? ' (覆盖原图模式)' : ''), 'info');

        try {
            await OperationManager.execute({
                title: `🖼️ 正在压缩 ${files.length} 张图片...`,
                completeMessage: `✅ 图片压缩完成`,
                execute: async (progress) => {
                    progress.setTotal(files.length);
                    const result = await apiCall('/api/media/compress', {
                        files: files,
                        quality: quality,
                        dry_run: dryRun,
                        overwrite: overwrite
                    });

                    if (result.error) {
                        throw new Error(result.error);
                    }

                    if (result.results) {
                        if (dryRun) {
                            result.results.forEach(r => {
                                if (r.status === 'preview') {
                                    const tag = r.overwrite ? ' [覆盖]' : '';
                                    showLog('📋 ' + r.file + ' → ' + r.output + tag + ' (预计节省 ' + (r.estimated_ratio || 0).toFixed(1) + '%)', 'info');
                                }
                            });
                            showLog('📊 预览完成，共 ' + result.results.length + ' 张图片', 'info');
                        } else {
                            const success = result.results.filter(r => r.status === 'success');
                            success.forEach(r => {
                                const saved = r.ratio || 0;
                                const tag = r.overwrite ? ' [覆盖原图]' : '';
                                showLog('✅ ' + r.file + ' → ' + r.output + tag + ' (节省 ' + saved.toFixed(1) + '%)', 'success');
                            });
                            const msg = result.stats.compressed + ' 张图片已压缩，节省 ' + formatSize(result.stats.saved_bytes || 0);
                            showLog('✅ ' + msg + (overwrite ? ' (已覆盖原图)' : ''), 'success');
                        }
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
