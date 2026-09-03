// static/js/progress.js
/**
 * 进度条组件
 */
class ProgressBar {
    constructor(options) {
        this.container = options.container || document.body;
        this.title = options.title || '处理中...';
        this.onComplete = options.onComplete || null;
        this.onCancel = options.onCancel || null;
        
        this._total = 0;
        this._current = 0;
        this._isComplete = false;
        this._isCancelled = false;
        
        this._createUI();
    }
    
    _createUI() {
        this._overlay = document.createElement('div');
        this._overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            z-index: 999999;
            display: none;
            justify-content: center;
            align-items: center;
        `;
        
        this._container = document.createElement('div');
        this._container.style.cssText = `
            background: #1a1d27;
            border-radius: 12px;
            padding: 30px 40px;
            max-width: 400px;
            width: 90%;
            border: 1px solid #2d313e;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
            text-align: center;
        `;
        
        this._titleEl = document.createElement('div');
        this._titleEl.style.cssText = `
            color: #e4e6eb;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
        `;
        this._titleEl.textContent = this.title;
        this._container.appendChild(this._titleEl);
        
        this._track = document.createElement('div');
        this._track.style.cssText = `
            width: 100%;
            height: 8px;
            background: #2d313e;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 12px;
        `;
        
        this._fill = document.createElement('div');
        this._fill.style.cssText = `
            height: 100%;
            width: 0%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 4px;
            transition: width 0.3s ease;
        `;
        this._track.appendChild(this._fill);
        this._container.appendChild(this._track);
        
        this._textEl = document.createElement('div');
        this._textEl.style.cssText = `
            color: #8b8fa3;
            font-size: 13px;
            margin-bottom: 16px;
        `;
        this._textEl.textContent = '0 / 0';
        this._container.appendChild(this._textEl);
        
        this._cancelBtn = document.createElement('button');
        this._cancelBtn.style.cssText = `
            background: #2d313e;
            border: 0;
            color: #b5b9c9;
            padding: 6px 20px;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.15s ease;
        `;
        this._cancelBtn.textContent = '取消';
        this._cancelBtn.addEventListener('click', () => {
            if (this.onCancel) {
                this._isCancelled = true;
                this.onCancel();
            }
            this.hide();
        });
        this._container.appendChild(this._cancelBtn);
        
        this._overlay.appendChild(this._container);
        this.container.appendChild(this._overlay);
    }
    
    setTotal(total) {
        this._total = total;
        this._updateText();
    }
    
    update(current, extra = '') {
        this._current = current;
        const percent = this._total > 0 ? (current / this._total) * 100 : 0;
        this._fill.style.width = Math.min(percent, 100) + '%';
        this._updateText(extra);
    }
    
    _updateText(extra = '') {
        const display = this._isComplete ? '完成' : `${this._current} / ${this._total}`;
        this._textEl.textContent = extra ? `${display} - ${extra}` : display;
    }
    
    show() {
        this._overlay.style.display = 'flex';
    }
    
    hide() {
        this._overlay.style.display = 'none';
    }
    
    complete(message = '处理完成') {
        this._isComplete = true;
        this._fill.style.width = '100%';
        this._fill.style.background = 'linear-gradient(135deg, #68d391, #38a169)';
        this._titleEl.textContent = '✅ ' + message;
        this._textEl.textContent = '已完成';
        this._cancelBtn.textContent = '关闭';
        this._cancelBtn.style.background = 'linear-gradient(135deg, #667eea, #764ba2)';
        this._cancelBtn.style.color = '#fff';
        this._cancelBtn.onclick = () => {
            this.hide();
            if (this.onComplete) this.onComplete();
        };
    }
    
    error(message = '处理失败') {
        this._isComplete = true;
        this._fill.style.width = '100%';
        this._fill.style.background = 'linear-gradient(135deg, #fc8181, #e53e3e)';
        this._titleEl.textContent = '❌ ' + message;
        this._textEl.textContent = '操作失败，请查看日志';
        this._cancelBtn.textContent = '关闭';
        this._cancelBtn.style.background = '#e53e3e';
        this._cancelBtn.style.color = '#fff';
        this._cancelBtn.onclick = () => {
            this.hide();
            if (this.onComplete) this.onComplete();
        };
    }
    
    isCancelled() {
        return this._isCancelled;
    }
    
    destroy() {
        if (this._overlay && this._overlay.parentNode) {
            this._overlay.parentNode.removeChild(this._overlay);
        }
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProgressBar;
}
