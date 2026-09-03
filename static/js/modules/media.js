// static/js/modules/media.js

const MediaModule = {
    name: 'media',

    init() {
        document.getElementById('mediaCompressBtn').addEventListener('click', () => this.compress());
        document.getElementById('mediaConvertBtn').addEventListener('click', () => this.convert());
        document.getElementById('mediaResizeBtn').addEventListener('click', () => this.resize());
        this.updateCount();
    },

    onSelectChange(selected) {
        this.updateCount();
    },

    updateCount() {
        const count = selectedFiles.size;
        const el = document.getElementById('mediaSelectedCount');
        if (el) el.textContent = count;
    },

    getImageFiles() {
        const exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'];
        return Array.from(selectedFiles).filter(f => {
            const ext = f.substring(f.lastIndexOf('.')).toLowerCase();
            return exts.includes(ext);
        });
    },

    compress() {
        const files = this.getImageFiles();
        if (files.length === 0) {
            showLog('⚠️ 请选择图片文件', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal-overlay show">
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
                <div class="form-group">
                    <label>输出格式</label>
                    <select id="mediaFormat">
                        <option value="original">保持原格式</option>
                        <option value="webp">WebP（推荐）</option>
                        <option value="jpg">JPEG</option>
                        <option value="png">PNG</option>
                    </select>
                </div>
                <div style="color:#8b8fa3;font-size:12px;margin-bottom:8px;">
                    <input type="checkbox" id="mediaDryRun" checked> 预览模式（不实际压缩）
                </div>
                <div id="mediaPreviewArea" style="display:none;margin-top:8px;">
                    <div class="preview-list" id="mediaPreviewList" style="max-height:200px;"></div>
                    <div style="color:#68d391;font-size:12px;margin-top:4px;" id="mediaStats"></div>
                </div>
                <div class="btn-row">
                    <button class="btn-cancel" onclick="closeModal()">取消</button>
                    <button class="btn-confirm" id="mediaCompressConfirm">执行压缩</button>
                </div>
            </div>
        </div>
        `;

        openModal(modalHtml);
        document.getElementById('mediaCompressConfirm').addEventListener('click', () => this.doCompress(files));
        document.getElementById('mediaQuality').addEventListener('input', () => this.previewCompress(files));
        document.getElementById('mediaFormat').addEventListener('change', () => this.previewCompress(files));
        document.getElementById('mediaDryRun').addEventListener('change', () => this.previewCompress(files));
        setTimeout(() => this.previewCompress(files), 100);
    },

    async previewCompress(files) {
        const quality = parseInt(document.getElementById('mediaQuality').value) || 85;
        const format = document.getElementById('mediaFormat').value;

        try {
            const result = await apiCall('/api/media/compress', {
                files: files,
                quality: quality,
                format: format,
                dry_run: true
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
                        div.style.cssText = 'color:#68d391;padding:2px 0;font-size:12px;';
                        div.textContent = '📄 ' + r.file + ' → ' + r.output + ' (预计节省 ' + saved.toFixed(1) +
                            '%)';
                        previewList.appendChild(div);
                        totalSaved += saved;
                    }
                });
                const avg = result.results.length > 0 ? (totalSaved / result.results.length).toFixed(1) : 0;
                stats.textContent = '📊 共 ' + result.results.length + ' 张图片，平均预计节省 ' + avg + '%';
                previewArea.style.display = 'block';
            } else {
                previewList.innerHTML = '<div style="color:#4a4e62;">没有图片需要压缩</div>';
                previewArea.style.display = 'block';
            }
        } catch (e) {}
    },

    async doCompress(files) {
        const quality = parseInt(document.getElementById('mediaQuality').value) || 85;
        const format = document.getElementById('mediaFormat').value;
        const dryRun = document.getElementById('mediaDryRun').checked;

        closeModal();
        clearLog();
        showLog('⏳ 开始压缩图片...', 'info');

        try {
            const result = await apiCall('/api/media/compress', {
                files: files,
                quality: quality,
                format: format,
                dry_run: dryRun
            });

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }

            if (result.results) {
                if (dryRun) {
                    result.results.forEach(r => {
                        if (r.status === 'preview') {
                            showLog('📋 ' + r.file + ' → ' + r.output + ' (预计节省 ' + (r.estimated_ratio || 0)
                                .toFixed(1) + '%)', 'info');
                        }
                    });
                    showLog('📊 预览完成，共 ' + result.results.length + ' 张图片', 'info');
                } else {
                    const success = result.results.filter(r => r.status === 'success');
                    success.forEach(r => {
                        const saved = r.ratio || 0;
                        showLog('✅ ' + r.file + ' → ' + r.output + ' (节省 ' + saved.toFixed(1) + '%)',
                        'success');
                    });
                    showLog('✅ ' + result.stats.compressed + ' 张图片已压缩，节省 ' + formatSize(result.stats
                        .saved_bytes || 0), 'success');
                }
            }

            await loadFiles(currentPath);
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    },

    convert() {
        const files = this.getImageFiles();
        if (files.length === 0) {
            showLog('⚠️ 请选择图片文件', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal-overlay show">
            <div class="modal" style="max-width:450px;">
                <h2>🔄 格式转换</h2>
                <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                    已选 <strong style="color:#e4e6eb;">${files.length}</strong> 张图片
                </div>
                <div class="form-group">
                    <label>目标格式</label>
                    <select id="mediaConvertFormat">
                        <option value="webp">WebP（推荐）</option>
                        <option value="jpg">JPEG</option>
                        <option value="png">PNG</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>质量 (1-100)</label>
                    <input type="number" id="mediaConvertQuality" value="85" min="1" max="100">
                </div>
                <div style="color:#8b8fa3;font-size:12px;margin-bottom:8px;">
                    <input type="checkbox" id="mediaConvertDryRun" checked> 预览模式
                </div>
                <div class="btn-row">
                    <button class="btn-cancel" onclick="closeModal()">取消</button>
                    <button class="btn-confirm" id="mediaConvertConfirm">执行转换</button>
                </div>
            </div>
        </div>
        `;

        openModal(modalHtml);
        document.getElementById('mediaConvertConfirm').addEventListener('click', () => this.doConvert(files));
    },

    async doConvert(files) {
        const targetFormat = document.getElementById('mediaConvertFormat').value;
        const quality = parseInt(document.getElementById('mediaConvertQuality').value) || 85;
        const dryRun = document.getElementById('mediaConvertDryRun').checked;

        closeModal();
        clearLog();
        showLog('⏳ 开始格式转换...', 'info');

        try {
            const result = await apiCall('/api/media/convert', {
                files: files,
                target_format: targetFormat,
                quality: quality,
                dry_run: dryRun
            });

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }

            if (result.results) {
                if (dryRun) {
                    result.results.forEach(r => {
                        if (r.status === 'preview') {
                            showLog('📋 ' + r.file + ' → ' + r.output, 'info');
                        }
                    });
                    showLog('📊 预览完成，共 ' + result.results.length + ' 张图片将转换', 'info');
                } else {
                    result.results.forEach(r => {
                        if (r.status === 'success') {
                            showLog('✅ ' + r.file + ' → ' + r.output, 'success');
                        }
                    });
                    showLog('✅ ' + result.stats.converted + ' 张图片已转换', 'success');
                }
            }

            await loadFiles(currentPath);
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    },

    resize() {
        const files = this.getImageFiles();
        if (files.length === 0) {
            showLog('⚠️ 请选择图片文件', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal-overlay show">
            <div class="modal" style="max-width:450px;">
                <h2>📐 调整尺寸</h2>
                <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                    已选 <strong style="color:#e4e6eb;">${files.length}</strong> 张图片
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div class="form-group">
                        <label>宽度 (px)</label>
                        <input type="number" id="mediaResizeWidth" value="1920">
                    </div>
                    <div class="form-group">
                        <label>高度 (px)</label>
                        <input type="number" id="mediaResizeHeight" value="1080">
                    </div>
                </div>
                <div class="form-group">
                    <label>缩放模式</label>
                    <select id="mediaResizeMode">
                        <option value="fit">适应 (保持比例)</option>
                        <option value="fill">填充 (裁切)</option>
                        <option value="stretch">拉伸</option>
                    </select>
                </div>
                <div style="color:#8b8fa3;font-size:12px;margin-bottom:8px;">
                    <input type="checkbox" id="mediaResizeDryRun" checked> 预览模式
                </div>
                <div class="btn-row">
                    <button class="btn-cancel" onclick="closeModal()">取消</button>
                    <button class="btn-confirm" id="mediaResizeConfirm">执行调整</button>
                </div>
            </div>
        </div>
        `;

        openModal(modalHtml);
        document.getElementById('mediaResizeConfirm').addEventListener('click', () => this.doResize(files));
    },

    async doResize(files) {
        const width = parseInt(document.getElementById('mediaResizeWidth').value) || 1920;
        const height = parseInt(document.getElementById('mediaResizeHeight').value) || 1080;
        const mode = document.getElementById('mediaResizeMode').value;
        const dryRun = document.getElementById('mediaResizeDryRun').checked;

        closeModal();
        clearLog();
        showLog('⏳ 开始调整尺寸...', 'info');

        try {
            const result = await apiCall('/api/media/resize', {
                files: files,
                width: width,
                height: height,
                mode: mode,
                dry_run: dryRun
            });

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }

            if (result.results) {
                if (dryRun) {
                    result.results.forEach(r => {
                        if (r.status === 'preview') {
                            showLog('📋 ' + r.file + ' → ' + r.output + ' (' + r.width + 'x' + r.height + ')',
                                'info');
                        }
                    });
                    showLog('📊 预览完成，共 ' + result.results.length + ' 张图片将调整', 'info');
                } else {
                    result.results.forEach(r => {
                        if (r.status === 'success') {
                            showLog('✅ ' + r.file + ' → ' + r.output, 'success');
                        }
                    });
                    showLog('✅ ' + result.stats.resized + ' 张图片已调整', 'success');
                }
            }

            await loadFiles(currentPath);
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

ModuleManager.register('media', MediaModule);
