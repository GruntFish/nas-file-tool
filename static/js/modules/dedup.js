// static/js/modules/dedup.js
const DedupModule = {
    name: 'dedup',

    init() {
        document.getElementById('dedupOpenBtn').addEventListener('click', () => this.openModal());
        this.updatePath();
    },

    updatePath() {
        const el = document.getElementById('dedupPathDisplay');
        if (el) el.textContent = currentPath;
    },

    openModal() {
        const modalHtml = `
        <div class="modal-overlay show">
            <div class="modal" style="max-width:500px;">
                <h2>🧹 文件去重</h2>
                <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                    当前目录: <strong style="color:#e4e6eb;">${currentPath}</strong>
                </div>
                <div class="form-group">
                    <label>去重模式</label>
                    <select id="dedupMode">
                        <option value="fast">⚡ 快速（按大小）</option>
                        <option value="standard" selected>📋 标准（动态采样，推荐）</option>
                        <option value="precise">🎯 精确（MD5，限500文件）</option>
                    </select>
                    <div style="color:#4a4e62;font-size:11px;margin-top:2px;">
                        标准模式：小文件MD5，大文件多点采样
                    </div>
                </div>
                <div class="form-group">
                    <label>操作</label>
                    <select id="dedupAction">
                        <option value="find">仅查找（列出重复项）</option>
                        <option value="delete_first">删除重复（保留第一个）</option>
                        <option value="delete_last">删除重复（保留最后一个）</option>
                        <option value="delete_smallest">删除重复（保留最大的）</option>
                        <option value="delete_largest">删除重复（保留最小的）</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>递归子目录</label>
                    <select id="dedupRecursive">
                        <option value="true">是</option>
                        <option value="false">否（仅当前目录）</option>
                    </select>
                </div>
                <div id="dedupPreviewArea" style="display:none;margin-top:8px;">
                    <div class="preview-list" id="dedupPreviewList" style="max-height:200px;"></div>
                    <div style="color:#f6ad55;font-size:12px;margin-top:4px;" id="dedupStats"></div>
                </div>
                <div class="btn-row">
                    <button class="btn-cancel" onclick="closeModal()">取消</button>
                    <button class="btn-confirm" id="dedupConfirmBtn">确认执行</button>
                </div>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#dedupConfirmBtn').addEventListener('click', () => this.execute());
    },

    async execute() {
        const mode = document.getElementById('dedupMode').value;
        const action = document.getElementById('dedupAction').value;
        const recursive = document.getElementById('dedupRecursive').value === 'true';

        closeModal();
        clearLog();
        showLog('⏳ 查找重复文件...', 'info');

        try {
            const result = await dedupFiles({ method: 'md5', mode, action, recursive, path: currentPath });
            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }

            if (result.duplicates && result.duplicates.length > 0) {
                showLog('📋 发现 ' + result.duplicates.length + ' 组重复', 'info');
                let totalDup = 0;
                result.duplicates.forEach(g => {
                    const count = g.length - 1;
                    totalDup += count;
                    showLog('  ├─ ' + getFileName(g[0]) + ' (' + count + ' 个重复)', 'info');
                });
                if (result.deleted > 0) {
                    showLog('✅ 已删除 ' + result.deleted + ' 个重复文件', 'success');
                } else if (action === 'find') {
                    showLog('📋 共发现 ' + totalDup + ' 个重复文件', 'info');
                }
            } else {
                showLog('✅ 没有重复文件', 'success');
            }

            if (result.warning) {
                showLog('⚠️ ' + result.warning, 'warning');
            }

            await loadFiles(currentPath);
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(DedupModule);
}
