# -*- coding: utf-8 -*-
"""
Build script for creating a single-file Windows executable for DSSAT Viewer
This script handles common PyInstaller issues on Windows including:
- OpenGL platform detection
- pkg_resources scanning issues
- PyQt6 dependency management
- pyqtgraph dependency handling
- ctypes/libffi dependency inclusion
"""

import os
import sys
import shutil
import subprocess
import logging
import time
import platform
import importlib.util
import glob

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure we're on Windows
if platform.system() != 'Windows':
    logger.error("This script is for Windows only. Please use the macOS script on macOS.")
    sys.exit(1)

# Base directories
base_dir = os.getcwd()
build_dir = os.path.join(base_dir, 'build')
dist_dir = os.path.join(base_dir, 'dist')
hooks_dir = os.path.join(base_dir, 'hooks')

def setup_directories():
    """Create necessary directories for the build process"""
    for directory in [build_dir, dist_dir, hooks_dir]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # Create resources directory if needed
    resources_dir = os.path.join(base_dir, 'resources')
    os.makedirs(resources_dir, exist_ok=True)
    logger.info(f"Created directory: {resources_dir}")

def clean_build_directories():
    """Clean build and dist directories"""
    for directory in [build_dir, dist_dir]:
        if os.path.exists(directory):
            logger.info(f"Cleaning directory: {directory}")
            shutil.rmtree(directory)
            os.makedirs(directory)
    
    # Clean PyInstaller cache
    cache_dir = os.path.expanduser('~/AppData/Local/pyinstaller')
    if os.path.exists(cache_dir):
        logger.info(f"Cleaning PyInstaller cache: {cache_dir}")
        shutil.rmtree(cache_dir)
    
    # Clean __pycache__ directories
    for root, dirs, files in os.walk(base_dir):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                logger.info(f"Removing: {pycache_path}")
                shutil.rmtree(pycache_path)
    
    # Remove any faulty hook-pyqtgraph.py
    faulty_hook = os.path.join(hooks_dir, "hook-pyqtgraph.py")
    if os.path.exists(faulty_hook):
        logger.warning(f"Removing potentially faulty hook: {faulty_hook}")
        os.remove(faulty_hook)

def install_dependencies():
    """Install required dependencies for the build"""
    dependencies = [
        'pyinstaller',
        'PyQt6',
        'pyqtgraph',
        'appdirs',
        'packaging',
        'setuptools',
        'attrs',
        'importlib_metadata',
        'more_itertools',
        'zipp',
        'PyOpenGL',
        'PyOpenGL-accelerate',
        'python-dateutil',  # Required by pandas
        'pandas',
        'numpy',
        'threadpoolctl'
    ]
    
    logger.info(f"Installing required dependencies: {', '.join(dependencies)}")
    
    for package in dependencies:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])
            logger.info(f"Successfully installed/upgraded {package}")
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to install {package}: {e}")
            logger.warning(f"Build may fail due to missing {package}")
    
    # Ensure PyQt5 and pygame are uninstalled to avoid conflicts
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "PyQt5", "PyQt5-sip", "PyQt5-Qt5", "pygame"])
        logger.info("Successfully uninstalled PyQt5 and pygame")
    except subprocess.SubprocessError:
        logger.info("PyQt5 or pygame not found or already uninstalled")

