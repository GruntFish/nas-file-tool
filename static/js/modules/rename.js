// static/js/modules/rename.js
const RenameModule = {
    name: 'rename',

    init() {
        // ===== 只绑定一次 =====
        if (!this._initialized) {
            this.bindEvents();
            this._initialized = true;
        }
        this.setupActionToggle();
        setTimeout(() => this.autoPreview(), 500);
        document.addEventListener('filesLoaded', () => {
            setTimeout(() => this.autoPreview(), 300);
        });
        document.addEventListener('selectionChanged', () => {
            setTimeout(() => this.autoPreview(), 200);
        });
    },

    destroy() {
        // ===== 只清理数据，不清理样式 =====
        window.renamePreview = {};
        selectedFiles.clear();
        updateSelectedInfo();
        if (typeof renderFiles === 'function' && window.fileList) {
            renderFiles(window.fileList);
        }
        // 不重置 _initialized，避免重新绑定
    },

    // ===== 事件绑定只执行一次 =====
    bindEvents() {
        if (this._bound) return;
        this._bound = true;

        // ===== 【修复】直接绑定事件，不替换 DOM =====
        const executeBtn = document.getElementById('executeRenameBtn');
        if (executeBtn) {
            executeBtn.addEventListener('click', () => this.execute());
            executeBtn.className = 'btn-execute';
        }

        const actionSelect = document.getElementById('renameAction');
        if (actionSelect) {
            actionSelect.addEventListener('change', () => {
                this.setupActionToggle();
                this.autoPreview();
            });
            actionSelect.disabled = false;
            actionSelect.style.color = '#e4e6eb';
            actionSelect.style.background = '#1a1d27';
        }

        ['findText', 'replaceText', 'caseSensitive', 'startNum', 'stepNum', 'digitsNum',
            'numberPos', 'extAction', 'extValue', 'removeStart', 'removeLen', 'removeFromEnd',
            'dateType', 'dateFormat', 'datePos'
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => this.autoPreview());
                el.addEventListener('change', () => this.autoPreview());
                if (el.tagName === 'SELECT') {
                    el.style.color = '#e4e6eb';
                    el.style.background = '#1a1d27';
                    el.disabled = false;
                }
                if (el.tagName === 'INPUT' && el.type !== 'checkbox') {
                    el.style.color = '#e4e6eb';
                    el.style.background = '#1a1d27';
                }
            }
        });

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.restoreSelectState();
            }
        });
    },

    cleanup() {
        // ===== 只清理按钮，不动输入框 =====
        // 实际上现在不需要了，因为不再替换 DOM
    },

    restoreSelectState() {
        const selects = document.querySelectorAll('.module-rename select');
        selects.forEach(select => {
            select.disabled = false;
            select.style.color = '#e4e6eb';
            select.style.background = '#1a1d27';
            select.querySelectorAll('option').forEach(opt => {
                opt.style.color = '#e4e6eb';
                opt.style.background = '#1a1d27';
            });
        });
    },

    setupActionToggle() {
        const actionEl = document.getElementById('renameAction');
        if (!actionEl) return;
        actionEl.disabled = false;
        actionEl.style.color = '#e4e6eb';
        actionEl.style.background = '#1a1d27';
        const action = actionEl.value;
        const numParams = document.getElementById('numParams');
        const extParams = document.getElementById('extParams');
        const removePosParams = document.getElementById('removePosParams');
        const dateParams = document.getElementById('dateParams');
        if (numParams) numParams.style.display = 'none';
        if (extParams) extParams.style.display = 'none';
        if (removePosParams) removePosParams.style.display = 'none';
        if (dateParams) dateParams.style.display = 'none';
        const findLabel = document.getElementById('findLabel');
        const findText = document.getElementById('findText');
        const replaceLabel = document.getElementById('replaceLabel');
        const replaceText = document.getElementById('replaceText');
        const caseSensitive = document.getElementById('caseSensitive');
        if (findLabel) findLabel.style.display = 'inline';
        if (findText) {
            findText.style.display = 'inline';
            findText.style.color = '#e4e6eb';
            findText.style.background = '#1a1d27';
        }
        if (replaceLabel) replaceLabel.style.display = 'inline';
        if (replaceText) {
            replaceText.style.display = 'inline';
            replaceText.style.color = '#e4e6eb';
            replaceText.style.background = '#1a1d27';
        }
        if (caseSensitive) caseSensitive.parentElement.style.display = 'inline-flex';
        switch (action) {
            case 'number':
                if (numParams) numParams.style.display = 'inline';
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.style.display = 'none';
                if (replaceText) replaceText.style.display = 'none';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'extension':
                if (extParams) extParams.style.display = 'inline';
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.style.display = 'none';
                if (replaceText) replaceText.style.display = 'none';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'removepos':
                if (removePosParams) removePosParams.style.display = 'inline';
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.style.display = 'none';
                if (replaceText) replaceText.style.display = 'none';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'date':
                if (dateParams) dateParams.style.display = 'inline';
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.style.display = 'none';
                if (replaceText) replaceText.style.display = 'none';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'prefix':
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.textContent = '前缀';
                if (replaceText) replaceText.placeholder = '输入前缀...';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'suffix':
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.textContent = '后缀';
                if (replaceText) replaceText.placeholder = '输入后缀...';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'remove':
                if (replaceLabel) replaceLabel.style.display = 'none';
                if (replaceText) replaceText.style.display = 'none';
                if (findLabel) findLabel.textContent = '删除';
                if (findText) findText.placeholder = '要删除的字符...';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            case 'lowercase':
            case 'uppercase':
            case 'capitalize':
            case 'titlecase':
            case 'camelcase':
                if (findLabel) findLabel.style.display = 'none';
                if (findText) findText.style.display = 'none';
                if (replaceLabel) replaceLabel.style.display = 'none';
                if (replaceText) replaceText.style.display = 'none';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'none';
                break;
            default:
                if (findLabel) findLabel.textContent = '查找';
                if (findText) findText.placeholder = '查找';
                if (replaceLabel) replaceLabel.textContent = '替换为';
                if (replaceText) replaceText.placeholder = '替换为';
                if (caseSensitive) caseSensitive.parentElement.style.display = 'inline-flex';
                break;
        }
        document.querySelectorAll('.module-rename select, .module-rename input').forEach(el => {
            if (el.style.display !== 'none') {
                el.style.visibility = 'visible';
                el.style.opacity = '1';
            }
        });
    },

    getParams() {
        const actionEl = document.getElementById('renameAction');
        if (!actionEl) {
            return { action: 'replace', find: '', replace: '', case_sensitive: false };
        }
        const action = actionEl.value;
        const params = { action };
        switch (action) {
            case 'replace':
            case 'regex':
                params.find = document.getElementById('findText')?.value || '';
                params.replace = document.getElementById('replaceText')?.value || '';
                params.case_sensitive = document.getElementById('caseSensitive')?.checked || false;
                break;
            case 'prefix':
            case 'suffix':
                params.replace = document.getElementById('replaceText')?.value || '';
                break;
            case 'remove':
                params.find = document.getElementById('findText')?.value || '';
                break;
            case 'number':
                params.start = parseInt(document.getElementById('startNum')?.value) || 1;
                params.step = parseInt(document.getElementById('stepNum')?.value) || 1;
                params.digits = parseInt(document.getElementById('digitsNum')?.value) || 2;
                params.position = document.getElementById('numberPos')?.value || 'suffix';
                break;
            case 'extension':
                params.ext_action = document.getElementById('extAction')?.value || 'change';
                params.ext_value = document.getElementById('extValue')?.value || '';
                break;
            case 'removepos':
                params.start = parseInt(document.getElementById('removeStart')?.value) || 1;
                params.length = parseInt(document.getElementById('removeLen')?.value) || 1;
                params.from_end = document.getElementById('removeFromEnd')?.checked || false;
                break;
            case 'date':
                params.date_type = document.getElementById('dateType')?.value || 'created';
                params.date_format = document.getElementById('dateFormat')?.value || 'YYYY-MM-DD';
                params.date_pos = document.getElementById('datePos')?.value || 'prefix';
                break;
            default:
                break;
        }
        return params;
    },

    applyRenameAction(oldName, params) {
        const action = params.action;
        let name, ext, newName;
        switch (action) {
            case 'replace':
                const findStr = params.find || '';
                const replaceStr = params.replace || '';
                if (findStr) {
                    newName = params.case_sensitive ?
                        oldName.replace(findStr, replaceStr) :
                        oldName.toLowerCase().replace(findStr.toLowerCase(), replaceStr);
                } else {
                    newName = oldName;
                }
                break;
            case 'regex':
                const regexFind = params.find || '';
                const regexReplace = params.replace || '';
                if (regexFind) {
                    try {
                        const flags = params.case_sensitive ? '' : 'i';
                        newName = oldName.replace(new RegExp(regexFind, flags), regexReplace);
                    } catch (e) {
                        newName = oldName;
                    }
                } else {
                    newName = oldName;
                }
                break;
            case 'prefix':
                newName = (params.replace || '') + oldName;
                break;
            case 'suffix':
                name = getFileNameWithoutExt(oldName);
                ext = getFileExtension(oldName);
                newName = name + (params.replace || '') + ext;
                break;
            case 'lowercase':
                newName = oldName.toLowerCase();
                break;
            case 'uppercase':
                newName = oldName.toUpperCase();
                break;
            case 'capitalize':
                name = getFileNameWithoutExt(oldName);
                ext = getFileExtension(oldName);
                newName = name.charAt(0).toUpperCase() + name.slice(1) + ext;
                break;
            case 'titlecase':
                name = getFileNameWithoutExt(oldName);
                ext = getFileExtension(oldName);
                newName = name.replace(/\w\S*/g, function(txt) {
                    return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
                }) + ext;
                break;
            case 'camelcase':
                name = getFileNameWithoutExt(oldName);
                ext = getFileExtension(oldName);
                const parts = name.replace(/[_\-\s]+/g, ' ').split(' ');
                if (parts.length > 0) {
                    newName = parts[0].toLowerCase() + parts.slice(1).map(function(p) {
                        return p.charAt(0).toUpperCase() + p.slice(1).toLowerCase();
                    }).join('') + ext;
                } else {
                    newName = oldName;
                }
                break;
            case 'extension':
                name = getFileNameWithoutExt(oldName);
                const extAction = params.ext_action || 'change';
                const extValue = params.ext_value || '';
                if (extAction === 'change') {
                    newName = name + (extValue ? '.' + extValue : '');
                } else if (extAction === 'add') {
                    newName = oldName + (extValue ? '.' + extValue : '');
                } else if (extAction === 'remove') {
                    newName = name;
                } else if (extAction === 'replace') {
                    newName = name + (extValue ? '.' + extValue : '');
                } else {
                    newName = oldName;
                }
                break;
            case 'remove':
                const removeStr = params.find || '';
                if (removeStr) {
                    newName = oldName.replace(new RegExp(removeStr, 'g'), '');
                } else {
                    newName = oldName;
                }
                break;
            case 'removepos':
                const startPos = (params.start || 1) - 1;
                const length = params.length || 1;
                const fromEnd = params.from_end || false;
                name = getFileNameWithoutExt(oldName);
                ext = getFileExtension(oldName);
                let pos = startPos;
                if (fromEnd) {
                    pos = name.length - startPos - length + 1;
                }
                if (pos >= 0 && pos < name.length) {
                    newName = name.substring(0, pos) + name.substring(pos + length) + ext;
                } else {
                    newName = oldName;
                }
                break;
            default:
                newName = oldName;
                break;
        }
        return newName;
    },

    applyNumbering(oldName, index, data) {
        const name = getFileNameWithoutExt(oldName);
        const ext = getFileExtension(oldName);
        const start = data.start || 1;
        const step = data.step || 1;
        const digits = data.digits || 2;
        const position = data.position || 'suffix';
        const num = start + (index - 1) * step;
        const numStr = String(num).padStart(digits, '0');
        if (position === 'prefix') {
            return numStr + '_' + oldName;
        } else {
            return name + '_' + numStr + ext;
        }
    },

    applyDate(oldName, filePath, data) {
        const name = getFileNameWithoutExt(oldName);
        const ext = getFileExtension(oldName);
        const dateType = data.date_type || 'created';
        const dateFormat = data.date_format || 'YYYY-MM-DD';
        const position = data.date_pos || 'prefix';
        const timestamp = Date.now();
        const dt = new Date(timestamp);
        const fmtMap = {
            'YYYY-MM-DD': dt.toISOString().split('T')[0],
            'YYYYMMDD': dt.toISOString().split('T')[0].replace(/-/g, ''),
            'YYMMDD': dt.toISOString().split('T')[0].replace(/-/g, '').slice(2)
        };
        const dateStr = fmtMap[dateFormat] || fmtMap['YYYY-MM-DD'];
        if (position === 'prefix') {
            return dateStr + '_' + oldName;
        } else {
            return name + '_' + dateStr + ext;
        }
    },

    autoPreview() {
        const actionSelect = document.getElementById('renameAction');
        if (!actionSelect) return;
        const currentFiles = window.fileList || [];
        if (currentFiles.length === 0) {
            window.renamePreview = {};
            if (typeof renderFiles === 'function') {
                renderFiles(currentFiles);
            }
            return;
        }
        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            window.renamePreview = {};
            if (typeof renderFiles === 'function') {
                renderFiles(currentFiles);
            }
            return;
        }
        const targetFiles = files.filter(f => {
            const fileObj = currentFiles.find(cf => cf.path === f);
            return fileObj && !fileObj.is_dir;
        });
        if (targetFiles.length === 0) {
            window.renamePreview = {};
            if (typeof renderFiles === 'function') {
                renderFiles(currentFiles);
            }
            return;
        }
        const params = this.getParams();
        const action = params.action;
        if (action === 'number') {
            const previewMap = {};
            targetFiles.forEach((filePath, idx) => {
                const oldName = getFileName(filePath);
                const newName = this.applyNumbering(oldName, idx + 1, params);
                if (newName !== oldName) {
                    previewMap[filePath] = newName;
                }
            });
            window.renamePreview = previewMap;
            if (typeof renderFiles === 'function') {
                renderFiles(currentFiles);
            }
            return;
        }
        if (action === 'date') {
            const previewMap = {};
            targetFiles.forEach((filePath) => {
                const oldName = getFileName(filePath);
                const newName = this.applyDate(oldName, filePath, params);
                if (newName !== oldName) {
                    previewMap[filePath] = newName;
                }
            });
            window.renamePreview = previewMap;
            if (typeof renderFiles === 'function') {
                renderFiles(currentFiles);
            }
            return;
        }
        const previewMap = {};
        let hasChanges = false;
        for (let filePath of targetFiles) {
            const oldName = getFileName(filePath);
            const newName = this.applyRenameAction(oldName, params);
            if (newName !== oldName) {
                previewMap[filePath] = newName;
                hasChanges = true;
            }
        }
        window.renamePreview = hasChanges ? previewMap : {};
        if (typeof renderFiles === 'function') {
            renderFiles(currentFiles);
        }
    },

    async execute() {
        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            showLog('⚠️ 请先勾选要重命名的文件', 'warning');
            return;
        }
        const currentFiles = window.fileList || [];
        const targetFiles = files.filter(f => {
            const fileObj = currentFiles.find(cf => cf.path === f);
            return fileObj && !fileObj.is_dir;
        });
        if (targetFiles.length === 0) {
            showLog('⚠️ 选中的文件中没有可重命名的文件', 'warning');
            return;
        }
        let hasChange = false;
        for (let f of targetFiles) {
            if (window.renamePreview[f] && window.renamePreview[f] !== getFileName(f)) {
                hasChange = true;
                break;
            }
        }
        if (!hasChange) {
            showLog('⚠️ 选中的文件没有需要修改的名称', 'warning');
            return;
        }
        const params = this.getParams();
        const action = params.action;
        const filesToRename = [];
        if (action === 'number') {
            let idx = 1;
            for (let f of targetFiles) {
                const oldName = getFileName(f);
                const newName = this.applyNumbering(oldName, idx, params);
                if (newName !== oldName) {
                    filesToRename.push({
                        old_path: f,
                        new_path: f.substring(0, f.lastIndexOf('/') + 1) + newName,
                        old_name: oldName,
                        new_name: newName
                    });
                    idx++;
                }
            }
        } else if (action === 'date') {
            for (let f of targetFiles) {
                const oldName = getFileName(f);
                const newName = this.applyDate(oldName, f, params);
                if (newName !== oldName) {
                    filesToRename.push({
                        old_path: f,
                        new_path: f.substring(0, f.lastIndexOf('/') + 1) + newName,
                        old_name: oldName,
                        new_name: newName
                    });
                }
            }
        } else {
            for (let f of targetFiles) {
                if (window.renamePreview[f] && window.renamePreview[f] !== getFileName(f)) {
                    filesToRename.push({
                        old_path: f,
                        new_path: f.substring(0, f.lastIndexOf('/') + 1) + window.renamePreview[f],
                        old_name: getFileName(f),
                        new_name: window.renamePreview[f]
                    });
                }
            }
        }
        if (filesToRename.length === 0) {
            showLog('⚠️ 选中的文件没有需要修改的名称', 'warning');
            return;
        }
        if (!confirm(`确定要重命名 ${filesToRename.length} 个选中的文件吗？`)) return;
        clearLog();
        showLog('⏳ 开始重命名 ' + filesToRename.length + ' 个选中的文件...', 'info');

        try {
            await OperationManager.execute({
                title: `✏️ 正在重命名 ${filesToRename.length} 个文件...`,
                completeMessage: `✅ 成功重命名 ${filesToRename.length} 个文件`,
                execute: async (progress) => {
                    progress.setTotal(filesToRename.length);
                    const requestData = {
                        action: action,
                        files: filesToRename,
                        ...params
                    };
                    let result;
                    try {
                        result = await apiCall('/api/execute', requestData);
                    } catch (e) {
                        throw new Error('请求失败: ' + e.message);
                    }
                    if (!result) {
                        throw new Error('服务器无响应');
                    }
                    if (result.error) {
                        throw new Error(result.error);
                    }
                    if (result.logs) {
                        result.logs.forEach(log => showLog(log.text, log.type || 'info'));
                    }
                    if (result.stats && result.stats.processed === 0 && !result.error) {
                        showLog('⚠️ 后端没有处理任何文件，请检查文件路径是否正确', 'warning');
                        if (result.logs && result.logs.length > 0) {
                            result.logs.forEach(log => showLog(log.text, log.type || 'info'));
                        }
                        return;
                    }
                    if (result.stats) {
                        showLog('✅ ' + result.stats.message, 'success');
                    }
                    if (result.history && result.history.length > 0) {
                        window.renameHistory.push(...result.history);
                        const undoBtn = document.getElementById('undoBtn');
                        if (undoBtn) undoBtn.disabled = false;
                    }
                    window.renamePreview = {};
                    selectedFiles.clear();
                    await loadFiles(currentPath);
                    this.restoreSelectState();
                    if (result.stats && result.stats.processed > 0) {
                        const findText = document.getElementById('findText');
                        const replaceText = document.getElementById('replaceText');
                        if (findText) findText.value = '';
                        if (replaceText) replaceText.value = '';
                        if (typeof renderFiles === 'function') {
                            renderFiles(window.fileList);
                        }
                        showLog('✅ 输入框已清空，可以继续操作', 'info');
                    }
                }
            });
        } catch (e) {
            console.error('重命名异常:', e);
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(RenameModule);
}
