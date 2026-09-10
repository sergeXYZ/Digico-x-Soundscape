# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Digico×Soundscape (one-file).

Build on the target OS/arch (no cross-compile):
  Windows:  build_exe.bat
  macOS / Linux / Raspberry Pi:  scripts/build_binary_unix.sh
  Or from a packaged zip:  ./build_binary.sh
"""

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas: list = []
binaries: list = []
hiddenimports: list = []

for package in ("flask", "werkzeug", "jinja2", "itsdangerous", "click", "markupsafe", "pythonosc"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["run_bridge.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="Digico-x-Soundscape",
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
)
