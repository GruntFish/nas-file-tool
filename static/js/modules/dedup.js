// static/js/modules/dedup.js
const DedupModule = {
    name: 'dedup',

    init() {
        document.getElementById('dedupOpenBtn').addEventListener('click', () => this.openModal());
        this.updatePath();
    },

    destroy() {
        closeModal();
        selectedFiles.clear();
        updateSelectedInfo();
        if (typeof renderFiles === 'function' && window.fileList) {
            renderFiles(window.fileList);
        }
    },

    updatePath() {
        const el = document.getElementById('dedupPathDisplay');
        if (el) el.textContent = currentPath;
    },

    openModal() {
        const currentDir = window.currentPath || '/';

        const modalHtml = `
        <div class="modal" style="max-width:550px;">
            <h2>🧹 文件去重</h2>
            <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                当前目录: <strong style="color:#e4e6eb;">${currentDir}</strong>
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">📁 只在当前目录下进行去重，不会进入父目录</div>
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
            <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <label style="margin:0;display:flex;align-items:center;gap:6px;cursor:pointer;">
                    <input type="checkbox" id="dedupRecursive" style="accent-color:#667eea;width:16px;height:16px;">
                    <span style="color:#8b8fa3;font-size:13px;">📂 包括子目录</span>
                </label>
                <span style="color:#4a4e62;font-size:11px;">（勾选后将对所有子目录进行去重）</span>
            </div>
            <div id="dedupPreviewArea" style="display:none;margin-top:8px;">
                <div class="preview-list" id="dedupPreviewList" style="max-height:200px;"></div>
                <div style="color:#f6ad55;font-size:12px;margin-top:4px;" id="dedupStats"></div>
            </div>
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="dedupConfirmBtn">确认执行</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#dedupConfirmBtn').addEventListener('click', () => this.execute());
    },

    async execute() {
        const mode = document.getElementById('dedupMode').value;
        const action = document.getElementById('dedupAction').value;
        const recursive = document.getElementById('dedupRecursive').checked;

        closeModal();
        clearLog();
        showLog('⏳ 开始去重扫描...' + (recursive ? ' (包含子目录)' : ' (仅当前目录)'), 'info');

        try {
            await OperationManager.execute({
                title: `🧹 正在去重扫描...`,
                completeMessage: `✅ 去重完成`,
                execute: async (progress) => {
                    progress.setTotal(1);
                    progress.update(0, '正在扫描文件...');

                    const result = await dedupFiles({
                        method: 'md5',
                        mode,
                        action,
                        recursive: recursive,
                        path: currentPath
                    });

                    progress.update(1, '处理完成');

                    if (result.error) {
                        throw new Error(result.error);
                    }

                    if (result.logs && result.logs.length > 0) {
                        showLog(`📋 共 ${result.logs.length} 条操作日志`, 'info');
                        const keyLogs = result.logs.filter(log => 
                            log.status === 'success' || 
                            log.status === 'error' || 
                            log.status === 'warning' ||
                            log.message.includes('MD5') ||
                            log.message.includes('删除') ||
                            log.message.includes('重复组') ||
                            log.message.includes('保留')
                        );
                        const displayLogs = keyLogs.slice(-50);
                        displayLogs.forEach(log => {
                            const statusMap = {
                                'success': '✅',
                                'error': '❌',
                                'warning': '⚠️',
                                'info': '📋'
                            };
                            const icon = statusMap[log.status] || '📋';
                            let fileInfo = '';
                            if (log.file) {
                                const parts = log.file.split('/');
                                fileInfo = ` [${parts[parts.length - 1]}]`;
                            }
                            showLog(`${icon} ${log.message}${fileInfo}`, log.status);
                        });
                        if (keyLogs.length > 50) {
                            showLog(`📋 ... 还有 ${keyLogs.length - 50} 条日志未显示`, 'info');
                        }
                    }

                    if (result.duplicates && result.duplicates.length > 0) {
                        showLog(`📋 发现 ${result.duplicates.length} 组重复`, 'info');
                        let totalDup = 0;
                        result.duplicates.forEach((g, idx) => {
                            const count = g.length - 1;
                            totalDup += count;
                            const fileName = g[0].split('/').pop();
                            showLog(`  ├─ 组 #${idx + 1}: ${fileName} (${count} 个重复)`, 'info');
                        });
                        if (result.deleted > 0) {
                            showLog(`✅ 已删除 ${result.deleted} 个重复文件`, 'success');
                        } else if (action === 'find') {
                            showLog(`📋 共发现 ${totalDup} 个重复文件`, 'info');
                        }
                    } else {
                        showLog('✅ 没有重复文件', 'success');
                    }

                    if (result.warning) {
                        showLog('⚠️ ' + result.warning, 'warning');
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
    ModuleRegistry.register(DedupModule);
}
