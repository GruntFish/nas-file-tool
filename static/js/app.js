// static/js/app.js
// 模块注册器
const ModuleRegistry = {
    modules: {},
    currentModule: null,

    register(module) {
        this.modules[module.name] = module;
    },

    async load(name) {
        if (this.currentModule === name && this.modules[name]?.loaded) return;

        window.selectedFiles.clear();
        updateSelectedInfo();
        window.renamePreview = {};
        closeModal();

        const selectAllCheckbox = document.getElementById('selectAll');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }

        document.querySelectorAll('#fileTableBody tr.selected').forEach(tr => {
            tr.classList.remove('selected');
        });
        document.querySelectorAll('#fileTableBody input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });

        if (this.currentModule && this.modules[this.currentModule] && this.modules[this.currentModule].destroy) {
            this.modules[this.currentModule].destroy();
        }

        this.currentModule = name;

        const container = document.getElementById('moduleContent');
        if (!container) return;

        try {
            const res = await fetch(`/modules/${name}.html`);
            if (!res.ok) throw new Error('模块不存在');
            const html = await res.text();
            container.innerHTML = html;

            if (this.modules[name] && this.modules[name].init) {
                this.modules[name].init();
                this.modules[name].loaded = true;
            }
        } catch (e) {
            container.innerHTML = `<div style="padding:20px;color:#fc8181;">❌ 模块加载失败: ${e.message}</div>`;
        }

        if (typeof renderFiles === 'function') {
            renderFiles(window.fileList);
        }

        // ===== 切换模块后重新应用正则过滤 =====
        if (window.filterRegex) {
            const checkboxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled)');
            try {
                const regex = new RegExp(window.filterRegex);
                checkboxes.forEach(cb => {
                    const fileName = getFileName(cb.value);
                    const isMatch = regex.test(fileName);
                    cb.checked = isMatch;
                    const tr = cb.closest('tr');
                    if (tr) {
                        isMatch ? tr.classList.add('selected') : tr.classList.remove('selected');
                    }
                    if (isMatch) {
                        window.selectedFiles.add(cb.value);
                    } else {
                        window.selectedFiles.delete(cb.value);
                    }
                });
            } catch (e) {
                // 正则无效，忽略
            }
            updateSelectedInfo();
            updateSelectAllState();
        }
    }
};

window.ModuleRegistry = ModuleRegistry;

window.currentPath = '/';
window.fileList = [];
window.selectedFiles = new Set();
window.renamePreview = {};
window.renameHistory = [];
window.fullTreeData = [];
window.filterRegex = null;

async function apiCall(endpoint, data) {
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return res.json();
}

async function fetchTree(path) { return apiCall('/api/tree', { path }); }
async function fetchFiles(path) { return apiCall('/api/files', { path }); }
async function dedupFiles(data) { return apiCall('/api/dedup', data); }

function getFileName(filePath) {
    if (!filePath) return '';
    const parts = filePath.split('/');
    return parts[parts.length - 1];
}

function getFileExtension(fileName) {
    const idx = fileName.lastIndexOf('.');
    if (idx > 0) return fileName.substring(idx);
    return '';
}

function getFileNameWithoutExt(fileName) {
    const idx = fileName.lastIndexOf('.');
    if (idx > 0) return fileName.substring(0, idx);
    return fileName;
}

