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

// ===== openModal - 保留 CSS 类样式 =====
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

    // ===== 只设置定位样式，不覆盖 CSS 类 =====
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

    overlay.addEventListener('click', function(e) {
        if (e.target === this) this.remove();
    });

    document.body.prepend(overlay);
    return overlay;
}

function closeModal() {
    document.querySelectorAll('.modal-overlay.show').forEach(el => el.remove());
}

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
            `<td class="new-name-col${isChanged && !isDir ? '' : ' unchanged'}">${isDir ? '-' : escapeHtml(newName)}</td>` +
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
