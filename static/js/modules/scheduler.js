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

                const params = task.params || {};
                const targetPath = params.target_path || '/data';
                const filePattern = params.file_pattern || '*';
                const recursive = params.recursive ? '📂 包含子目录' : '📁 仅当前目录';

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
                        <div style="color:#8b8fa3;font-size:11px;">${recursive}</div>
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
        let dirOptions = '';
        const collectDirs = (nodes, prefix) => {
            if (!nodes || nodes.length === 0) return;
            for (let node of nodes) {
                if (node.is_dir) {
                    const path = prefix ? prefix + '/' + node.name : node.name;
                    const displayPath = '/' + path;
                    dirOptions += `<option value="${displayPath}">📁 ${displayPath}</option>`;
                    if (node.children && node.children.length > 0) {
                        collectDirs(node.children, path);
                    }
                }
            }
        };
        collectDirs(window.fullTreeData || [], '');

        const modalHtml = `
        <div class="modal" style="max-width:580px;">
            <h2>⏰ 添加定时任务</h2>
            <div class="form-group">
                <label>任务名称</label>
                <input type="text" id="schedulerName" placeholder="例如: 每日去重" value="定时任务" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
            </div>
            <div class="form-group">
                <label>任务类型</label>
                <select id="schedulerType" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                    <option value="rename">重命名</option>
                    <option value="dedup">去重</option>
                    <option value="classify">分类整理</option>
                    <option value="delete">删除</option>
                    <option value="move_copy">移动/复制</option>
                    <option value="chmod">权限修改</option>
                    <option value="compress">图片压缩</option>
                </select>
            </div>
            <div class="form-group">
                <label>📁 操作目录</label>
                <select id="schedulerTargetPath" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                    <option value="/data">📁 /data</option>
                    ${dirOptions}
                </select>
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">💡 任务将在选中的目录下执行</div>
            </div>

            <!-- ===== 文件匹配 ===== -->
            <div class="form-group">
                <label>📄 文件匹配（正则表达式）</label>
                <input type="text" id="schedulerFilePattern" value=".*" placeholder=".* 匹配所有文件" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">💡 例如: \\.jpg$ 只匹配 JPG 文件</div>
            </div>

            <!-- ===== 【新增】包括子目录选项 ===== -->
            <div class="form-group" style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <label style="margin:0;display:flex;align-items:center;gap:6px;cursor:pointer;">
                    <input type="checkbox" id="schedulerRecursive" style="accent-color:#667eea;width:16px;height:16px;">
                    <span style="color:#8b8fa3;font-size:13px;">📂 包括子目录</span>
                </label>
                <span style="color:#4a4e62;font-size:11px;">（勾选后将对所有子目录进行相同操作）</span>
            </div>

            <!-- ===== 重命名参数 ===== -->
            <div class="form-group" id="schedulerRenameParams" style="display:block;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">🔍 查找</label>
                        <input type="text" id="schedulerFind" placeholder="要查找的字符" style="width:100%;padding:6px 10px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;box-sizing:border-box;height:34px;">
                    </div>
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">📝 替换为</label>
                        <input type="text" id="schedulerReplace" placeholder="替换成的字符" style="width:100%;padding:6px 10px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;box-sizing:border-box;height:34px;">
                    </div>
                </div>
            </div>

            <!-- ===== 移动/复制参数 ===== -->
            <div class="form-group" id="schedulerMoveCopyParams" style="display:none;">
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">操作</label>
                        <select id="schedulerMoveAction" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                            <option value="move">移动</option>
                            <option value="copy">复制</option>
                        </select>
                    </div>
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">目标目录</label>
                        <input type="text" id="schedulerMoveTarget" placeholder="/data/目标目录" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                    </div>
                    <div style="display:flex;align-items:center;padding-top:20px;">
                        <label style="display:flex;align-items:center;gap:6px;color:#8b8fa3;font-size:12px;cursor:pointer;margin:0;">
                            <input type="checkbox" id="schedulerMoveOverwrite" style="accent-color:#667eea;width:14px;height:14px;">
                            覆盖已存在
                        </label>
                    </div>
                </div>
            </div>

            <!-- ===== 权限修改参数 ===== -->
            <div class="form-group" id="schedulerChmodParams" style="display:none;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">权限模式</label>
                        <select id="schedulerChmodMode" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                            <option value="755">755 (rwxr-xr-x)</option>
                            <option value="644">644 (rw-r--r--)</option>
                            <option value="777">777 (rwxrwxrwx)</option>
                            <option value="600">600 (rw-------)</option>
                            <option value="700">700 (rwx------)</option>
                            <option value="775">775 (rwxrwxr-x)</option>
                        </select>
                    </div>
                    <div style="display:flex;align-items:center;padding-top:20px;">
                        <label style="display:flex;align-items:center;gap:6px;color:#8b8fa3;font-size:12px;cursor:pointer;margin:0;">
                            <input type="checkbox" id="schedulerChmodRecursive" style="accent-color:#667eea;width:14px;height:14px;">
                            递归子目录
                        </label>
                    </div>
                </div>
            </div>

            <!-- ===== 图片压缩参数 ===== -->
            <div class="form-group" id="schedulerCompressParams" style="display:none;">
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">压缩质量</label>
                        <input type="number" id="schedulerCompressQuality" value="85" min="1" max="100" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                    </div>
                    <div>
                        <label style="display:block;color:#8b8fa3;font-size:12px;font-weight:600;margin-bottom:3px;">输出格式</label>
                        <select id="schedulerCompressFormat" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                            <option value="original">保持原格式</option>
                            <option value="webp">WebP</option>
                            <option value="jpg">JPEG</option>
                            <option value="png">PNG</option>
                        </select>
                    </div>
                    <div style="display:flex;align-items:center;padding-top:20px;">
                        <label style="display:flex;align-items:center;gap:6px;color:#8b8fa3;font-size:12px;cursor:pointer;margin:0;">
                            <input type="checkbox" id="schedulerCompressOverwrite" style="accent-color:#667eea;width:14px;height:14px;">
                            覆盖原图
                        </label>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label>调度方式</label>
                <select id="schedulerScheduleType" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                    <option value="cron">Cron 表达式</option>
                    <option value="interval">间隔时间</option>
                </select>
            </div>
            <div class="form-group" id="schedulerCronGroup">
                <label>Cron 表达式 (如: 0 2 * * * 每天凌晨2点)</label>
                <input type="text" id="schedulerCron" placeholder="0 2 * * *" value="0 2 * * *" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
                <div style="color:#4a4e62;font-size:11px;margin-top:2px;">
                    分 时 日 月 周 | 示例: 0 2 * * * = 每天凌晨2点
                </div>
            </div>
            <div class="form-group" id="schedulerIntervalGroup" style="display:none;">
                <label>间隔时间 (秒)</label>
                <input type="number" id="schedulerInterval" value="3600" style="width:100%;padding:5px 8px;background:#14171f;border:1px solid #2d313e;border-radius:6px;color:#e4e6eb;font-size:13px;outline:0;font-family:inherit;">
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
            const type = this.value;
            document.getElementById('schedulerRenameParams').style.display = type === 'rename' ? 'block' : 'none';
            document.getElementById('schedulerMoveCopyParams').style.display = type === 'move_copy' ? 'block' : 'none';
            document.getElementById('schedulerChmodParams').style.display = type === 'chmod' ? 'block' : 'none';
            document.getElementById('schedulerCompressParams').style.display = type === 'compress' ? 'block' : 'none';
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
        // ===== 【新增】读取子目录选项 =====
        const recursive = document.getElementById('schedulerRecursive').checked;

        const params = {
            target_path: targetPath,
            file_pattern: filePattern,
            recursive: recursive  // ===== 传递子目录参数 =====
        };

        if (type === 'rename') {
            params.find = document.getElementById('schedulerFind')?.value || '';
            params.replace = document.getElementById('schedulerReplace')?.value || '';
        } else if (type === 'move_copy') {
            params.move_action = document.getElementById('schedulerMoveAction')?.value || 'move';
            params.move_target = document.getElementById('schedulerMoveTarget')?.value.trim() || '';
            params.move_overwrite = document.getElementById('schedulerMoveOverwrite')?.checked || false;
        } else if (type === 'chmod') {
            params.chmod_mode = document.getElementById('schedulerChmodMode')?.value || '755';
            params.chmod_recursive = document.getElementById('schedulerChmodRecursive')?.checked || false;
        } else if (type === 'compress') {
            params.compress_quality = parseInt(document.getElementById('schedulerCompressQuality')?.value) || 85;
            params.compress_format = document.getElementById('schedulerCompressFormat')?.value || 'original';
            params.compress_overwrite = document.getElementById('schedulerCompressOverwrite')?.checked || false;
        }

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
