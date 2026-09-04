// static/js/progress.js
class ProgressBar {
    constructor(options) {
        this.container = options.container || document.body;
        this.title = options.title || '处理中...';
        this.onComplete = options.onComplete || null;
        this.onCancel = options.onCancel || null;
        this.onProgress = options.onProgress || null;

        this._total = 0;
        this._current = 0;
        this._isComplete = false;
        this._isCancelled = false;
        this._isHidden = false;

        this._createUI();
        this._bindEvents();
    }

    _createUI() {
        this._overlay = document.createElement('div');
        this._overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 999999;
            display: none;
            justify-content: center;
            align-items: center;
        `;

        this._container = document.createElement('div');
        this._container.style.cssText = `
            background: #1a1d27;
            border-radius: 16px;
            padding: 36px 48px;
            max-width: 450px;
            width: 90%;
            border: 1px solid #2d313e;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.9);
            text-align: center;
        `;

        this._titleEl = document.createElement('div');
        this._titleEl.style.cssText = `
            color: #e4e6eb;
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 20px;
        `;
        this._titleEl.textContent = this.title;
        this._container.appendChild(this._titleEl);

        this._track = document.createElement('div');
        this._track.style.cssText = `
            width: 100%;
            height: 10px;
            background: #2d313e;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 14px;
        `;

        this._fill = document.createElement('div');
        this._fill.style.cssText = `
            height: 100%;
            width: 0%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 6px;
            transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        this._track.appendChild(this._fill);
        this._container.appendChild(this._track);

        this._infoEl = document.createElement('div');
        this._infoEl.style.cssText = `
            color: #8b8fa3;
            font-size: 14px;
            margin-bottom: 18px;
            min-height: 22px;
        `;
        this._infoEl.textContent = '准备中...';
        this._container.appendChild(this._infoEl);

        this._btnRow = document.createElement('div');
        this._btnRow.style.cssText = `
            display: flex;
            gap: 10px;
            justify-content: center;
        `;

        this._cancelBtn = document.createElement('button');
        this._cancelBtn.style.cssText = `
            background: #2d313e;
            border: 0;
            color: #b5b9c9;
            padding: 8px 28px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.15s ease;
        `;
        this._cancelBtn.textContent = '取消';
        this._cancelBtn.addEventListener('click', () => this._handleCancel());
        this._btnRow.appendChild(this._cancelBtn);

        this._container.appendChild(this._btnRow);

        this._overlay.appendChild(this._container);
        this.container.appendChild(this._overlay);
    }

    _bindEvents() {
        this._onKeydown = (e) => {
            if (e.key === 'Escape' && this._isVisible() && !this._isComplete) {
                this._handleCancel();
            }
        };
        document.addEventListener('keydown', this._onKeydown);
    }

    _handleCancel() {
        if (this._isComplete) {
            this.hide();
            if (this.onComplete) this.onComplete();
            return;
        }
        if (this._isCancelled) return;
        this._isCancelled = true;
        if (this.onCancel) {
            this.onCancel();
        }
        this._titleEl.textContent = '⏹️ 正在取消...';
        this._cancelBtn.disabled = true;
        this._cancelBtn.style.opacity = '0.5';
    }

    _isVisible() {
        return this._overlay.style.display === 'flex';
    }

    setTotal(total) {
        this._total = total;
        this._updateInfo();
    }

    update(current, extra = '') {
        if (this._isCancelled || this._isComplete) return;
        this._current = Math.min(current, this._total);
        const percent = this._total > 0 ? (this._current / this._total) * 100 : 0;
        this._fill.style.width = Math.min(percent, 100) + '%';
        this._updateInfo(extra);
        if (this.onProgress) {
            this.onProgress(this._current, this._total);
        }
    }

    _updateInfo(extra = '') {
        if (this._isComplete) {
            this._infoEl.textContent = '✅ 已完成';
            return;
        }
        const display = this._total > 0 ? `${this._current} / ${this._total}` : '准备中...';
        this._infoEl.textContent = extra ? `${display} - ${extra}` : display;
    }

    show() {
        this._overlay.style.display = 'flex';
        this._isHidden = false;
        this._current = 0;
        this._isComplete = false;
        this._isCancelled = false;
        this._cancelBtn.disabled = false;
        this._cancelBtn.style.opacity = '1';
        this._cancelBtn.textContent = '取消';
        this._fill.style.width = '0%';
        this._titleEl.textContent = this.title;
        this._updateInfo('准备中...');
    }

    hide() {
        this._overlay.style.display = 'none';
        this._isHidden = true;
        document.removeEventListener('keydown', this._onKeydown);
        if (this._overlay && this._overlay.parentNode) {
            this._overlay.parentNode.removeChild(this._overlay);
        }
    }

    complete(message = '✅ 处理完成') {
        this._isComplete = true;
        this._fill.style.width = '100%';
        this._fill.style.background = 'linear-gradient(135deg, #68d391, #38a169)';
        this._titleEl.textContent = message;
        this._infoEl.textContent = '✅ 已完成';
        this._cancelBtn.textContent = '关闭';
        this._cancelBtn.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
        this._cancelBtn.style.color = '#fff';
        this._cancelBtn.disabled = false;
        this._cancelBtn.style.opacity = '1';
        this._cancelBtn.onclick = () => {
            this.hide();
            if (this.onComplete) this.onComplete();
        };
    }

    error(message = '❌ 操作失败') {
        this._isComplete = true;
        this._fill.style.width = '100%';
        this._fill.style.background = 'linear-gradient(135deg, #fc8181, #e53e3e)';
        this._titleEl.textContent = message;
        this._infoEl.textContent = '⚠️ 操作失败，请查看日志';
        this._cancelBtn.textContent = '关闭';
        this._cancelBtn.style.background = '#e53e3e';
        this._cancelBtn.style.color = '#fff';
        this._cancelBtn.disabled = false;
        this._cancelBtn.style.opacity = '1';
        this._cancelBtn.onclick = () => {
            this.hide();
            if (this.onComplete) this.onComplete();
        };
    }

    isCancelled() {
        return this._isCancelled;
    }

    destroy() {
        document.removeEventListener('keydown', this._onKeydown);
        if (this._overlay && this._overlay.parentNode) {
            this._overlay.parentNode.removeChild(this._overlay);
        }
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressBar;
}
