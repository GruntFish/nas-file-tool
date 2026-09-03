// static/js/virtual_scroll.js
/**
 * 虚拟滚动 - 优化大量文件渲染
 */
class VirtualScroll {
    constructor(options) {
        this.container = options.container;
        this.itemHeight = options.itemHeight || 30;
        this.renderItem = options.renderItem;
        this.data = options.data || [];
        this.bufferSize = options.bufferSize || 5;
        
        this._scrollTop = 0;
        this._containerHeight = 0;
        this._totalHeight = 0;
        this._visibleStart = 0;
        this._visibleEnd = 0;
        this._cache = {};
        
        this._setupContainer();
        this._bindEvents();
        this.render();
    }
    
    _setupContainer() {
        this.container.style.position = 'relative';
        this.container.style.overflow = 'auto';
        this.container.style.height = '100%';
        
        this._placeholder = document.createElement('div');
        this._placeholder.style.position = 'absolute';
        this._placeholder.style.top = '0';
        this._placeholder.style.left = '0';
        this._placeholder.style.right = '0';
        this._placeholder.style.pointerEvents = 'none';
        this.container.appendChild(this._placeholder);
        
        this._content = document.createElement('div');
        this._content.style.position = 'relative';
        this.container.appendChild(this._content);
    }
    
    _bindEvents() {
        this._onScroll = this._onScroll.bind(this);
        this.container.addEventListener('scroll', this._onScroll);
        
        this._onResize = this._onResize.bind(this);
        window.addEventListener('resize', this._onResize);
    }
    
    _onScroll() {
        this._scrollTop = this.container.scrollTop;
        this.render();
    }
    
    _onResize() {
        this._containerHeight = this.container.clientHeight;
        this.render();
    }
    
    updateData(data) {
        this.data = data;
        this._cache = {};
        this._totalHeight = data.length * this.itemHeight;
        this._placeholder.style.height = this._totalHeight + 'px';
        this.render();
    }
    
    _getVisibleRange() {
        const start = Math.max(0, Math.floor(this._scrollTop / this.itemHeight) - this.bufferSize);
        const end = Math.min(this.data.length, 
            Math.ceil((this._scrollTop + this._containerHeight) / this.itemHeight) + this.bufferSize);
        return { start, end };
    }
    
    render() {
        if (!this.data || this.data.length === 0) {
            this._content.innerHTML = '';
            return;
        }
        
        this._containerHeight = this.container.clientHeight || this.container.parentElement?.clientHeight || 300;
        this._totalHeight = this.data.length * this.itemHeight;
        this._placeholder.style.height = this._totalHeight + 'px';
        
        const { start, end } = this._getVisibleRange();
        
        if (start === this._visibleStart && end === this._visibleEnd) {
            return;
        }
        
        this._visibleStart = start;
        this._visibleEnd = end;
        
        const fragment = document.createDocumentFragment();
        const offset = start * this.itemHeight;
        
        for (let i = start; i < end; i++) {
            const item = this.data[i];
            const el = this.renderItem(item, i);
            el.style.position = 'absolute';
            el.style.top = (i * this.itemHeight - offset) + 'px';
            el.style.left = '0';
            el.style.right = '0';
            el.style.height = this.itemHeight + 'px';
            fragment.appendChild(el);
        }
        
        this._content.innerHTML = '';
        this._content.appendChild(fragment);
        this._content.style.height = (end - start) * this.itemHeight + 'px';
        this._content.style.transform = `translateY(${offset}px)`;
    }
    
    destroy() {
        this.container.removeEventListener('scroll', this._onScroll);
        window.removeEventListener('resize', this._onResize);
        this.container.innerHTML = '';
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = VirtualScroll;
}
