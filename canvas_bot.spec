# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files


a = Analysis(
    ['canvas_bot.py'],
    pathex=['C:\\Users\\Fonta\\PycharmProjects\\canvas-bot-v2', 'C:\\Users\\Fonta\\PycharmProjects\\canvas-bot-v2\\config'],
    binaries=[],
    datas=[('config\\config.yaml', 'config'), ('config\\download_manifest.yaml', 'config'), ('config\\re.yaml', 'config'), ('tools\\vba\\DocumentTriggers.cls', 'tools\\vba'), ('tools\\vba\\CheckIfFileExists.bas', 'tools\\vba'), ('cb.ico', '.')]
          + collect_data_files('customtkinter'),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='canvas_bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['cb.ico'],
)
