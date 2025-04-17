
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Include ctypes and its dependencies
hiddenimports = collect_submodules('ctypes')

# Collect libffi DLL
datas = collect_data_files('ctypes')
