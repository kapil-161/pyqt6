# -*- coding: utf-8 -*-
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.config import CONF
import os
import sys
import subprocess
import time
import logging
import shutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure necessary PyInstaller configurations are set
base_path = os.getcwd()
CONF['spec'] = os.path.join(base_path, 'dssat_viewer.spec')
CONF['workpath'] = os.path.join(base_path, 'build')
CONF['warnfile'] = os.path.join(base_path, 'build', 'warn.txt')  # Add this line to fix the KeyError
CONF['xref-file'] = os.path.join(base_path, 'build', 'xref.txt')  # Add this line to fix the KeyError
CONF['distpath'] = os.path.join(base_path, 'dist')
CONF['code_cache'] = {}  # Initialize an empty code cache dictionary
os.makedirs(CONF['workpath'], exist_ok=True)
os.makedirs(CONF['distpath'], exist_ok=True)
def create_jaraco_hook():
    """Create jaraco.text fix hook for PyInstaller"""
    hook_content = """
from PyInstaller.utils.hooks import collect_submodules

# Add missing dependencies
hiddenimports = ['jaraco.text', 'plistlib']
"""
    try:
        hook_path = os.path.join(os.getcwd(), "hook-pkg_resources.py")
        with open(hook_path, "w") as f:
            f.write(hook_content)
        logger.info("Created hook-pkg_resources.py with necessary imports")
        return True
    except Exception as e:
        logger.error(f"Error creating hook-pkg_resources.py: {e}")
        return False

def create_opengl_exclusion_hook():
    """Create exclusion hook for OpenGL"""
    hook_content = """
# Empty OpenGL hook to prevent PyInstaller from including OpenGL DLLs
"""
    try:
        hook_path = os.path.join(os.getcwd(), "hook-OpenGL.py")
        with open(hook_path, "w") as f:
            f.write(hook_content)
        logger.info("Created hook-OpenGL.py to exclude OpenGL DLLs")
        return True
    except Exception as e:
        logger.error(f"Error creating hook-OpenGL.py: {e}")
        return False

def find_upx():
    """Find UPX executable for compression"""
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
            logger.info(f"UPX found at: {upx_path}")
            break
            
    return upx_path

def clean_pyinstaller_cache():
    """Clean PyInstaller cache to avoid OpenGL DLL issues"""
    try:
        cache_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'pyinstaller')
        if os.path.exists(cache_dir):
            logger.info(f"Cleaning PyInstaller cache at: {cache_dir}")
            shutil.rmtree(cache_dir)
            
        # Also clean __pycache__ directories
        for root, dirs, files in os.walk(os.getcwd()):
            for dir in dirs:
                if dir == "__pycache__":
                    pycache_path = os.path.join(root, dir)
                    logger.info(f"Removing: {pycache_path}")
                    shutil.rmtree(pycache_path)
                    
        return True
    except Exception as e:
        logger.error(f"Error cleaning PyInstaller cache: {e}")
        return False

block_cipher = None

# Define minimal Qt plugins
qt_plugins = [
    ('platforms', ['platforms/qwindows.dll'])
]

# Create minimal hooks
def minimal_hooks():
    return ['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 
            'pyqtgraph', 'pandas.core.frame', 'pandas.core.series', 
            'numpy.core', 'jaraco.text', 'plistlib']

# Minimal exclusion list - only large/unnecessary packages
excluded_modules = [
    'matplotlib', 'scipy', 'tkinter', '_tkinter', 'Tkinter', 'wx',
    'IPython', 'notebook', 'sphinx', 'docutils',
    'PIL', 'sqlalchemy', 'tornado', 'jinja2', 'flask',
    'PyQt6.QtWebEngine', 'PyQt6.QtMultimedia', 'PyQt6.QtNetwork',
    'PyQt6.QtQml', 'PyQt6.QtQuick', 
    'plotly', 'dash'
]
upx_path = find_upx()
CONF['upx_available'] = upx_path is not None
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=minimal_hooks(),
    hookspath=['.'],
    hooksconfig={'pyqt6': {'plugins': qt_plugins}},
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
        'Qt6WebEngine', 'Qt6Designer', 'Qt6Quick', 'Qt6Qml', 'Qt6Help',
        'Qt6Multimedia'
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

