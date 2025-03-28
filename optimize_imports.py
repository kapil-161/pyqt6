# Add this to the top of main.py for optimized lazy loading
import sys
import os
import importlib.util

class LazyImporter:
    def __init__(self):
        self._modules = {}
    
    def __call__(self, name):
        if name not in self._modules:
            self._modules[name] = LazyModule(name)
        return self._modules[name]

class LazyModule:
    def __init__(self, name):
        self.name = name
        self._module = None
    
    def __getattr__(self, attr):
        if self._module is None:
            self._module = importlib.import_module(self.name)
        return getattr(self._module, attr)

# Create lazy importer
lazy_import = LazyImporter()

# Use like: pd = lazy_import('pandas')
# numpy = lazy_import('numpy')
# pg = lazy_import('pyqtgraph')

# Optimize Qt settings for faster loading
from PyQt6.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
QCoreApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Set environment variables
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
