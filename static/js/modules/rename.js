const RenameModule = {
    name: 'rename',

    init() {
        this.bindEvents();
        this.setupActionToggle();
        setTimeout(() => this.autoPreview(), 200);

        document.addEventListener('filesLoaded', () => {
            setTimeout(() => this.autoPreview(), 100);
        });
        document.addEventListener('selectionChanged', () => {
            setTimeout(() => this.autoPreview(), 50);
        });
    },

    bindEvents() {
        document.getElementById('executeRenameBtn').addEventListener('click', () => this.execute());

        document.getElementById('renameAction').addEventListener('change', () => {
            this.setupActionToggle();
            this.autoPreview();
        });

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
        const action = document.getElementById('renameAction').value;

        document.getElementById('numParams').style.display = 'none';
        document.getElementById('extParams').style.display = 'none';
        document.getElementById('removePosParams').style.display = 'none';
        document.getElementById('dateParams').style.display = 'none';

        const findLabel = document.getElementById('findLabel');
        const findText = document.getElementById('findText');
        const replaceLabel = document.getElementById('replaceLabel');
        const replaceText = document.getElementById('replaceText');
        const caseSensitive = document.getElementById('caseSensitive');

        findLabel.style.display = 'inline';
        findText.style.display = 'inline';
        replaceLabel.style.display = 'inline';
        replaceText.style.display = 'inline';
        caseSensitive.parentElement.style.display = 'inline-flex';

        switch (action) {
            case 'number':
                document.getElementById('numParams').style.display = 'inline';
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.style.display = 'none';
                replaceText.style.display = 'none';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'extension':
                document.getElementById('extParams').style.display = 'inline';
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.style.display = 'none';
                replaceText.style.display = 'none';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'removepos':
                document.getElementById('removePosParams').style.display = 'inline';
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.style.display = 'none';
                replaceText.style.display = 'none';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'date':
                document.getElementById('dateParams').style.display = 'inline';
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.style.display = 'none';
                replaceText.style.display = 'none';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'prefix':
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.textContent = '前缀';
                replaceText.placeholder = '输入前缀...';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'suffix':
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.textContent = '后缀';
                replaceText.placeholder = '输入后缀...';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'remove':
                replaceLabel.style.display = 'none';
                replaceText.style.display = 'none';
                findLabel.textContent = '删除';
                findText.placeholder = '要删除的字符...';
                caseSensitive.parentElement.style.display = 'none';
                break;
            case 'lowercase':
            case 'uppercase':
            case 'capitalize':
            case 'titlecase':
            case 'camelcase':
                findLabel.style.display = 'none';
                findText.style.display = 'none';
                replaceLabel.style.display = 'none';
                replaceText.style.display = 'none';
                caseSensitive.parentElement.style.display = 'none';
                break;
            default:
                findLabel.textContent = '查找';
                findText.placeholder = '查找';
                replaceLabel.textContent = '替换为';
                replaceText.placeholder = '替换为';
                caseSensitive.parentElement.style.display = 'inline-flex';
                break;
        }
    },

    getParams() {
        const action = document.getElementById('renameAction').value;
        const params = { action };

        switch (action) {
            case 'replace':
            case 'regex':
                params.find = document.getElementById('findText').value || '';
                params.replace = document.getElementById('replaceText').value || '';
                params.case_sensitive = document.getElementById('caseSensitive').checked;
                break;
            case 'prefix':
            case 'suffix':
                params.replace = document.getElementById('replaceText').value || '';
                break;
            case 'remove':
                params.find = document.getElementById('findText').value || '';
                break;
            case 'number':
                params.start = parseInt(document.getElementById('startNum').value) || 1;
                params.step = parseInt(document.getElementById('stepNum').value) || 1;
                params.digits = parseInt(document.getElementById('digitsNum').value) || 2;
                params.position = document.getElementById('numberPos').value;
                break;
            case 'extension':
                params.ext_action = document.getElementById('extAction').value;
                params.ext_value = document.getElementById('extValue').value || '';
                break;
            case 'removepos':
                params.start = parseInt(document.getElementById('removeStart').value) || 1;
                params.length = parseInt(document.getElementById('removeLen').value) || 1;
                params.from_end = document.getElementById('removeFromEnd').checked;
                break;
            case 'date':
                params.date_type = document.getElementById('dateType').value;
                params.date_format = document.getElementById('dateFormat').value;
                params.date_pos = document.getElementById('datePos').value;
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
        const files = Array.from(selectedFiles);
        const targetFiles = files.length > 0 ? files : window.fileList.filter(f => !f.is_dir).map(f => f.path);
        const params = this.getParams();

        if (targetFiles.length === 0 || !params.action) {
            window.renamePreview = {};
            renderFiles(window.fileList);
            return;
        }

        if (params.action === 'number' || params.action === 'date') {
            window.renamePreview = {};
            renderFiles(window.fileList);
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
        renderFiles(window.fileList);
    },

    async execute() {
        let files = Array.from(selectedFiles);
        if (files.length === 0) {
            files = window.fileList.filter(f => !f.is_dir).map(f => f.path);
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
                document.getElementById('undoBtn').disabled = false;
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