def find_libffi_dll():
    """Dynamically find libffi-8.dll in the Python installation"""
    search_paths = [
        os.path.join(sys.prefix, 'DLLs'),
        os.path.join(sys.prefix, 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin'),
        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Programs', 'Python', 'Python313', 'DLLs'),
        os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python313', 'site-packages', 'PyQt6', 'Qt6', 'bin')
    ]
    
    for path in search_paths:
        pattern = os.path.join(path, 'libffi-8.dll')
        matches = glob.glob(pattern)
        if matches:
            logger.info(f"Found libffi-8.dll at: {matches[0]}")
            return matches[0]
    
    logger.warning("libffi-8.dll not found in standard paths. Build may fail.")
    return None

def create_pkg_resources_hook():
    """Create runtime hook for pkg_resources to fix scanning issues"""
    runtime_hook_content = """
# PyInstaller runtime hook to fix pkg_resources scanning issues
import os
import sys

def patch_pkg_resources():
    try:
        import pkg_resources
        
        # Get original working_set
        original_working_set = pkg_resources.working_set
        
        # Monkey patch the processing of paths in WorkingSet
        original_add_entry = original_working_set.add_entry
        
        def safe_add_entry(self, entry):
            # Skip temporary directories that might cause problems
            if isinstance(entry, str) and any(x in entry.lower() for x in ['\\\\temp\\\\', '\\\\tmp\\\\', '_MEI']):
                return
            try:
                original_add_entry(entry)
            except Exception:
                # If any error occurs during path scanning, just ignore this path
                pass
                
        # Apply the patch
        original_working_set.add_entry = lambda entry: safe_add_entry(original_working_set, entry)
        
        print("Successfully patched pkg_resources")
    except Exception as e:
        print(f"Error patching pkg_resources: {e}")
        
# Apply the patch
patch_pkg_resources()
"""
    
    hook_path = os.path.join(hooks_dir, "pkg_resources_hook.py")
    with open(hook_path, "w") as f:
        f.write(runtime_hook_content)
    logger.info(f"Created runtime hook for pkg_resources: {hook_path}")
    return "pkg_resources_hook.py"

def create_pkg_resources_import_hook():
    """Create a hook to ensure pkg_resources dependencies are included"""
    hook_content = """
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Add missing dependencies
hiddenimports = [
    'jaraco.text', 
    'plistlib', 
    'appdirs', 
    'packaging', 
    'packaging.version', 
    'packaging.specifiers', 
    'packaging.requirements', 
    'packaging.markers',
    'importlib_metadata',
    'zipp',
    'attrs',
    'more_itertools'
]

# Add data files
datas = collect_data_files('pkg_resources')
"""
    hook_path = os.path.join(hooks_dir, "hook-pkg_resources.py")
    with open(hook_path, "w") as f:
        f.write(hook_content)
    logger.info(f"Created import hook for pkg_resources: {hook_path}")

def create_opengl_hook():
    """Create OpenGL hooks to fix Windows platform detection"""
    # Runtime hook to patch OpenGL platform detection
    runtime_hook_content = """
# PyInstaller runtime hook to fix OpenGL platform detection on Windows
import os
import sys

def patch_opengl():
    try:
        # Set environment variables before importing OpenGL
        os.environ["PYOPENGL_PLATFORM"] = "wgl"
        
        # Disable acceleration which can cause issues
        os.environ["PYOPENGL_ACCELERATE_DISABLE"] = "1"
        
        # Import OpenGL with these settings already in place
        import OpenGL
        OpenGL.ERROR_CHECKING = False
        
        print("Successfully configured OpenGL for Windows")
    except Exception as e:
        print(f"Error configuring OpenGL: {e}")
        
# Apply the patch
patch_opengl()
"""
    runtime_hook_path = os.path.join(hooks_dir, "opengl_hook.py")
    with open(runtime_hook_path, "w") as f:
        f.write(runtime_hook_content)
    logger.info(f"Created runtime hook for OpenGL: {runtime_hook_path}")
    
    # Import hook to collect all OpenGL modules
    import_hook_content = """
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all PyOpenGL submodules
hiddenimports = collect_submodules('OpenGL')

# Don't forget the OpenGL_accelerate module
hiddenimports += collect_submodules('OpenGL_accelerate')

# Collect any data files
datas = collect_data_files('OpenGL')
"""
    import_hook_path = os.path.join(hooks_dir, "hook-OpenGL.py")
    with open(import_hook_path, "w") as f:
        f.write(import_hook_content)
    logger.info(f"Created import hook for OpenGL: {import_hook_path}")
    
    return "opengl_hook.py"

def create_attrs_hook():
    """Create a hook for attrs to ensure all submodules are included"""
    hook_content = """
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Make sure we include all attrs submodules
hiddenimports = collect_submodules('attrs')

# Add data files
datas = collect_data_files('attrs')
"""
    hook_path = os.path.join(hooks_dir, "hook-attrs.py")
    with open(hook_path, "w") as f:
        f.write(hook_content)
    logger.info(f"Created import hook for attrs: {hook_path}")

def create_ctypes_hook():
    """Create a hook to ensure ctypes and libffi are included"""
    hook_content = """
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Include ctypes and its dependencies
hiddenimports = collect_submodules('ctypes')

# Collect libffi DLL
datas = collect_data_files('ctypes')
"""
    hook_path = os.path.join(hooks_dir, "hook-ctypes.py")
    with open(hook_path, "w") as f:
        f.write(hook_content)
    logger.info(f"Created import hook for ctypes: {hook_path}")

def create_pygame_hook():
    """Create a hook to explicitly exclude pygame"""
    hook_content = """
# Empty hook to ensure pygame is not included
hiddenimports = []
datas = []
"""
    hook_path = os.path.join(hooks_dir, "hook-pygame.py")
    with open(hook_path, "w") as f:
        f.write(hook_content)
    logger.info(f"Created import hook for pygame: {hook_path}")

def create_pyqtgraph_hook():
    """Create a hook for pyqtgraph to ensure all submodules are included"""
    hook_content = """
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all pyqtgraph submodules as hidden imports
hiddenimports = collect_submodules('pyqtgraph')

# Collect any data files
datas = collect_data_files('pyqtgraph')
"""
    hook_path = os.path.join(hooks_dir, "hook-pyqtgraph.py")
    with open(hook_path, "w") as f:
        f.write(hook_content)
    logger.info(f"Created import hook for pyqtgraph: {hook_path}")

def create_spec_file(pkg_hook, opengl_hook):
    """Create a spec file for PyInstaller"""
    # Get pyqtgraph path if available
    pyqtgraph_path = ''
    pyqtgraph_spec = importlib.util.find_spec('pyqtgraph')
    if pyqtgraph_spec:
        pyqtgraph_path = os.path.dirname(pyqtgraph_spec.origin)
    
    # Find libffi-8.dll
    libffi_path = find_libffi_dll()
    binaries = []
    if libffi_path:
        binaries.append((libffi_path, '.'))
    
    spec_content = f"""
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
    pathex=[{repr(pyqtgraph_path)}] if {repr(pyqtgraph_path)} else [],
    binaries={binaries},
    datas=[('resources', 'resources')],
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={{'pyqt6': {{'plugins': qt_plugins}}}},
    runtime_hooks=[
        f'hooks/{pkg_hook}',
        f'hooks/{opengl_hook}'
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
"""
    spec_path = os.path.join(base_dir, "dssat_viewer.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)
    logger.info(f"Created spec file: {spec_path}")
    return spec_path

def create_launcher_script():
    """Create a batch file to launch the application"""
    script_content = """@echo off
echo Running DSSAT Viewer...
cd dist
dssat_viewer.exe
"""
    script_path = os.path.join(base_dir, "run_dssat_viewer.bat")
    with open(script_path, "w") as f:
        f.write(script_content)
    logger.info(f"Created launcher script: {script_path}")

def build_executable(spec_path):
    """Run PyInstaller to build the executable"""
    build_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--log-level",
        "INFO",
        spec_path
    ]
    
    logger.info(f"Running PyInstaller: {' '.join(build_cmd)}")
    
    try:
        subprocess.check_call(build_cmd)
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"PyInstaller build failed: {e}")
        return False

