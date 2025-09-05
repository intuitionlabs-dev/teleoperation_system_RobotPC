import os
import sys

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

def find_first_specific_so_file(root_dir):
    import sys
    python_version = f"cpython-{sys.version_info.major}{sys.version_info.minor}"
    
    # First try to find the version-specific library
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.startswith('arx_x5_python') and filename.endswith('.so') and python_version in filename:
                return os.path.join(dirpath, filename)
    
    # Fallback to any compatible library
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.startswith('arx_x5_python') and filename.endswith('.so'):
                return os.path.join(dirpath, filename)
    
    return None

# 使用 os.path.join 来拼接路径
so_file = find_first_specific_so_file(os.path.join(current_dir, 'api', 'arx_x5_python'))

# 确保共享库的路径在 Python 的路径中
if os.path.exists(so_file):
    sys.path.append(os.path.dirname(so_file))  # 添加共享库所在目录到 sys.path
else:
    raise FileNotFoundError(f"Shared library not found: {so_file}")

# 导入编译模块
try:
    # 确保编译模块的路径在Python路径中
    sys.path.insert(0, os.path.dirname(so_file))
    
    # Import the compiled module with the correct name
    import importlib.util
    spec = importlib.util.spec_from_file_location("arx_x5_python", so_file)
    compiled_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compiled_module)
    
    # 将编译模块的内容暴露出来
    InterfacesPy = compiled_module.InterfacesPy
except Exception as e:
    print(f"Warning: Failed to import compiled module: {e}")
    print(f"Library path: {so_file}")
    InterfacesPy = None

# 导入 Python 模块
try:
    from .script.dual_arm import BimanualArm  # 确保这两个类在各自的文件中被正确定义
    from .script.single_arm import SingleArm
except ImportError as e:
    raise ImportError(f"Failed to import Python modules: {e}")

# 可选：定义 __all__ 以控制模块导出的内容
__all__ = ['BimanualArm', 'SingleArm', 'InterfacesPy']
