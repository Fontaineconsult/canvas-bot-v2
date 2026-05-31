# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all, collect_submodules
import _tkinter, os

# Derive Python install root from _tkinter.pyd location
_python_root = os.path.dirname(os.path.dirname(_tkinter.__file__))
_tcl_root = os.path.join(_python_root, 'tcl')

datas = [
    ('config\\config.yaml', 'config'),
    ('config\\download_manifest.yaml', 'config'),
    ('config\\re.yaml', 'config'),
    ('tools\\vba\\DocumentTriggers.cls', 'tools\\vba'),
    ('tools\\vba\\CheckIfFileExists.bas', 'tools\\vba'),
    ('cb.ico', '.'),
    # Tcl/Tk data for PyInstaller runtime hook
    (os.path.join(_tcl_root, 'tcl8.6'), '_tcl_data'),
    (os.path.join(_tcl_root, 'tk8.6'), '_tk_data'),
]
datas += collect_data_files('customtkinter')
# accessible_output2 ships screen-reader client DLLs + sound files in its
# package tree; collect_data_files grabs them so the frozen exe can speak.
datas += collect_data_files('accessible_output2')

# Collect all tkinter submodules, binaries, and data
tk_datas, tk_binaries, tk_hiddenimports = collect_all('tkinter')
datas += tk_datas

hiddenimports = (['gui', 'gui.app', 'gui.wx', 'gui.wx.app', '_tkinter',
                  'customtkinter', 'wx', 'accessible_output2',
                  'accessible_output2.outputs.auto']
                 + tk_hiddenimports
                 + collect_submodules('accessible_output2')
                 + collect_submodules('wx'))

a = Analysis(
    ['canvas_bot.py'],
    pathex=['C:\\Users\\Fonta\\PycharmProjects\\canvas-bot-v2', 'C:\\Users\\Fonta\\PycharmProjects\\canvas-bot-v2\\config'],
    binaries=tk_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
