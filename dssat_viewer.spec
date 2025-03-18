# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\kbhattarai1\\Desktop\\dash 20250312\\dash pixel - Copy\\main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'tkinter', 'docutils', 'sphinx', 'IPython', 'PyQt5.QtWebEngine', 'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtMultimedia'],
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
