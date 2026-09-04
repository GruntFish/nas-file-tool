// static/js/modules/move_copy.js
const MoveCopyModule = {
    name: 'move_copy',

    init() {
        document.getElementById('moveCopyOpenBtn').addEventListener('click', () => this.openModal());
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
        const el = document.getElementById('moveCopySelectedCount');
        if (el) el.textContent = count;
    },

    openModal() {
        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            showLog('⚠️ 请先选择要移动/复制的文件', 'warning');
            return;
        }

        const currentDir = window.currentPath || '/';
        let dirOptions = '';
        const collectDirs = (nodes, prefix) => {
            for (let node of nodes) {
                if (node.is_dir) {
                    const path = prefix ? prefix + '/' + node.name : node.name;
                    if (path !== currentDir.replace(/^\//, '')) {
                        dirOptions += `<option value="${path}">📁 ${path}</option>`;
                    }
                    if (node.children) collectDirs(node.children, path);
                }
            }
        };
        collectDirs(window.fullTreeData || [], '');

        const modalHtml = `
        <div class="modal" style="max-width:550px;">
            <h2>📦 移动/复制文件</h2>
            <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                已选 <strong style="color:#e4e6eb;">${files.length}</strong> 个文件
                <div style="color:#4a4e62;font-size:11px;margin-top:4px;">
                    📁 当前目录: <strong style="color:#b5b9c9;">${escapeHtml(currentDir)}</strong>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div class="form-group">
                    <label>操作</label>
                    <select id="mcAction">
                        <option value="move">移动</option>
                        <option value="copy">复制</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>覆盖已存在文件</label>
                    <div style="display:flex;align-items:center;height:32px;padding-left:4px;">
                        <input type="checkbox" id="mcOverwrite" style="accent-color:#667eea;width:16px;height:16px;">
                        <span style="color:#8b8fa3;font-size:11px;margin-left:6px;">勾选后覆盖同名文件</span>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label>目标目录</label>
                <div style="display:flex;gap:6px;">
                    <select id="mcTargetSelect" style="flex:2;">
                        <option value="">📁 选择已有目录...</option>
                        ${dirOptions}
                    </select>
                    <input type="text" id="mcTargetInput" placeholder="输入新目录名自动创建" style="flex:1;">
                </div>
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">
                    💡 下拉框选择已有目录，或输入新目录名称（在当前目录下自动创建）
                </div>
            </div>

            <hr>
            <h3>📋 过滤条件（可选）</h3>
            <div class="filter-grid">
                <div class="form-group"><label>文件名包含</label><input type="text" id="mcFilterNameContains" placeholder="IMG_"></div>
                <div class="form-group"><label>文件名不包含</label><input type="text" id="mcFilterNameNotContains" placeholder="temp"></div>
                <div class="form-group"><label>扩展名</label><input type="text" id="mcFilterExtensions" placeholder=".jpg,.png"></div>
                <div class="form-group"><label>排除扩展名</label><input type="text" id="mcFilterExtNot" placeholder=".tmp"></div>
                <div class="form-group"><label>最小大小(KB)</label><input type="number" id="mcFilterMinSize" placeholder="1024"></div>
                <div class="form-group"><label>最大大小(KB)</label><input type="number" id="mcFilterMaxSize" placeholder="10240"></div>
                <div class="form-group"><label>日期(晚于)</label><input type="date" id="mcFilterDateAfter"></div>
                <div class="form-group"><label>日期(早于)</label><input type="date" id="mcFilterDateBefore"></div>
                <div class="form-group"><label>文件类型</label>
                    <select id="mcFilterFileTypes">
                        <option value="">全部</option>
                        <option value="image">图片</option>
                        <option value="video">视频</option>
                        <option value="audio">音频</option>
                        <option value="document">文档</option>
                        <option value="archive">压缩包</option>
                    </select>
                </div>
                <div class="form-group full-width"><label>正则匹配</label><input type="text" id="mcFilterRegex" placeholder="^IMG_.*\.jpg$"></div>
            </div>

            <div id="mcFilterPreview" style="display:none;margin-top:6px;">
                <div class="preview-info" id="mcFilterPreviewInfo"></div>
            </div>

            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="mcConfirmBtn">确认执行</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#mcConfirmBtn').addEventListener('click', () => this.execute());
        overlay.querySelectorAll('input, select').forEach(el => {
            el.addEventListener('input', () => this.previewFilter());
            el.addEventListener('change', () => this.previewFilter());
        });
    },

    getFilters() {
        const v = (id) => document.getElementById(id)?.value?.trim() || '';
        const filters = {};
        if (v('mcFilterNameContains')) filters.name_contains = v('mcFilterNameContains');
        if (v('mcFilterNameNotContains')) filters.name_not_contains = v('mcFilterNameNotContains');
        if (v('mcFilterExtensions')) filters.extensions = v('mcFilterExtensions').split(',').map(s => s.trim()).filter(s => s);
        if (v('mcFilterExtNot')) filters.extensions_not = v('mcFilterExtNot').split(',').map(s => s.trim()).filter(s => s);
        if (v('mcFilterMinSize')) filters.min_size = parseInt(v('mcFilterMinSize'));
        if (v('mcFilterMaxSize')) filters.max_size = parseInt(v('mcFilterMaxSize'));
        if (v('mcFilterDateAfter')) filters.date_after = v('mcFilterDateAfter');
        if (v('mcFilterDateBefore')) filters.date_before = v('mcFilterDateBefore');
        if (v('mcFilterFileTypes')) filters.file_types = v('mcFilterFileTypes');
        if (v('mcFilterRegex')) filters.regex = v('mcFilterRegex');
        return filters;
    },

    async previewFilter() {
        const files = Array.from(selectedFiles);
        if (files.length === 0) return;
        const filters = this.getFilters();
        if (Object.keys(filters).length === 0) {
            document.getElementById('mcFilterPreview').style.display = 'none';
            return;
        }
        try {
            const result = await apiCall('/api/filter_preview', { files, filters });
            const div = document.getElementById('mcFilterPreview');
            div.style.display = 'block';
            document.getElementById('mcFilterPreviewInfo').innerHTML =
                `<span class="total">总数: ${result.total}</span><span class="matched" style="margin-left:16px;">✅ 匹配: ${result.matched}</span>` +
                (result.matched === 0 ? '<span style="color:#fc8181;margin-left:16px;">⚠️ 无匹配</span>' : '');
        } catch (e) {}
    },

    async execute() {
        const action = document.getElementById('mcAction').value;
        let targetDir = document.getElementById('mcTargetSelect').value.trim();
        const inputDir = document.getElementById('mcTargetInput').value.trim();

        if (inputDir) {
            const currentDir = window.currentPath || '/';
            if (currentDir === '/') {
                targetDir = inputDir;
            } else {
                targetDir = currentDir.replace(/^\//, '') + '/' + inputDir;
            }
        }

        if (!targetDir) {
            showLog('⚠️ 请选择或输入目标目录', 'warning');
            return;
        }

        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            showLog('⚠️ 请选择文件', 'warning');
            return;
        }

        const overwriteEl = document.getElementById('mcOverwrite');
        const overwrite = overwriteEl ? overwriteEl.checked : false;

        closeModal();
        clearLog();

        const filters = this.getFilters();
        if (Object.keys(filters).length > 0) showLog('📋 应用过滤条件...', 'info');
        showLog('⏳ 开始' + (action === 'move' ? '移动' : '复制') + ' ' + files.length + ' 个文件到: ' + targetDir, 'info');

        try {
            await OperationManager.execute({
                title: `📦 正在${action === 'move' ? '移动' : '复制'} ${files.length} 个文件...`,
                completeMessage: `✅ 成功${action === 'move' ? '移动' : '复制'} ${files.length} 个文件`,
                execute: async (progress) => {
                    progress.setTotal(files.length);
                    const result = await apiCall('/api/move_copy', {
                        action: action,
                        files: files,
                        target_dir: targetDir,
                        overwrite: overwrite,
                        filters: filters,
                        dry_run: false
                    });
                    if (result.error) {
                        throw new Error(result.error);
                    }
                    if (result.results) {
                        const success = result.results.filter(r => r.status === 'success');
                        const errors = result.results.filter(r => r.status === 'error');
                        const skipped = result.results.filter(r => r.status === 'skip');
                        success.forEach((r, idx) => {
                            progress.update(idx + 1, `已处理: ${r.file}`);
                            showLog('✅ ' + r.file + ' → ' + r.to, 'success');
                        });
                        errors.forEach(r => {
                            showLog('❌ ' + r.file + ' - ' + r.reason, 'error');
                        });
                        skipped.forEach(r => {
                            showLog('⚠️ ' + r.file + ' - ' + r.reason, 'warning');
                        });
                    }
                    const msg = result.stats?.message || '处理完成';
                    showLog('✅ ' + msg, 'success');
                    await loadFiles(window.currentPath);
                }
            });
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(MoveCopyModule);
}