def create_spec_file():
    """Create a spec file for PyInstaller"""
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports={minimal_hooks()},
    hookspath=['.'],
    hooksconfig={{'pyqt6': {{'plugins': {qt_plugins}}}}},
    runtime_hooks=[],
    excludes={excluded_modules},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
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
        "--onefile",                 # Create a single executable
        "--windowed",                # Windows application (no console)
        "--add-data", "resources;resources", # Include resources
        "--paths", ".",             # Add current directory to search path
        "--additional-hooks-dir", ".",  # Use local hooks directory - FIXED
        
        # Essential imports
        "--hidden-import", "jaraco.text",
        "--hidden-import", "plistlib",
        "--hidden-import", "pandas.core.frame",
        "--hidden-import", "pandas.core.series",
        "--hidden-import", "numpy.core",
        "--hidden-import", "PyQt6",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtGui",
        
        # Explicit exclusions to avoid problems
        "--exclude-module", "PyQt5",
        "--exclude-module", "OpenGL",
        "--exclude-module", "OpenGL_accelerate",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "tkinter",
        "--exclude-module", "PyQt6.QtWebEngine",
        "--exclude-module", "PyQt6.QtMultimedia",
        "--exclude-module", "PyQt6.QtNetwork",
        "--exclude-module", "PyQt6.QtQml",
        "--exclude-module", "PyQt6.QtQuick",
        "--exclude-module", "plotly",
        "--exclude-module", "dash",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        "--exclude-module", "sphinx",
        "--exclude-module", "docutils",
        "--exclude-module", "PIL",
        "--exclude-module", "sqlalchemy",
        "--exclude-module", "tornado",
        "--exclude-module", "jinja2",
        "--exclude-module", "flask",
        "--exclude-module", "yaml",
        "--exclude-module", "numpy.distutils",
        "--exclude-module", "numpy.f2py",
        "--exclude-module", "numpy.testing",
        "--exclude-module", "pandas.io.formats.excel",
       
        
        "--exclude-module", "pandas.io.clipboard",

        # Name output as dssat_viewer
        "--name", "dssat_viewer",
        
        # Main script
        "main.py"
    ]
    
    # Find UPX for compression - add at the end
    upx_path = find_upx()
    if upx_path:
        build_cmd.extend(["--upx-dir", upx_path])
        #build_cmd.extend(["--upx-args", "--best"])
    
    logger.info(f"Running: {' '.join(build_cmd)}")
    
    try:
        subprocess.check_call(build_cmd)
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Error during build: {e}")
        return False

def create_resources_folder():
    """Ensure resources/icons directory exists with a placeholder icon"""
    icon_dir = os.path.join(os.getcwd(), "resources", "icons")
    os.makedirs(icon_dir, exist_ok=True)
    
    icon_path = os.path.join(icon_dir, "dssat_icon.ico")
    if not os.path.exists(icon_path):
        logger.info("Creating placeholder icon file")
        try:
            # Create a minimal valid .ico file
            with open(icon_path, "wb") as f:
                # Write a minimal valid .ico file header
                f.write(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x04\x00\x28\x01\x00\x00\x16\x00\x00\x00')
                f.write(b'\x28\x00\x00\x00\x10\x00\x00\x00\x20\x00\x00\x00\x01\x00\x04\x00\x00\x00\x00\x00\x00\x00')
                f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
                f.write(b'\x00\x00\x00\x00\x00\x00')
        except:
            logger.warning("Could not create placeholder icon file")

def create_batch_file():
    """Create a batch file to run the optimized executable"""
    batch_content = '@echo off\necho Running DSSAT Viewer...\ncd dist\ndssat_viewer.exe\n'
    
    with open("run_dssat_viewer.bat", "w") as f:
        f.write(batch_content)
    
    logger.info("Created launcher: run_dssat_viewer.bat")

def build_exe_final():
    """Build a single-file executable with all issues fixed"""
    print("\n=== Building DSSAT Viewer (Final Fixed Version) ===\n")
    
    start_time = time.time()
    
    # Clean PyInstaller cache
    clean_pyinstaller_cache()
    
    # Create resources folder with icon
    create_resources_folder()
    
    # Create hook files
    create_jaraco_hook()
    create_opengl_exclusion_hook()
    
    # Run final build
    if not create_spec_file():
        return False
    
    # Create batch file
    create_batch_file()
    
    # Check if executable was created
    exe_path = os.path.join(os.getcwd(), "dist", "dssat_viewer.exe")
    if os.path.exists(exe_path):
        size_bytes = os.path.getsize(exe_path)
        size_mb = size_bytes / (1024 * 1024)
        
        build_time = time.time() - start_time
        
        print("\n=== Build Results ===")
        print(f"Executable created at: {exe_path}")
        print(f"Executable size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
        print(f"Build completed in {build_time:.1f} seconds!")
        
        return True
    else:
        print(f"Error: Executable not found at {exe_path}")
        return False

if __name__ == "__main__":
    build_exe_final()