// static/js/modules/classify.js

const ClassifyModule = {
    name: 'classify',

    init() {
        document.getElementById('classifyOpenBtn').addEventListener('click', () => this.openModal());
        this.updateCount();
    },

    onSelectChange(selected) {
        this.updateCount();
    },

    updateCount() {
        const count = selectedFiles.size;
        const el = document.getElementById('classifySelectedCount');
        if (el) el.textContent = count;
    },

    openModal() {
        const files = Array.from(selectedFiles);
        if (files.length === 0) {
            showLog('⚠️ 请先选择要分类的文件', 'warning');
            return;
        }

        const modalHtml = `
        <div class="modal-overlay show">
            <div class="modal" style="max-width:500px;">
                <h2>📂 分类整理</h2>
                <div style="color:#8b8fa3;font-size:13px;margin-bottom:10px;">
                    已选 <strong style="color:#e4e6eb;">${files.length}</strong> 个文件
                </div>
                <div class="form-group">
                    <label>分类方式</label>
                    <select id="classifyMethod">
                        <option value="type">按文件类型（图片/视频/文档等）</option>
                        <option value="date">按创建日期（年-月）</option>
                        <option value="size">按文件大小</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>目标根目录</label>
                    <input type="text" id="classifyTarget" value="分类整理" placeholder="分类整理">
                    <div style="color:#4a4e62;font-size:11px;margin-top:2px;">
                        💡 将在当前目录下创建该文件夹，所有分类子目录都在里面
                    </div>
                </div>
                <div style="color:#8b8fa3;font-size:12px;margin-bottom:8px;">
                    <input type="checkbox" id="classifyCopyModeModal"> 复制模式（不移动原文件）
                </div>
                <div id="classifyPreviewArea" style="display:none;margin-top:8px;">
                    <div class="preview-list" id="classifyPreviewList" style="max-height:200px;"></div>
                    <div style="color:#68d391;font-size:12px;margin-top:4px;" id="classifyStats"></div>
                </div>
                <div class="btn-row">
                    <button class="btn-cancel" onclick="closeModal()">取消</button>
                    <button class="btn-confirm" id="classifyPreviewBtn">👁️ 预览</button>
                    <button class="btn-confirm" id="classifyConfirmBtn" style="display:none;">确认执行</button>
                </div>
            </div>
        </div>
        `;

        openModal(modalHtml);

        document.getElementById('classifyPreviewBtn').addEventListener('click', () => this.preview());
        document.getElementById('classifyConfirmBtn').addEventListener('click', () => this.execute());
    },

    async preview() {
        const files = Array.from(selectedFiles);
        const method = document.getElementById('classifyMethod').value;
        const targetBase = document.getElementById('classifyTarget').value.trim() || '分类整理';
        const copyMode = document.getElementById('classifyCopyModeModal').checked;

        if (files.length === 0) { showLog('⚠️ 请选择文件', 'warning'); return; }

        showLog('⏳ 预览分类结果...', 'info');

        try {
            const result = await apiCall('/api/classify', {
                files: files,
                method: method,
                target_base: targetBase,
                copy_mode: copyMode,
                dry_run: true
            });

            if (result
