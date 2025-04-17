
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Define required Qt plugins
qt_plugins = [
    ('platforms', ['platforms/qwindows.dll'])
]

# All hidden imports for our app
hidden_imports = [
    # PyQt6 and UI dependencies
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui',
    'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets',
    'pyqtgraph', 'pyqtgraph.graphicsItems',
    
    # Data processing dependencies
    'pandas', 'pandas.core.frame', 'pandas.core.series', 
    'numpy', 'numpy.core',
    'python_dateutil', 'dateutil',
    
    # ctypes dependencies
    'ctypes', 'ctypes.util',
    
    # pkg_resources dependencies
    'jaraco.text', 'plistlib', 'appdirs', 
    'packaging', 'packaging.version', 'packaging.specifiers', 
    'packaging.requirements', 'packaging.markers',
    'importlib_metadata', 'zipp', 'attrs', 'more_itertools',
    
    # OpenGL dependencies
    'OpenGL', 'OpenGL.GL', 'OpenGL.GLU', 'OpenGL.GLUT', 'OpenGL.platform',
    
    # Other dependencies
    'threadpoolctl'
]

# Minimal exclusion list - only large/unnecessary packages
exclusions = [
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.sip',
    'matplotlib', 'scipy', 'tkinter', '_tkinter', 'Tkinter', 'wx',
    'IPython', 'notebook', 'sphinx', 'docutils',
    'PIL', 'sqlalchemy', 'tornado', 'jinja2', 'flask',
    'PyQt6.QtWebEngine', 'PyQt6.QtMultimedia', 'PyQt6.QtNetwork',
    'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtSvg', 'PyQt6.QtTest',
    'PyQt6.QtPdf',
    'plotly', 'plotly.graph_objects', 'plotly.express', 'plotly.io',
    'dash',
    'pygame', 'psutil', 'openpyxl', 'charset_normalizer',
    'jupyter', 'sqlite3',
    'concurrent.futures', 'importlib.util',

]

a = Analysis(
    ['main.py'],
    pathex=['C:\\Users\\kbhattarai1\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\pyqtgraph'] if 'C:\\Users\\kbhattarai1\\AppData\\Local\\Programs\\Python\\Python313\\Lib\\site-packages\\pyqtgraph' else [],
    binaries=[('C:\\Users\\kbhattarai1\\AppData\\Local\\Programs\\Python\\Python313\\DLLs\\libffi-8.dll', '.')],
    datas=[('resources', 'resources')],
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={'pyqt6': {'plugins': qt_plugins}},
    runtime_hooks=[
        f'hooks/pkg_resources_hook.py',
        f'hooks/opengl_hook.py'
    ],
    excludes=exclusions,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter unnecessary Qt plugins and large DLLs
def filter_binaries(binaries):
    excluded_patterns = [
        'Qt6WebEngine', 'Qt6Designer', 'Qt6Quick', 'Qt6Qml', 'Qt6Help',
        'Qt6Multimedia', 'Qt6Svg', 'Qt6Test', 'Qt6Pdf', 'Qt5',
        'opengl32sw.dll', 'd3dcompiler_47.dll',
        'libcrypto', 'libssl', 'sqlite3.dll', 'pythoncom', 'pywintypes',
        'MSVCP140', 'VCRUNTIME140', 'MSVCR100'
    ]
    
    return [(name, path, typ) for name, path, typ in binaries 
            if not any(pattern in name for pattern in excluded_patterns)]

a.binaries = filter_binaries(a.binaries)

# Add a script to create an empty __init__.py file to prevent scanning issues
init_script = '''
import os
import sys

# Create an empty __init__.py in the root directory
base_dir = os.path.dirname(sys.executable)
init_path = os.path.join(base_dir, "__init__.py")

with open(init_path, "w") as f:
    f.write("# Empty __init__.py to prevent scanning issues")
'''

a.scripts.append(('pkg_resources_workaround', init_script, 'PYSOURCE'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dssat_viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Disable strip to avoid FileNotFoundError
    upx=True,
    upx_exclude=['Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'python313.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
