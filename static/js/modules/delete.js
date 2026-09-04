// static/js/modules/delete.js
const DeleteModule = {
    name: 'delete',

    init() {
        document.getElementById('deleteOpenBtn').addEventListener('click', () => this.openModal());
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
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#deleteConfirmBtn').addEventListener('click', () => this.execute(files));
    },

    async execute(files) {
        closeModal();
        clearLog();
        showLog('⏳ 开始删除 ' + files.length + ' 个文件/目录...', 'info');

        try {
            await OperationManager.execute({
                title: `🗑️ 正在删除 ${files.length} 个文件...`,
                completeMessage: `✅ 成功删除 ${files.length} 个文件`,
                onCancel: () => {
                    showLog('⏹️ 删除已取消', 'warning');
                },
                execute: async (progress) => {
                    progress.setTotal(files.length);
                    let deleted = 0;
                    let failed = 0;

                    for (let i = 0; i < files.length; i++) {
                        if (progress.isCancelled()) {
                            throw new Error('操作已取消');
                        }
                        const filePath = files[i];
                        progress.update(i + 1, `正在删除: ${getFileName(filePath)}`);

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

                        // 每10个文件刷新一次界面
                        if (i % 10 === 0) {
                            await new Promise(resolve => setTimeout(resolve, 50));
                        }
                    }

                    if (deleted > 0) showLog('✅ 成功删除 ' + deleted + ' 个文件/目录', 'success');
                    if (failed > 0) showLog('⚠️ 删除失败 ' + failed + ' 个文件/目录', 'error');

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
    ModuleRegistry.register(DeleteModule);
}
