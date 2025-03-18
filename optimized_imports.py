
# Add to the beginning of main.py for optimized lazy loading
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
