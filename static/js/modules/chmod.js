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
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="chmodConfirmBtn">确认执行</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#chmodConfirmBtn').addEventListener('click', () => this.execute());
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
                title: '🔒 正在修改 ' + files.length + ' 个文件的权限...',
                completeMessage: '✅ 权限修改完成',
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
                        let processed = 0;
                        success.forEach(r => {
                            showLog('✅ ' + r.path + ' → ' + r.current, 'success');
                            processed++;
                            progress.update(processed, '✅ ' + r.path + ' (' + processed + '/' + files.length + ')');
                        });
                        const errors = result.results.filter(r => r.status === 'error');
                        errors.forEach(r => {
                            showLog('❌ ' + r.path + ' - ' + r.reason, 'error');
                            processed++;
                            progress.update(processed, '❌ ' + r.path + ' 失败 (' + processed + '/' + files.length + ')');
                        });
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
