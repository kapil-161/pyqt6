import os
import sys
import subprocess
import shutil
import time

def build_debug_exe():
    """Build a debug version with minimal exclusions to identify required modules"""
    print("\n=== Building Debug DSSAT Viewer ===\n")
    
    start_time = time.time()
    
    # First, create jaraco.text fix
    with open("hook-pkg_resources.py", "w") as f:
        f.write("""
from PyInstaller.utils.hooks import collect_submodules

# Add missing dependencies
hiddenimports = ['jaraco.text', 'plistlib']
""")
    print("Created hook-pkg_resources.py with necessary imports")
    
    # Find UPX
    upx_path = None
    possible_upx_locations = [
        r"C:\Users\kbhattarai1\Downloads\upx-5.0.0-win64\upx-5.0.0-win64",
        os.path.join(os.getcwd(), "upx-5.0.0-win64"),
        os.path.join(os.getcwd(), "upx")
    ]
    
    for location in possible_upx_locations:
        upx_exe = os.path.join(location, "upx.exe")
        if os.path.exists(upx_exe):
            upx_path = location
            print(f"UPX found at: {upx_path}")
            break
    
    # Create a more conservative spec file for debugging
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

# Define minimal Qt plugins
qt_plugins = [
    ('platforms', ['platforms/qwindows.dll'])
]

# Create minimal hooks
def minimal_hooks():
    return ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 
            'pyqtgraph', 'pandas.core.frame', 'pandas.core.series', 
            'numpy.core', 'jaraco.text', 'plistlib']

# Minimal exclusion list - only large/unnecessary packages
excluded_modules = [
    'matplotlib', 'scipy', 'tkinter', '_tkinter', 'Tkinter', 'wx',
    'IPython', 'notebook', 'sphinx', 'docutils',
    'PIL', 'sqlalchemy', 'tornado', 'jinja2', 'flask',
    'PyQt5.QtWebEngine', 'PyQt5.QtMultimedia', 'PyQt5.QtNetwork',
    'PyQt5.QtQml', 'PyQt5.QtQuick', 
    'plotly', 'dash'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=minimal_hooks(),
    hookspath=['.'],
    hooksconfig={'pyqt5': {'plugins': qt_plugins}},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter unnecessary Qt plugins
def filter_binaries(binaries):
    excluded_patterns = [
        'Qt5WebEngine', 'Qt5Designer', 'Qt5Quick', 'Qt5Qml', 'Qt5Help',
        'Qt5Multimedia'
    ]
    
    return [(name, path, typ) for name, path, typ in binaries 
            if not any(pattern in name for pattern in excluded_patterns)]

a.binaries = filter_binaries(a.binaries)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dssat_viewer',
    debug=False,          # Enable debug mode
    bootloader_ignore_signals=False,
    strip=False,         # Don't strip for debugging
    upx=False,           # No UPX for debugging
    runtime_tmpdir=None,
    console=False,        # Show console for error messages
    disable_windowed_traceback=False,  # Enable traceback
)
"""
    
    spec_path = os.path.join(os.getcwd(), "dssat_viewer.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)
    
    print("Created debug spec file with minimal exclusions")
    
    # Build command
    build_cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "--clean",
        spec_path
    ]
    
    print(f"Running: {' '.join(build_cmd)}")
    
    try:
        subprocess.check_call(build_cmd)
        build_time = time.time() - start_time
        print(f"\nBuild completed in {build_time:.1f} seconds!")
        
        # Check if executable was created
        exe_path = os.path.join(os.getcwd(), "dist", "dssat_viewer_debug.exe")
        if os.path.exists(exe_path):
            size_bytes = os.path.getsize(exe_path)
            size_mb = size_bytes / (1024 * 1024)
            
            print(f"\n=== Debug Build Results ===")
            print(f"Debug executable created at: {exe_path}")
            print(f"Executable size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
            print("\nRun this debug version to check for any additional missing modules")
            print("Once it runs successfully, you can gradually add more exclusions")
            
            # Create a launcher for the debug version
            with open("run_debug.bat", "w") as f:
                f.write('@echo off\necho Running debug version...\ncd dist\ndssat_viewer_debug.exe\npause\n')
            print("Created launcher: run_debug.bat")
            
            return True
        else:
            print(f"Error: Debug executable not found at {exe_path}")
            return False
            
    except subprocess.SubprocessError as e:
        print(f"Error during build: {e}")
        return False

if __name__ == "__main__":
    build_debug_exe()