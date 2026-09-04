// static/js/modules/chmod.js
const ChmodModule = {
    name: 'chmod',

    init() {
        document.getElementById('chmodOpenBtn').addEventListener('click', () => this.openModal());
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
        const el = document.getElementById('chmodSelectedCount');
        if (el) el.textContent = count;
    },

    openModal() {
        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            showLog('⚠️ 请先选择要修改权限的文件或目录', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal" style="max-width:500px;">
            <h2>🔒 修改权限</h2>
            <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                已选 <strong style="color:#e4e6eb;">${files.length}</strong> 个文件/目录
            </div>
            <div class="form-group">
                <label>权限模式</label>
                <select id="chmodMode">
                    <option value="755">755 (rwxr-xr-x) - 目录/可执行文件</option>
                    <option value="644">644 (rw-r--r--) - 普通文件</option>
                    <option value="777">777 (rwxrwxrwx) - 完全开放</option>
                    <option value="600">600 (rw-------) - 仅所有者读写</option>
                    <option value="700">700 (rwx------) - 仅所有者</option>
                    <option value="775">775 (rwxrwxr-x) - 组内可写</option>
                </select>
            </div>
            <div class="form-group">
                <label><input type="checkbox" id="chmodRecursive"> 递归修改子目录</label>
            </div>
            <div id="chmodPreviewArea" style="display:none;margin-top:8px;">
                <div class="preview-list" id="chmodPreviewList" style="max-height:200px;"></div>
                <div style="color:#68d391;font-size:12px;margin-top:4px;" id="chmodStats"></div>
            </div>
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="chmodPreviewBtn">👁️ 预览</button>
                <button class="btn-confirm" id="chmodConfirmBtn" style="display:none;">确认执行</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#chmodPreviewBtn').addEventListener('click', () => this.preview());
        overlay.querySelector('#chmodConfirmBtn').addEventListener('click', () => this.execute());
    },

    async preview() {
        const files = Array.from(selectedFiles);
        const mode = document.getElementById('chmodMode').value;
        const recursive = document.getElementById('chmodRecursive').checked;

        showLog('⏳ 预览权限修改...', 'info');

        try {
            const result = await apiCall('/api/chmod', {
                files: files,
                mode: mode,
                recursive: recursive,
                dry_run: true
            });

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }

            const previewList = document.getElementById('chmodPreviewList');
            const stats = document.getElementById('chmodStats');
            const previewArea = document.getElementById('chmodPreviewArea');

            previewList.innerHTML = '';
            if (result.results && result.results.length > 0) {
                const changed = result.results.filter(r => r.status === 'preview');
                changed.forEach(r => {
                    const div = document.createElement('div');
                    div.style.cssText = 'color:#68d391;padding:2px 0;';
                    div.textContent = '📄 ' + r.path + ' → ' + r.target + (r.is_dir ? ' (目录)' : '');
                    previewList.appendChild(div);
                });
                stats.textContent = '📊 共 ' + changed.length + ' 个文件/目录将被修改';
                previewArea.style.display = 'block';
                document.getElementById('chmodPreviewBtn').style.display = 'none';
                document.getElementById('chmodConfirmBtn').style.display = 'block';
            } else {
                previewList.innerHTML = '<div style="color:#4a4e62;">没有文件需要修改权限</div>';
                previewArea.style.display = 'block';
            }
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    },

    async execute() {
        const files = Array.from(selectedFiles);
        const mode = document.getElementById('chmodMode').value;
        const recursive = document.getElementById('chmodRecursive').checked;

        closeModal();
        clearLog();
        showLog('⏳ 开始修改权限...', 'info');

        try {
            await OperationManager.execute({
                title: `🔒 正在修改 ${files.length} 个文件的权限...`,
                completeMessage: `✅ 权限修改完成`,
                execute: async (progress) => {
                    progress.setTotal(files.length);
                    const result = await apiCall('/api/chmod', {
                        files: files,
                        mode: mode,
                        recursive: recursive,
                        dry_run: false
                    });

                    if (result.error) {
                        throw new Error(result.error);
                    }

                    if (result.results) {
                        const success = result.results.filter(r => r.status === 'success');
                        success.forEach(r => showLog('✅ ' + r.path + ' → ' + r.current, 'success'));
                    }

                    showLog('✅ ' + result.stats.changed + ' 个文件/目录权限已修改', 'success');
                    selectedFiles.clear();
                    await loadFiles(currentPath);
                }
            });
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(ChmodModule);
}