def finalize_build():
    """Perform final steps after successful build"""
    exe_path = os.path.join(dist_dir, "dssat_viewer.exe")
    
    if os.path.exists(exe_path):
        # Create empty __init__.py in dist directory as an additional safeguard
        init_path = os.path.join(dist_dir, "__init__.py")
        with open(init_path, "w") as f:
            f.write("# Empty __init__.py to prevent scanning issues")
        
        # Get executable size
        size_bytes = os.path.getsize(exe_path)
        size_mb = size_bytes / (1024 * 1024)
        
        print("\n=== Build Results ===")
        print(f"Executable created at: {exe_path}")
        print(f"Executable size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
        
        print("\nTo run the application, you can:")
        print("1. Run 'run_dssat_viewer.bat' in Command Prompt")
        print(f"2. Double-click 'dist\\dssat_viewer.exe'")
        
        return True
    else:
        logger.error(f"Executable not found at: {exe_path}")
        return False

def main():
    """Main function to build the executable"""
    print("\n=== Building DSSAT Viewer for Windows (Single-File Executable) ===\n")
    
    start_time = time.time()
    
    # Setup and clean directories
    setup_directories()
    clean_build_directories()
    
    # Install dependencies
    install_dependencies()
    
    # Create hooks
    pkg_hook = create_pkg_resources_hook()
    opengl_hook = create_opengl_hook()
    create_pkg_resources_import_hook()
    create_attrs_hook()
    create_ctypes_hook()
    create_pygame_hook()
    create_pyqtgraph_hook()
    
    # Create spec file
    spec_path = create_spec_file(pkg_hook, opengl_hook)
    
    # Create launcher script
    create_launcher_script()
    
    # Build executable
    if build_executable(spec_path):
        finalize_build()
        
        build_time = time.time() - start_time
        print(f"\nBuild completed in {build_time:.1f} seconds!")
        return 0
    else:
        print("\nBuild failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())