function formatSize(bytes) {
    if (!bytes) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return bytes.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLog(msg, type) {
    const logArea = document.getElementById('logArea');
    if (!logArea) return;
    logArea.classList.add('show');
    const div = document.createElement('div');
    div.className = 'log-line ' + (type || 'info');
    div.textContent = msg;
    logArea.appendChild(div);
    logArea.scrollTop = logArea.scrollHeight;
}

function clearLog() {
    const logArea = document.getElementById('logArea');
    if (!logArea) return;
    logArea.innerHTML = '';
    logArea.classList.remove('show');
}

// ===== openModal - 修复弹窗样式 =====
function openModal(html) {
    const existing = document.querySelectorAll('.modal-overlay');
    existing.forEach(el => el.remove());

    let overlay;
    if (html && html.includes('modal-overlay')) {
        const temp = document.createElement('div');
        temp.innerHTML = html;
        overlay = temp.firstElementChild;
        if (overlay) {
            overlay.classList.add('show');
        }
    } else {
        overlay = document.createElement('div');
        overlay.className = 'modal-overlay show';
        if (html) {
            overlay.innerHTML = html;
        }
    }

    if (!overlay) return null;

    // ===== 设置遮罩层样式 =====
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.right = '0';
    overlay.style.bottom = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.zIndex = '999999';
    overlay.style.display = 'flex';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';
    overlay.style.margin = '0';
    overlay.style.padding = '0';
    overlay.style.background = 'rgba(0, 0, 0, 0.6)';

    // ===== 强制弹窗内部样式 =====
    const modal = overlay.querySelector('.modal');
    if (modal) {
        modal.style.background = '#1a1d27';
        modal.style.borderRadius = '12px';
        modal.style.padding = '24px';
        modal.style.maxWidth = '550px';
        modal.style.width = '90%';
        modal.style.maxHeight = '85vh';
        modal.style.overflowY = 'auto';
        modal.style.border = '1px solid #2d313e';
        modal.style.boxShadow = '0 20px 60px rgba(0, 0, 0, 0.8)';
        modal.style.position = 'relative';
        modal.style.margin = 'auto';
        modal.style.color = '#e4e6eb';

        // 标题
        const h2 = modal.querySelector('h2');
        if (h2) {
            h2.style.color = '#e4e6eb';
            h2.style.fontSize = '17px';
            h2.style.marginBottom = '12px';
        }

        // 所有文本
        const allText = modal.querySelectorAll('p, div, span, label, li');
        allText.forEach(el => {
            if (!el.style.color && !el.closest('.btn-row') && !el.closest('button')) {
                el.style.color = '#b5b9c9';
            }
        });

        // 按钮
        const btns = modal.querySelectorAll('.btn-confirm, .btn-cancel');
        btns.forEach(btn => {
            if (btn.classList.contains('btn-confirm')) {
                btn.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
                btn.style.color = '#fff';
            } else if (btn.classList.contains('btn-cancel')) {
                btn.style.background = '#2d313e';
                btn.style.color = '#b5b9c9';
            }
            btn.style.border = '0';
            btn.style.padding = '8px';
            btn.style.borderRadius = '6px';
            btn.style.fontSize = '13px';
            btn.style.fontWeight = '600';
            btn.style.cursor = 'pointer';
            btn.style.fontFamily = 'inherit';
            btn.style.flex = '1';
        });

        // 按钮行
        const btnRow = modal.querySelector('.btn-row');
        if (btnRow) {
            btnRow.style.display = 'flex';
            btnRow.style.gap = '10px';
            btnRow.style.marginTop = '14px';
        }

        // 表单组
        const formGroups = modal.querySelectorAll('.form-group');
        formGroups.forEach(fg => {
            fg.style.marginBottom = '8px';
            const label = fg.querySelector('label');
            if (label) {
                label.style.display = 'block';
                label.style.color = '#8b8fa3';
                label.style.fontSize = '12px';
                label.style.fontWeight = '600';
                label.style.marginBottom = '2px';
            }
            const input = fg.querySelector('input, select');
            if (input) {
                input.style.width = '100%';
                input.style.padding = '5px 8px';
                input.style.background = '#14171f';
                input.style.border = '1px solid #2d313e';
                input.style.borderRadius = '6px';
                input.style.color = '#e4e6eb';
                input.style.fontSize = '13px';
                input.style.outline = '0';
                input.style.fontFamily = 'inherit';
            }
        });

        // 预览列表
        const previewList = modal.querySelector('.preview-list');
        if (previewList) {
            previewList.style.maxHeight = '120px';
            previewList.style.overflowY = 'auto';
            previewList.style.background = '#14171f';
            previewList.style.borderRadius = '6px';
            previewList.style.padding = '4px 8px';
            previewList.style.margin = '4px 0';
            previewList.style.fontSize = '12px';
            previewList.style.fontFamily = 'monospace';
            previewList.style.color = '#b5b9c9';
        }
    }

    overlay.addEventListener('click', function(e) {
        if (e.target === this) this.remove();
    });

    document.body.prepend(overlay);
    return overlay;
}

function closeModal() {
    document.querySelectorAll('.modal-overlay.show').forEach(el => el.remove());
}

// ===== 操作锁和进度条管理 =====
const OperationManager = {
    _isRunning: false,
    _queue: [],
    _currentProgress: null,

    isRunning() { return this._isRunning; },

    getStatus() {
        return { isRunning: this._isRunning, queueLength: this._queue.length };
    },

    async execute(options) {
        return new Promise((resolve, reject) => {
            this._queue.push({ options, resolve, reject });
            this._processQueue();
        });
    },

    async _processQueue() {
        if (this._isRunning || this._queue.length === 0) return;

        this._isRunning = true;
        const { options, resolve, reject } = this._queue.shift();

        this._setButtonsEnabled(false);

        let progress = null;
        try {
            progress = new ProgressBar({
                title: options.title || '处理中...',
                onCancel: () => {
                    if (options.onCancel) options.onCancel();
                    this._cancelCurrent();
                }
            });
            this._currentProgress = progress;
            progress.show();

            const result = await options.execute(progress);
            progress.complete(options.completeMessage || '✅ 处理完成');
            resolve(result);

        } catch (e) {
            if (progress) {
                progress.error(e.message || '操作失败');
            }
            reject(e);
        } finally {
            this._isRunning = false;
            this._currentProgress = null;
            this._setButtonsEnabled(true);
            setTimeout(() => this._processQueue(), 300);
        }
    },

    _cancelCurrent() {
        if (this._currentProgress) {
            this._currentProgress.hide();
            this._currentProgress = null;
        }
        this._isRunning = false;
        this._setButtonsEnabled(true);
        this._queue = [];
        showLog('⏹️ 操作已取消', 'warning');
    },

    _setButtonsEnabled(enabled) {
        const btnSelectors = [
            '#executeRenameBtn', '#moveCopyConfirmBtn', '#deleteConfirmBtn',
            '#dedupConfirmBtn', '#classifyConfirmBtn', '#chmodConfirmBtn',
            '#mediaCompressConfirm', '#mediaConvertConfirm', '#mediaResizeConfirm'
        ];
        btnSelectors.forEach(selector => {
            const btn = document.querySelector(selector);
            if (btn) {
                btn.disabled = !enabled;
                btn.style.opacity = enabled ? '1' : '0.5';
                btn.style.cursor = enabled ? 'pointer' : 'not-allowed';
            }
        });
        document.querySelectorAll('.module-dedup button, .module-delete button, .module-classify button, .module-chmod button, .module-media button, .module-move-copy button').forEach(btn => {
            if (!btn.closest('.module-rename')) {
                btn.disabled = !enabled;
                btn.style.opacity = enabled ? '1' : '0.5';
                btn.style.cursor = enabled ? 'pointer' : 'not-allowed';
            }
        });
    }
};

window.OperationManager = OperationManager;

async function loadTree(path) {
    try {
        const result = await fetchTree(path);
        if (result.error) throw new Error(result.error);
        window.fullTreeData = result.tree || [];
        renderTree(window.fullTreeData, document.getElementById('treeContainer'));
    } catch (err) {
        console.error(err);
    }
}

function renderTree(nodes, container) {
    if (!container) return;
    container.innerHTML = '';
    if (!nodes || nodes.length === 0) {
        container.innerHTML = '<div style="padding:20px;text-align:center;color:#4a4e62;font-size:13px;">📭 没有子目录</div>';
        return;
    }
    const folders = nodes.filter(n => n.is_dir);
    if (folders.length === 0) {
        container.innerHTML = '<div style="padding:20px;text-align:center;color:#4a4e62;font-size:13px;">📭 没有子目录</div>';
        return;
    }
    folders.sort((a, b) => a.name.localeCompare(b.name));
    folders.forEach(node => {
        const item = document.createElement('div');
        item.className = 'tree-item';
        if (node.path === window.currentPath) item.classList.add('active');
        const hasChildren = node.children && node.children.length > 0;
        item.innerHTML =
            `<span class="icon">📁</span><span class="name">${escapeHtml(node.name)}</span>${hasChildren ? '<span class="arrow open">▼</span>' : ''}`;
        item.addEventListener('click', function(e) {
            if (e.target.classList.contains('arrow')) return;
            window.currentPath = node.path;
            loadFiles(node.path);
        });
        container.appendChild(item);
        if (hasChildren) {
            const childContainer = document.createElement('div');
            childContainer.className = 'tree-children';
            if (window.currentPath.startsWith(node.path)) {
                childContainer.classList.remove('collapsed');
            } else {
                childContainer.classList.add('collapsed');
            }
            renderTree(node.children, childContainer);
            container.appendChild(childContainer);
            const arrow = item.querySelector('.arrow');
            if (arrow) {
                arrow.addEventListener('click', function(e) {
                    e.stopPropagation();
                    childContainer.classList.toggle('collapsed');
                    arrow.classList.toggle('open');
                });
            }
        }
    });
}

function updateSelectAllState() {
    const selectAll = document.getElementById('selectAll');
    if (!selectAll) return;

    const checkboxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled)');
    const checkedBoxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled):checked');

    if (checkboxes.length === 0) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
        return;
    }

    if (checkedBoxes.length === checkboxes.length) {
        selectAll.checked = true;
        selectAll.indeterminate = false;
    } else if (checkedBoxes.length === 0) {
        selectAll.checked = false;
        selectAll.indeterminate = false;
    } else {
        selectAll.checked = false;
        selectAll.indeterminate = true;
    }
}

