# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('resources', 'resources')],
    hiddenimports=['jaraco.text', 'plistlib', 'pandas.core.frame', 'pandas.core.series', 'numpy.core', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'OpenGL', 'OpenGL_accelerate', 'matplotlib', 'scipy', 'tkinter', 'PyQt6.QtWebEngine', 'PyQt6.QtMultimedia', 'PyQt6.QtNetwork', 'PyQt6.QtQml', 'PyQt6.QtQuick', 'plotly', 'dash', 'IPython', 'notebook', 'sphinx', 'docutils', 'PIL', 'sqlalchemy', 'tornado', 'jinja2', 'flask', 'yaml', 'numpy.distutils', 'numpy.f2py', 'numpy.testing', 'pandas.io.formats.excel', 'pandas.io.clipboard'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='dssat_viewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
