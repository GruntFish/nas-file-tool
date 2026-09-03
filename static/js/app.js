// 模块注册器
const ModuleRegistry = {
    modules: {},
    currentModule: null,

    register(module) {
        this.modules[module.name] = module;
    },

    async load(name) {
        if (this.currentModule === name && this.modules[name]?.loaded) return;
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
    }
};

window.ModuleRegistry = ModuleRegistry;

// ===== 全局状态 =====
let currentPath = '/';
let fileList = [];
let selectedFiles = new Set();
let renamePreview = {};
let renameHistory = [];
let fullTreeData = [];

// ===== API 调用 =====
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

// ===== 工具函数 =====
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
    logArea.classList.add('show');
    const div = document.createElement('div');
    div.className = 'log-line ' + (type || 'info');
    div.textContent = msg;
    logArea.appendChild(div);
    logArea.scrollTop = logArea.scrollHeight;
}

function clearLog() {
    const logArea = document.getElementById('logArea');
    logArea.innerHTML = '';
    logArea.classList.remove('show');
}

function openModal(html) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay show';
    overlay.innerHTML = html;
    overlay.addEventListener('click', function(e) {
        if (e.target === this) this.remove();
    });
    document.body.appendChild(overlay);
    return overlay;
}

function closeModal() {
    document.querySelectorAll('.modal-overlay.show').forEach(el => el.remove());
}

// ===== 目录树 =====
async function loadTree(path) {
    try {
        const result = await fetchTree(path);
        if (result.error) throw new Error(result.error);
        fullTreeData = result.tree || [];
        renderTree(fullTreeData, document.getElementById('treeContainer'));
    } catch (err) {
        console.error(err);
    }
}

function renderTree(nodes, container) {
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
        if (node.path === currentPath) item.classList.add('active');
        const hasChildren = node.children && node.children.length > 0;
        item.innerHTML =
            `<span class="icon">📁</span><span class="name">${escapeHtml(node.name)}</span>${hasChildren ? '<span class="arrow open">▼</span>' : ''}`;
        item.addEventListener('click', function(e) {
            if (e.target.classList.contains('arrow')) return;
            currentPath = node.path;
            loadFiles(node.path);
        });
        container.appendChild(item);
        if (hasChildren) {
            const childContainer = document.createElement('div');
            childContainer.className = 'tree-children';
            if (currentPath.startsWith(node.path)) {
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

// ===== 文件列表 =====
async function loadFiles(path) {
    try {
        const result = await fetchFiles(path);
        if (result.error) throw new Error(result.error);
        fileList = result.files || [];
        renderFiles(fileList);
        document.getElementById('currentPathDisplay').textContent = path;
        document.getElementById('fileCountDisplay').textContent = fileList.length + ' 项';
        document.dispatchEvent(new CustomEvent('filesLoaded', { detail: { files: fileList } }));
    } catch (err) {
        showLog('❌ 加载失败: ' + err.message, 'error');
    }
}

function renderFiles(files) {
    const tbody = document.getElementById('fileTableBody');
    tbody.innerHTML = '';
    if (!files || files.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="6">📭 此目录为空</td></tr>';
        return;
    }
    fileList = files;
    files.sort((a, b) => {
        if (a.is_dir && !b.is_dir) return -1;
        if (!a.is_dir && b.is_dir) return 1;
        return a.name.localeCompare(b.name);
    });
    document.getElementById('fileCountDisplay').textContent = files.length + ' 项';
    files.forEach(file => {
        const tr = document.createElement('tr');
        const isDir = file.is_dir;
        const icon = isDir ? '📁' : '📄';
        const size = isDir ? '' : formatSize(file.size);
        const date = file.modified ? new Date(file.modified * 1000).toLocaleString() : '-';
        const newName = renamePreview[file.path] || file.name;
        const isChanged = newName !== file.name && !isDir;
        const statusText = isDir ? '📁 文件夹' : (isChanged ? '🔄 修改' : '✓ 不变');
        const statusClass = isChanged ? 'changed' : 'ok';
        const checked = selectedFiles.has(file.path) ? 'checked' : '';
        tr.innerHTML =
            `<td class="checkbox-col"><input type="checkbox" value="${escapeHtml(file.path)}" ${checked}></td>` +
            `<td class="name-col${isDir ? ' folder-row' : ''}">${icon} ${escapeHtml(file.name)}</td>` +
            `<td class="new-name-col${isChanged && !isDir ? '' : ' unchanged'}">${isDir ? '-' : escapeHtml(newName)}</td>` +
            `<td class="size-col">${size}</td>` +
            `<td class="date-col">${date}</td>` +
            `<td class="status-col ${statusClass}">${statusText}</td>`;
        const cb = tr.querySelector('input[type="checkbox"]');
        cb.addEventListener('change', function() {
            if (this.checked) {
                selectedFiles.add(file.path);
                tr.classList.add('selected');
            } else {
                selectedFiles.delete(file.path);
                tr.classList.remove('selected');
            }
            updateSelectedInfo();
            document.dispatchEvent(new CustomEvent('selectionChanged', { detail: { selected: selectedFiles } }));
        });
        tbody.appendChild(tr);
    });
    updateSelectedInfo();
}

function updateSelectedInfo() {
    const count = selectedFiles.size;
    document.getElementById('selectedInfo').textContent = count > 0 ? `✅ 已选 ${count} 项` : '';
}

// ===== DOM 初始化 =====
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('selectAllBtn').addEventListener('click', function() {
        document.querySelectorAll('#fileTableBody input[type="checkbox"]').forEach(cb => {
            cb.checked = true;
            cb.dispatchEvent(new Event('change'));
        });
    });
    document.getElementById('clearAllBtn').addEventListener('click', function() {
        document.querySelectorAll('#fileTableBody input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
            cb.dispatchEvent(new Event('change'));
        });
    });
    document.getElementById('selectAll').addEventListener('change', function() {
        document.querySelectorAll('#fileTableBody input[type="checkbox"]').forEach(cb => {
            cb.checked = this.checked;
            cb.dispatchEvent(new Event('change'));
        });
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
});

document.getElementById('undoBtn')?.addEventListener('click', async function() {
    if (renameHistory.length === 0) return;
    try {
        const result = await apiCall('/api/undo', {});
        if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
        showLog('↩ ' + result.message, 'success');
        renameHistory.pop();
        if (renameHistory.length === 0) this.disabled = true;
        renamePreview = {};
        selectedFiles.clear();
        await loadFiles(currentPath);
    } catch (e) { showLog('❌ ' + e.message, 'error'); }
});
