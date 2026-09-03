// static/js/modules/rename.js

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

    // ===== 【新增】打印调试信息 =====
    console.log('准备重命名文件:', filesToRename);
    console.log('参数:', params);

    if (!confirm(`确定要重命名 ${filesToRename.length} 个选中的文件吗？`)) return;

    clearLog();
    showLog('⏳ 开始重命名 ' + filesToRename.length + ' 个选中的文件...', 'info');

    try {
        // ===== 【新增】构建请求数据 =====
        const requestData = {
            action: action,
            files: filesToRename,
            ...params
        };
        console.log('发送请求:', requestData);

        const result = await apiCall('/api/execute', requestData);
        console.log('后端返回:', result);

        if (result.error) {
            showLog('❌ ' + result.error, 'error');
            return;
        }

        // ===== 【修复】检查返回结果 =====
        if (result.stats && result.stats.processed === 0 && !result.error) {
            showLog('⚠️ 后端没有处理任何文件，请检查文件路径是否正确', 'warning');
            // 显示详细的返回信息帮助调试
            if (result.logs && result.logs.length > 0) {
                result.logs.forEach(log => showLog(log.text, log.type || 'info'));
            }
            // 不要清空输入框，让用户可以重试
            return;
        }

        if (result.logs) {
            result.logs.forEach(log => showLog(log.text, log.type || 'info'));
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

        // ===== 【修复】只有成功处理了文件才清空输入框 =====
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

    } catch (e) {
        console.error('重命名异常:', e);
        showLog('❌ ' + e.message, 'error');
    }
}
