# modules/__init__.py
import importlib
import pkgutil
from pathlib import Path

def register_all_routes(app):
    """自动发现并注册所有模块"""
    current_dir = Path(__file__).parent
    
    for module_info in pkgutil.iter_modules([str(current_dir)]):
        module_name = module_info.name
        
        # 跳过 __init__
        if module_name == '__init__':
            continue
        
        try:
            module = importlib.import_module(f'modules.{module_name}')
            
            # 如果模块有 register 函数，调用它
            if hasattr(module, 'register'):
                module.register(app)
                print(f'[模块] 已加载: {module_name}')
                
        except Exception as e:
            print(f'[模块] 加载失败 {module_name}: {e}')