async function loadFiles(path) {
    try {
        const result = await fetchFiles(path);
        if (result.error) throw new Error(result.error);
        window.selectedFiles.clear();
        window.fileList = result.files || [];
        renderFiles(window.fileList);
        document.getElementById('currentPathDisplay').textContent = path;
        document.getElementById('fileCountDisplay').textContent = window.fileList.length + ' 项';
        document.dispatchEvent(new CustomEvent('filesLoaded', { detail: { files: window.fileList } }));
    } catch (err) {
        showLog('❌ 加载失败: ' + err.message, 'error');
    }
}

function renderFiles(files) {
    const tbody = document.getElementById('fileTableBody');
    if (!tbody) return;

    const fileData = files || window.fileList || [];

    // ===== 判断当前是否是重命名模块 =====
    const isRenameModule = ModuleRegistry.currentModule === 'rename';

    // ===== 控制"新名称"列的显示 =====
    const thead = document.querySelector('#fileListContainer thead tr');
    if (thead) {
        const newNameTh = thead.querySelector('.new-name-col');
        if (newNameTh) {
            newNameTh.style.display = isRenameModule ? '' : 'none';
        }
    }

    let filteredFiles = fileData;
    if (window.filterRegex) {
        try {
            const regex = new RegExp(window.filterRegex);
            filteredFiles = fileData.filter(f => {
                if (f.is_dir) return true;
                return regex.test(f.name);
            });
        } catch (e) {
            filteredFiles = fileData;
        }
    }

    const filterCountEl = document.getElementById('filterCount');
    if (filterCountEl) {
        const total = fileData.length;
        const matched = filteredFiles.length;
        if (window.filterRegex && matched < total) {
            filterCountEl.textContent = `🔍 ${matched}/${total}`;
        } else {
            filterCountEl.textContent = '';
        }
    }

    tbody.innerHTML = '';
    if (!filteredFiles || filteredFiles.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="6">📭 此目录为空</td></tr>';
        const selectAll = document.getElementById('selectAll');
        if (selectAll) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        }
        return;
    }

    filteredFiles.sort((a, b) => {
        if (a.is_dir && !b.is_dir) return -1;
        if (!a.is_dir && b.is_dir) return 1;
        return a.name.localeCompare(b.name);
    });

    filteredFiles.forEach(file => {
        const tr = document.createElement('tr');
        const isDir = file.is_dir;
        const icon = isDir ? '📁' : '📄';
        const size = isDir ? '' : formatSize(file.size);
        const date = file.modified ? new Date(file.modified * 1000).toLocaleString() : '-';
        const newName = window.renamePreview[file.path] || file.name;
        const isChanged = newName !== file.name && !isDir;
        const statusText = isDir ? '📁 文件夹' : (isChanged ? '🔄 修改' : '✓ 不变');
        const statusClass = isChanged ? 'changed' : 'ok';

        const isChecked = window.selectedFiles.has(file.path) ||
            window.selectedFiles.has(file.path.replace(/^\//, '')) ||
            window.selectedFiles.has('/' + file.path);
        const checked = isChecked ? 'checked' : '';

        tr.innerHTML =
            `<td class="checkbox-col"><input type="checkbox" value="${escapeHtml(file.path)}" ${checked}></td>` +
            `<td class="name-col${isDir ? ' folder-row' : ''}">${icon} ${escapeHtml(file.name)}</td>` +
            `<td class="new-name-col${isChanged && !isDir ? '' : ' unchanged'}" style="${isRenameModule ? '' : 'display:none;'}">${isDir ? '-' : escapeHtml(newName)}</td>` +
            `<td class="size-col">${size}</td>` +
            `<td class="date-col">${date}</td>` +
            `<td class="status-col ${statusClass}">${statusText}</td>`;

        const cb = tr.querySelector('input[type="checkbox"]');
        if (!isDir) {
            if (isChecked) {
                tr.classList.add('selected');
                if (!window.selectedFiles.has(file.path)) {
                    window.selectedFiles.add(file.path);
                }
            }
            cb.addEventListener('change', function() {
                if (this.checked) {
                    window.selectedFiles.add(file.path);
                    tr.classList.add('selected');
                } else {
                    window.selectedFiles.delete(file.path);
                    tr.classList.remove('selected');
                }
                updateSelectedInfo();
                updateSelectAllState();
                document.dispatchEvent(new CustomEvent('selectionChanged', {
                    detail: { selected: window.selectedFiles }
                }));
            });
        } else {
            cb.disabled = true;
        }

        tbody.appendChild(tr);
    });

    updateSelectedInfo();
    updateSelectAllState();
}

function updateSelectedInfo() {
    const count = window.selectedFiles.size;
    const el = document.getElementById('selectedInfo');
    if (el) {
        el.textContent = count > 0 ? `✅ 已选 ${count} 项` : '';
    }
    document.querySelectorAll('[id$="SelectedCount"]').forEach(el => {
        el.textContent = count;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const selectAllBtn = document.getElementById('selectAllBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const selectAll = document.getElementById('selectAll');

    const filterInput = document.getElementById('filterInput');
    if (filterInput) {
        filterInput.addEventListener('input', function() {
            const val = this.value.trim();
            window.filterRegex = val || null;

            renderFiles(window.fileList);

            const checkboxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled)');

            if (val === '') {
                checkboxes.forEach(cb => {
                    cb.checked = false;
                    window.selectedFiles.delete(cb.value);
                    const tr = cb.closest('tr');
                    if (tr) tr.classList.remove('selected');
                });
            } else {
                try {
                    const regex = new RegExp(val);
                    checkboxes.forEach(cb => {
                        const fileName = getFileName(cb.value);
                        const isMatch = regex.test(fileName);
                        cb.checked = isMatch;
                        const tr = cb.closest('tr');
                        if (tr) {
                            isMatch ? tr.classList.add('selected') : tr.classList.remove('selected');
                        }
                        if (isMatch) {
                            window.selectedFiles.add(cb.value);
                        } else {
                            window.selectedFiles.delete(cb.value);
                        }
                    });
                } catch (e) {
                    checkboxes.forEach(cb => {
                        cb.checked = false;
                        window.selectedFiles.delete(cb.value);
                        const tr = cb.closest('tr');
                        if (tr) tr.classList.remove('selected');
                    });
                }
            }

            updateSelectedInfo();
            updateSelectAllState();
            document.dispatchEvent(new CustomEvent('selectionChanged', {
                detail: { selected: window.selectedFiles }
            }));
        });
    }

    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled)');
            checkboxes.forEach(cb => {
                cb.checked = true;
                window.selectedFiles.add(cb.value);
                const tr = cb.closest('tr');
                if (tr) tr.classList.add('selected');
            });
            updateSelectedInfo();
            updateSelectAllState();
            document.dispatchEvent(new CustomEvent('selectionChanged', {
                detail: { selected: window.selectedFiles }
            }));
        });
    }

    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled)');
            checkboxes.forEach(cb => {
                cb.checked = false;
                window.selectedFiles.delete(cb.value);
                const tr = cb.closest('tr');
                if (tr) tr.classList.remove('selected');
            });
            updateSelectedInfo();
            updateSelectAllState();
            document.dispatchEvent(new CustomEvent('selectionChanged', {
                detail: { selected: window.selectedFiles }
            }));
        });
    }

    if (selectAll) {
        selectAll.addEventListener('change', function() {
            const isChecked = this.checked;
            const checkboxes = document.querySelectorAll('#fileTableBody input[type="checkbox"]:not(:disabled)');
            checkboxes.forEach(cb => {
                cb.checked = isChecked;
                const tr = cb.closest('tr');
                if (tr) {
                    if (isChecked) {
                        tr.classList.add('selected');
                    } else {
                        tr.classList.remove('selected');
                    }
                }
                if (isChecked) {
                    window.selectedFiles.add(cb.value);
                } else {
                    window.selectedFiles.delete(cb.value);
                }
            });
            this.indeterminate = false;
            updateSelectedInfo();
            document.dispatchEvent(new CustomEvent('selectionChanged', {
                detail: { selected: window.selectedFiles }
            }));
        });
    }

    // ===== 键盘快捷键 =====
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'a') {
            e.preventDefault();
            const btn = document.getElementById('selectAllBtn');
            if (btn) btn.click();
        }
        if (e.key === 'Escape') {
            const btn = document.getElementById('clearAllBtn');
            if (btn) btn.click();
        }
        if (e.ctrlKey && e.key === 'z') {
            e.preventDefault();
            const undoBtn = document.getElementById('undoBtn');
            if (undoBtn && !undoBtn.disabled) undoBtn.click();
        }
    });

    loadTree('/');
    loadFiles('/');

    setTimeout(() => {
        ModuleRegistry.load('rename');
    }, 300);

    document.querySelectorAll('.menu-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.menu-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            ModuleRegistry.load(this.dataset.module);
        });
    });

    const undoBtn = document.getElementById('undoBtn');
    if (undoBtn) {
        undoBtn.addEventListener('click', async function() {
            if (window.renameHistory.length === 0) return;
            try {
                const result = await apiCall('/api/undo', {});
                if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
                showLog('↩ ' + result.message, 'success');
                window.renameHistory.pop();
                if (window.renameHistory.length === 0) this.disabled = true;
                window.renamePreview = {};
                window.selectedFiles.clear();
                await loadFiles(window.currentPath);
            } catch (e) { showLog('❌ ' + e.message, 'error'); }
        });
    }

    document.getElementById('refreshTreeBtn')?.addEventListener('click', function() {
        loadTree(window.currentPath);
    });
});
