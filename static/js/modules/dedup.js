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
                <select id="dedupMode" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                    <option value="fast">⚡ 快速（文件名+大小+哈希）</option>
                    <option value="standard" selected>📋 哈希 + MD5（推荐）</option>
                    <option value="precise">🎯 精确（完整 MD5，速度较慢）</option>
                </select>
                <div style="color:#4a4e62;font-size:11px;margin-top:4px;">
                    <div>⚡ 快速：按文件名+大小+哈希采样，速度极快</div>
                    <div>📋 推荐：xxHash + MD5 组合，速度快，精度高</div>
                    <div>🎯 精确：完整 MD5 计算，最精准但速度较慢</div>
                </div>
            </div>
            <div class="form-group" style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
                <label style="display:flex;align-items:center;gap:4px;cursor:pointer;white-space:nowrap;margin:0;">
                    <input type="checkbox" id="dedupRecursive" style="accent-color:#667eea;width:15px;height:15px;margin:0;">
                    <span style="color:#8b8fa3;font-size:13px;">📂 包括子目录</span>
                </label>
                <span style="color:#4a4e62;font-size:11px;white-space:nowrap;">（勾选后将对所有子目录进行去重）</span>
            </div>
            <div id="dedupResultArea" style="display:none;margin-top:8px;">
                <div style="color:#e4e6eb;font-size:14px;font-weight:600;margin-bottom:6px;">📋 重复文件组</div>
                <div id="dedupResultList" style="max-height:300px;overflow-y:auto;background:#14171f;border-radius:6px;padding:8px;border:1px solid #2d313e;"></div>
                <div style="color:#f6ad55;font-size:12px;margin-top:6px;" id="dedupResultStats"></div>
                <div class="btn-row" style="margin-top:10px;">
                    <button class="btn-confirm" id="dedupDeleteBtn" style="background:#e53e3e;color:#fff;display:none;">🗑️ 删除选中的重复文件</button>
                </div>
            </div>
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="dedupScanBtn">🔍 扫描重复</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#dedupScanBtn').addEventListener('click', () => this.scan());
        overlay.querySelector('#dedupDeleteBtn').addEventListener('click', () => this.deleteSelected());
        this._overlay = overlay;
    },

    async scan() {
        const mode = document.getElementById('dedupMode').value;
        const recursive = document.getElementById('dedupRecursive').checked;
        const scanBtn = document.getElementById('dedupScanBtn');
        const resultArea = document.getElementById('dedupResultArea');
        const resultList = document.getElementById('dedupResultList');
        const resultStats = document.getElementById('dedupResultStats');
        const deleteBtn = document.getElementById('dedupDeleteBtn');

        scanBtn.disabled = true;
        scanBtn.textContent = '⏳ 扫描中...';
        resultArea.style.display = 'none';
        deleteBtn.style.display = 'none';

        showLog('⏳ 开始扫描重复文件...' + (recursive ? ' (包含子目录)' : ' (仅当前目录)'), 'info');

        try {
            const result = await apiCall('/api/dedup', {
                method: 'md5',
                mode: mode,
                action: 'find',
                recursive: recursive,
                path: window.currentPath
            });

            if (result.error) {
                showLog('❌ ' + result.error, 'error');
                scanBtn.disabled = false;
                scanBtn.textContent = '🔍 扫描重复';
                return;
            }

            if (!result.duplicates || result.duplicates.length === 0) {
                resultArea.style.display = 'block';
                resultList.innerHTML = '<div style="color:#68d391;text-align:center;padding:20px;">✅ 没有发现重复文件</div>';
                resultStats.textContent = '';
                deleteBtn.style.display = 'none';
                showLog('✅ 没有发现重复文件', 'success');
                scanBtn.disabled = false;
                scanBtn.textContent = '🔍 扫描重复';
                return;
            }

            let html = '';
            let totalDup = 0;
            let groupId = 0;

            result.duplicates.forEach(group => {
                groupId++;
                const groupLabel = '📁 重复组 #' + groupId + '（' + group.length + ' 个文件）';
                html += '<div style="color:#f0c94d;font-weight:600;font-size:13px;margin-top:6px;padding:4px 0;">' + groupLabel + '</div>';
                
                group.forEach((filePath, idx) => {
                    const fileName = filePath.split('/').pop();
                    const isChecked = idx === 0 ? 'checked' : '';
                    html += `
                        <div style="display:flex;align-items:center;gap:8px;padding:2px 4px;background:${idx === 0 ? '#1a2a1a' : '#1a1a1a'};border-radius:3px;margin:1px 0;">
                            <input type="checkbox" class="dedup-file-checkbox" data-group="${groupId}" data-path="${filePath}" ${isChecked} style="accent-color:#667eea;width:14px;height:14px;">
                            <span style="color:${idx === 0 ? '#68d391' : '#b5b9c9'};font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                                ${idx === 0 ? '✅ ' : '📄 '}${fileName}
                            </span>
                            <span style="color:#4a4e62;font-size:10px;"></span>
                        </div>
                    `;
                });
                totalDup += group.length;
            });

            resultList.innerHTML = html;
            resultStats.textContent = '📊 发现 ' + result.duplicates.length + ' 组重复，共 ' + totalDup + ' 个文件（每组默认保留第一个）';
            resultArea.style.display = 'block';
            deleteBtn.style.display = 'block';
            deleteBtn.textContent = '🗑️ 删除 ' + (totalDup - result.duplicates.length) + ' 个重复文件';

            window._dedupResult = {
                groups: result.duplicates,
                totalFiles: totalDup
            };

            resultList.querySelectorAll('.dedup-file-checkbox').forEach(cb => {
                cb.addEventListener('change', function() {
                    const group = this.dataset.group;
                    const groupSelector = '.dedup-file-checkbox[data-group="' + group + '"]';
                    const checkboxes = resultList.querySelectorAll(groupSelector);
                    const checked = resultList.querySelectorAll(groupSelector + ':checked');
                    
                    if (!this.checked && checked.length === 0) {
                        this.checked = true;
                        showLog('⚠️ 每组至少保留一个文件', 'warning');
                        return;
                    }
                    
                    const allCheckboxes = resultList.querySelectorAll('.dedup-file-checkbox');
                    const allChecked = resultList.querySelectorAll('.dedup-file-checkbox:checked');
                    const totalFiles = window._dedupResult?.totalFiles || 0;
                    const toDelete = totalFiles - allChecked.length;
                    if (toDelete > 0) {
                        deleteBtn.textContent = '🗑️ 删除 ' + toDelete + ' 个重复文件';
                    } else {
                        deleteBtn.textContent = '✅ 没有重复文件需要删除';
                    }
                });
            });

            showLog('📋 发现 ' + result.duplicates.length + ' 组重复文件', 'info');

        } catch (e) {
            console.error('扫描失败:', e);
            showLog('❌ ' + e.message, 'error');
        } finally {
            scanBtn.disabled = false;
            scanBtn.textContent = '🔍 扫描重复';
        }
    },

    async deleteSelected() {
        const resultList = document.getElementById('dedupResultList');
        const allCheckboxes = resultList.querySelectorAll('.dedup-file-checkbox');
        const toDeleteFiles = [];

        allCheckboxes.forEach(cb => {
            if (!cb.checked) {
                toDeleteFiles.push(cb.dataset.path);
            }
        });

        if (toDeleteFiles.length === 0) {
            showLog('⚠️ 没有需要删除的重复文件', 'warning');
            return;
        }

        if (!confirm('确定要删除 ' + toDeleteFiles.length + ' 个重复文件吗？\n\n⚠️ 此操作不可恢复！')) {
            return;
        }

        closeModal();
        clearLog();
        showLog('⏳ 开始删除 ' + toDeleteFiles.length + ' 个重复文件...', 'info');

        try {
            await OperationManager.execute({
                title: '🗑️ 正在删除 ' + toDeleteFiles.length + ' 个重复文件...',
                completeMessage: '✅ 成功删除 ' + toDeleteFiles.length + ' 个重复文件',
                execute: async (progress) => {
                    progress.setTotal(toDeleteFiles.length);
                    let deleted = 0;
                    let failed = 0;

                    for (let i = 0; i < toDeleteFiles.length; i++) {
                        if (progress.isCancelled()) {
                            throw new Error('操作已取消');
                        }
                        const filePath = toDeleteFiles[i];
                        const fileName = filePath.split('/').pop();

                        progress.update(
                            i,
                            '📄 正在删除: ' + fileName + ' (' + (i + 1) + '/' + toDeleteFiles.length + ')'
                        );

                        showLog('⏳ 正在删除: ' + fileName + ' (' + (i + 1) + '/' + toDeleteFiles.length + ')', 'info');

                        try {
                            const result = await apiCall('/api/delete', { files: [filePath] });
                            if (result.error) {
                                failed++;
                                showLog('❌ 删除失败: ' + fileName + ' - ' + result.error, 'error');
                                progress.update(
                                    i + 1,
                                    '❌ ' + fileName + ' 失败 (' + (i + 1) + '/' + toDeleteFiles.length + ')'
                                );
                            } else {
                                deleted++;
                                if (result.logs) result.logs.forEach(log => showLog(log.text, log.type || 'info'));
                                progress.update(
                                    i + 1,
                                    '✅ ' + fileName + ' 已删除 (' + deleted + '/' + toDeleteFiles.length + ')'
                                );
                            }
                        } catch (e) {
                            failed++;
                            showLog('❌ 删除失败: ' + fileName + ' - ' + e.message, 'error');
                            progress.update(
                                i + 1,
                                '❌ ' + fileName + ' 失败 (' + (i + 1) + '/' + toDeleteFiles.length + ')'
                            );
                        }
                    }

                    if (deleted > 0) showLog('✅ 成功删除 ' + deleted + ' 个重复文件', 'success');
                    if (failed > 0) showLog('⚠️ 删除失败 ' + failed + ' 个重复文件', 'error');

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
