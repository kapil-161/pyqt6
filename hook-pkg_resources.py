
from PyInstaller.utils.hooks import collect_submodules

# Add missing dependencies
hiddenimports = ['jaraco.text', 'plistlib']
