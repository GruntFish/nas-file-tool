// static/js/modules/scheduler.js
const SchedulerModule = {
    name: 'scheduler',

    init() {
        document.getElementById('schedulerAddBtn').addEventListener('click', () => this.addTask());
        document.getElementById('schedulerRefreshBtn').addEventListener('click', () => this.loadTasks());
        this.loadTasks();
    },

    destroy() {
        closeModal();
        selectedFiles.clear();
        updateSelectedInfo();
        if (typeof renderFiles === 'function' && window.fileList) {
            renderFiles(window.fileList);
        }
    },

    async loadTasks() {
        const container = document.getElementById('schedulerList');
        try {
            const result = await fetch('/api/scheduler/list').then(r => r.json());
            if (result.error) {
                container.innerHTML = '<div style="color:#e53e3e;text-align:center;padding:20px;">❌ ' + result.error + '</div>';
                return;
            }

            if (!result.tasks || result.tasks.length === 0) {
                container.innerHTML = '<div style="color:#4a4e62;text-align:center;padding:20px;">📭 暂无定时任务</div>';
                return;
            }

            let html = '<div style="display:flex;flex-direction:column;gap:8px;">';
            result.tasks.forEach(task => {
                const status = task.enabled ? '🟢 运行中' : '🔴 已暂停';
                const runStatus = task.run_status ? (task.run_status.status === 'running' ? '⏳ 运行中' :
                    '✅ ' + task.run_status.status) : '⏸️ 等待';
                const lastRun = task.last_run ? new Date(task.last_run).toLocaleString() : '从未';
                const cronDisplay = task.cron || '每 ' + (task.interval / 3600) + ' 小时';

                // ===== 显示操作目标 =====
                const params = task.params || {};
                const targetPath = params.target_path || '/data';
                const filePattern = params.file_pattern || '*';

                // ===== 显示最近日志（最多3条） =====
                const logs = task.logs || [];
                const recentLogs = logs.slice(-3);
                let logHtml = '';
                if (recentLogs.length > 0) {
                    logHtml = '<div style="font-size:10px;color:#4a4e62;margin-top:4px;border-top:1px solid #1f222c;padding-top:4px;">';
                    recentLogs.forEach(log => {
                        const logColor = log.status === 'success' ? '#68d391' : log.status === 'error' ? '#fc8181' : '#f6ad55';
                        logHtml += `<div style="color:${logColor};">${log.time} - ${log.message}</div>`;
                    });
                    logHtml += '</div>';
                }

                html += `
                <div style="background:#1a1d27;border-radius:8px;padding:10px 14px;border:1px solid #2d313e;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                    <div style="flex:1;min-width:150px;">
                        <div style="color:#e4e6eb;font-weight:600;font-size:14px;">${task.name}</div>
                        <div style="color:#8b8fa3;font-size:12px;">类型: ${task.type} | 调度: ${cronDisplay}</div>
                        <div style="color:#8b8fa3;font-size:11px;">📁 目标: ${targetPath}</div>
                        <div style="color:#8b8fa3;font-size:11px;">📄 匹配: ${filePattern}</div>
                        <div style="color:#8b8fa3;font-size:11px;">上次执行: ${lastRun} | 状态: ${runStatus}</div>
                        ${logHtml}
                    </div>
                    <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
                        <span style="font-size:12px;padding:2px 10px;border-radius:12px;background:${task.enabled ? '#2d3b6e' : '#2d313e'};color:${task.enabled ? '#68d391' : '#8b8fa3'};">${status}</span>
                        <button class="scheduler-toggle" data-id="${task.id}" style="background:#2d313e;border:0;color:#b5b9c9;padding:2px 10px;border-radius:4px;font-size:11px;cursor:pointer;font-family:inherit;">${task.enabled ? '⏸️ 暂停' : '▶️ 启动'}</button>
                        <button class="scheduler-run" data-id="${task.id}" style="background:#2d313e;border:0;color:#b5b9c9;padding:2px 10px;border-radius:4px;font-size:11px;cursor:pointer;font-family:inherit;">▶️ 立即执行</button>
                        <button class="scheduler-delete" data-id="${task.id}" style="background:#2d313e;border:0;color:#b5b9c9;padding:2px 10px;border-radius:4px;font-size:11px;cursor:pointer;font-family:inherit;">🗑️</button>
                    </div>
                </div>`;
            });
            html += '</div>';
            container.innerHTML = html;

            container.querySelectorAll('.scheduler-toggle').forEach(btn => {
                btn.addEventListener('click', () => this.toggleTask(btn.dataset.id));
            });
            container.querySelectorAll('.scheduler-run').forEach(btn => {
                btn.addEventListener('click', () => this.runTask(btn.dataset.id));
            });
            container.querySelectorAll('.scheduler-delete').forEach(btn => {
                btn.addEventListener('click', () => this.deleteTask(btn.dataset.id));
            });

        } catch (e) {
            container.innerHTML = '<div style="color:#e53e3e;text-align:center;padding:20px;">❌ 加载失败: ' + e.message + '</div>';
        }
    },

    addTask() {
        // ===== 获取当前目录用于默认值 =====
        const currentDir = window.currentPath || '/data';

        const modalHtml = `
        <div class="modal" style="max-width:550px;">
            <h2>⏰ 添加定时任务</h2>
            <div class="form-group">
                <label>任务名称</label>
                <input type="text" id="schedulerName" placeholder="例如: 每日去重" value="定时任务">
            </div>
            <div class="form-group">
                <label>任务类型</label>
                <select id="schedulerType">
                    <option value="rename">重命名</option>
                    <option value="dedup">去重</option>
                    <option value="classify">分类整理</option>
                </select>
            </div>
            <div class="form-group">
                <label>📁 操作目录</label>
                <input type="text" id="schedulerTargetPath" value="${currentDir}" placeholder="/data/你的目录">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">💡 任务将在此目录下执行</div>
            </div>
            <div class="form-group">
                <label>📄 文件匹配（正则表达式）</label>
                <input type="text" id="schedulerFilePattern" value=".*" placeholder=".* 匹配所有文件">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">💡 例如: \\.jpg$ 只匹配 JPG 文件</div>
            </div>
            <div class="form-group" id="schedulerRenameParams" style="display:block;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                    <div>
                        <label>查找</label>
                        <input type="text" id="schedulerFind" placeholder="要查找的字符">
                    </div>
                    <div>
                        <label>替换为</label>
                        <input type="text" id="schedulerReplace" placeholder="替换成的字符">
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label>调度方式</label>
                <select id="schedulerScheduleType">
                    <option value="cron">Cron 表达式</option>
                    <option value="interval">间隔时间</option>
                </select>
            </div>
            <div class="form-group" id="schedulerCronGroup">
                <label>Cron 表达式 (如: 0 2 * * * 每天凌晨2点)</label>
                <input type="text" id="schedulerCron" placeholder="0 2 * * *" value="0 2 * * *">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">
                    分 时 日 月 周 | 示例: 0 2 * * * = 每天凌晨2点
                </div>
            </div>
            <div class="form-group" id="schedulerIntervalGroup" style="display:none;">
                <label>间隔时间 (秒)</label>
                <input type="number" id="schedulerInterval" value="3600">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">3600秒 = 1小时</div>
            </div>
            <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <label style="margin:0;display:flex;align-items:center;gap:4px;cursor:pointer;">
                    <input type="checkbox" id="schedulerEnabled" checked style="width:16px;height:16px;accent-color:#667eea;">
                    <span style="color:#8b8fa3;font-size:12px;">启用</span>
                </label>
            </div>
            <div class="btn-row">
                <button class="btn-cancel" onclick="closeModal()">取消</button>
                <button class="btn-confirm" id="schedulerSaveBtn">保存</button>
            </div>
        </div>`;

        const overlay = openModal(modalHtml);
        overlay.querySelector('#schedulerScheduleType').addEventListener('change', function() {
            document.getElementById('schedulerCronGroup').style.display = this.value === 'cron' ? 'block' : 'none';
            document.getElementById('schedulerIntervalGroup').style.display = this.value === 'interval' ? 'block' : 'none';
        });
        overlay.querySelector('#schedulerType').addEventListener('change', function() {
            document.getElementById('schedulerRenameParams').style.display = this.value === 'rename' ? 'block' : 'none';
        });
        overlay.querySelector('#schedulerSaveBtn').addEventListener('click', () => this.saveTask());
    },

    async saveTask() {
        const name = document.getElementById('schedulerName').value.trim() || '定时任务';
        const type = document.getElementById('schedulerType').value;
        const scheduleType = document.getElementById('schedulerScheduleType').value;
        const cron = scheduleType === 'cron' ? document.getElementById('schedulerCron').value : '';
        const interval = scheduleType === 'interval' ? parseInt(document.getElementById('schedulerInterval').value) || 3600 : 0;
        const enabled = document.getElementById('schedulerEnabled').checked;
        const targetPath = document.getElementById('schedulerTargetPath').value.trim() || '/data';
        const filePattern = document.getElementById('schedulerFilePattern').value.trim() || '.*';

        // ===== 重命名参数 =====
        const find = document.getElementById('schedulerFind')?.value || '';
        const replace = document.getElementById('schedulerReplace')?.value || '';

        const params = {
            target_path: targetPath,
            file_pattern: filePattern,
            find: find,
            replace: replace
        };

        closeModal();
        showLog('⏳ 创建定时任务...', 'info');

        try {
            const result = await fetch('/api/scheduler/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    type: type,
                    cron: cron,
                    interval: interval,
                    enabled: enabled,
                    params: params
                })
            }).then(r => r.json());

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
            showLog('✅ 定时任务 "' + name + '" 已创建', 'success');
            this.loadTasks();
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    },

    async toggleTask(id) {
        try {
            const result = await fetch('/api/scheduler/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            }).then(r => r.json());

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
            this.loadTasks();
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    },

    async runTask(id) {
        try {
            showLog('⏳ 正在执行任务...', 'info');
            const result = await fetch('/api/scheduler/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            }).then(r => r.json());

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
            showLog('✅ 任务已触发执行', 'success');
            // 延迟刷新以查看日志更新
            setTimeout(() => this.loadTasks(), 2000);
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    },

    async deleteTask(id) {
        if (!confirm('确定要删除这个定时任务吗？')) return;

        try {
            const result = await fetch('/api/scheduler/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            }).then(r => r.json());

            if (result.error) { showLog('❌ ' + result.error, 'error'); return; }
            showLog('✅ 任务已删除', 'success');
            this.loadTasks();
        } catch (e) {
            showLog('❌ ' + e.message, 'error');
        }
    }
};

if (typeof ModuleRegistry !== 'undefined') {
    ModuleRegistry.register(SchedulerModule);
}
