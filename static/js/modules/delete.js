// static/js/modules/delete.js

if (typeof ModuleRegistry === 'undefined') {
    var ModuleRegistry = window.ModuleRegistry || window.ModuleManager || {};
}

const DeleteModule = {
    name: 'delete',

    init() {
        document.getElementById('deleteOpenBtn').addEventListener('click', () => this.openModal());
        this.updateCount();
    },

    onSelectChange(selected) {
        this.updateCount();
    },

    updateCount() {
        const count = selectedFiles.size;
        const el = document.getElementById('deleteSelectedCount');
        if (el) el.textContent = count;
    },

    openModal() {
        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            showLog('⚠️ 请先选择要删除的文件或目录', 'warning');
            return;
        }

        const fileList = files.map(f => '  📄 ' + getFileName(f)).join('\n');

        const modalHtml = `
        <div class="modal-overlay show">
            <div class="modal" style="max-width:500px;">
                <h2>🗑️ 删除文件/目录</h2>
                <div style="color:#e53e3e;font-size:13px;margin-bottom:10px;">
                    ⚠️ 警告：删除操作不可恢复！
                </div>
                <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                    将删除 <strong style="color:#e4e6eb;">${files.length}</strong> 个文件/目录：
                    <div style="background:#14171f;border-radius:6px;padding:8px 12px;margin-top:6px;font-size:12px;font-family:monospace;color:#b5b9c9;max-height:150px;overflow-y:auto;">
                        ${fileList}
                    </div>
                </div>
                <div class="btn-row">
                    <button class="btn-cancel" onclick="closeModal()">取消</button>
                    <button class="btn-confirm" id="deleteConfirmBtn" style="background:#e53e3e;color:#fff;">确认删除</button>
                </div>
            </div>
        </div>
        `;

        openModal(modalHtml);
        document.getElementById('deleteConfirmBtn').addEventListener('click', () => this.execute(files));
    },

    async execute(files) {
        closeModal();
        clearLog();
        showLog('⏳ 开始删除 ' + files.length + ' 个文件/目录...', 'info');

        let deleted = 0;
        let failed = 0;

        for (let filePath of files) {
            try {
                const result = await apiCall('/api/delete', { files: [filePath] });
                if (result.error) {
                    failed++;
                    showLog('❌ 删除失败: ' + getFileName(filePath) + ' - ' + result.error, 'error');
                } else {
                    deleted++;
                    if (result.logs) result.logs.forEach(log => showLog(log.text, log.type || 'info'));
                }
            } catch (e) {
                failed++;
                showLog('❌ 删除失败: ' + getFileName(filePath) + ' - ' + e.message, 'error');
            }
        }

        if (deleted > 0) showLog('✅ 成功删除 ' + deleted + ' 个文件/目录', 'success');
        if (failed > 0) showLog('⚠️ 删除失败 ' + failed + ' 个文件/目录', 'error');

        selectedFiles.clear();
        await loadFiles(currentPath);
    }
};

if (typeof ModuleRegistry !== 'undefined' && ModuleRegistry.register) {
    ModuleRegistry.register(deleteModule);
}
