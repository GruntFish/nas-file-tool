const RenameModule = {
    name: 'rename',

    init() {
        this.bindEvents();
        this.setupActionToggle();
        // 延迟执行预览，确保 DOM 渲染完成
        setTimeout(() => this.autoPreview(), 300);

        document.addEventListener('filesLoaded', () => {
            setTimeout(() => this.autoPreview(), 200);
        });
        document.addEventListener('selectionChanged', () => {
            setTimeout(() => this.autoPreview(), 100);
        });
    },

    bindEvents() {
        const executeBtn = document.getElementById('executeRenameBtn');
        if (executeBtn) {
            executeBtn.addEventListener('click', () => this.execute());
        }

        const actionSelect = document.getElementById('renameAction');
        if (actionSelect) {
            actionSelect.addEventListener('change', () => {
                this.setupActionToggle();
                this.autoPreview();
            });
        }

        ['findText', 'replaceText', 'caseSensitive', 'startNum', 'stepNum', 'digitsNum',
            'numberPos', 'extAction', 'extValue', 'removeStart', 'removeLen', 'removeFromEnd',
            'dateType', 'dateFormat', 'datePos'
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', () => this.autoPreview());
                el.addEventListener('change', () => this.autoPreview());
            }
        });
    },

    setupActionToggle() {
        const actionEl = document.getElementById('renameAction');
        if (!actionEl) return;
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
        if (findText) findText.style.display = 'inline';
        if (replaceLabel) replaceLabel.style.display = 'inline';
        if (replaceText) replaceText.style.display = 'inline';
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
    },

    getParams() {
        const actionEl = document.getElementById('renameAction');
        // 如果元素不存在，返回默认参数
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

    autoPreview() {
        // 如果 renameAction 不存在，说明模块还没加载完成，跳过
        if (!document.getElementById('renameAction')) {
            return;
        }

        const files = Array.from(selectedFiles);
        const targetFiles = files.length > 0 ? files : window.fileList ? window.fileList.filter(f => !f.is_dir).map(f => f.path) : [];
        const params = this.getParams();

        if (targetFiles.length === 0 || !params.action) {
            window.renamePreview = {};
            if (typeof renderFiles === 'function') {
                renderFiles(window.fileList || []);
            }
            return;
        }

        if (params.action === 'number' || params.action === 'date') {
            window.renamePreview = {};
            if (typeof renderFiles === 'function') {
                renderFiles(window.fileList || []);
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
            renderFiles(window.fileList || []);
        }
    },

    async execute() {
        let files = Array.from(selectedFiles);
        if (files.length === 0) {
            files = window.fileList ? window.fileList.filter(f => !f.is_dir).map(f => f.path) : [];
        }
        if (files.length === 0) {
            showLog('⚠️ 当前目录没有文件', 'warning');
            return;
        }

        let hasChange = false;
        for (let f of files) {
            if (window.renamePreview[f] && window.renamePreview[f] !== getFileName(f)) {
                hasChange = true;
                break;
            }
        }
        if (!hasChange) {
            showLog('⚠️ 没有文件需要修改', 'warning');
            return;
        }

        const params = this.getParams();
        const filesToRename = [];
        for (let f of files) {
            if (window.renamePreview[f] && window.renamePreview[f] !== getFileName(f)) {
                filesToRename.push({
                    old_path: f,
                    new_path: f.substring(0, f.lastIndexOf('/') + 1) + window.renamePreview[f],
                    old_name: getFileName(f),
                    new_name: window.renamePreview[f]
                });
            }
        }

        if (filesToRename.length === 0) {
            showLog('⚠️ 没有文件需要修改', 'warning');
            return;
        }

        if (!confirm('确定要重命名 ' + filesToRename.length + ' 个文件吗？')) return;

        clearLog();
        showLog('⏳ 开始重命名 ' + filesToRename.length + ' 个文件...', 'info');

        try {
            const result = await apiCall('/api/execute', {
                action: params.action,
                files: filesToRename,
                ...params
            });
            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
            if (result.logs) result.logs.forEach(log => showLog(log.text, log.type || 'info'));
            if (result.stats) showLog('✅ ' + result.stats.message, 'success');
            if (result.history && result.history.length > 0) {
                window.renameHistory.push(...result.history);
                const undoBtn = document.getElementById('undoBtn');
                if (undoBtn) undoBtn.disabled = false;
            }
            window.renamePreview = {};
            selectedFiles.clear();
            await loadFiles(currentPath);
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(RenameModule);
}
