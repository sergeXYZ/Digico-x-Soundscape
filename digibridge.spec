# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Digico×Soundscape (windowed app, bundled deps).

Build on the target OS/arch (no cross-compile):
  Windows:  build_exe.bat
  macOS / Linux / Raspberry Pi:  scripts/build_binary_unix.sh
  Or from a packaged zip:  ./build_binary.sh

macOS: onedir Digico-x-Soundscape.app (double-clickable).
Windows/Linux: windowed one-file binary (no console).
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
ROOT = Path(SPECPATH)

datas: list = [
    (str(ROOT / "assets" / "logo-64.png"), "assets"),
    (str(ROOT / "assets" / "logo-192.png"), "assets"),
    (str(ROOT / "assets" / "logo.png"), "assets"),
    (str(ROOT / "assets" / "warning-18.png"), "assets"),
    (str(ROOT / "assets" / "warning-dd.png"), "assets"),
    (str(ROOT / "assets" / "warning.png"), "assets"),
]
binaries: list = []
hiddenimports: list = []

for package in (
    "flask",
    "werkzeug",
    "jinja2",
    "itsdangerous",
    "click",
    "markupsafe",
    "pythonosc",
    "webview",
):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

ICON_ICNS = str(ROOT / "assets" / "Digico-x-Soundscape.icns")
ICON_ICO = str(ROOT / "assets" / "Digico-x-Soundscape.ico")

a = Analysis(
    ["run_bridge.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports
    + [
        "bridge.webview_app",
        "bridge.launcher_gui",
        "bridge.resources",
        "bridge.web_gui",
        "bridge.bridge_app",
        "bridge.digico_client",
        "bridge.ds100_client",
        "bridge.sync_engine",
        "bridge.settings",
        "bridge.mapping",
        "bridge.connection_monitor",
        "bridge.net_utils",
        "bridge.osc_utils",
        "bridge.constants",
    ],
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

# macOS: onedir + .app (required; onefile+.app is deprecated / blocked in PyInstaller 7)
if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="Digico-x-Soundscape",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_ICNS,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="Digico-x-Soundscape",
    )
    app = BUNDLE(
        coll,
        name="Digico-x-Soundscape.app",
        icon=ICON_ICNS,
        bundle_identifier="com.sergexyz.digico-x-soundscape",
        info_plist={
            "CFBundleName": "Digico×Soundscape",
            "CFBundleDisplayName": "Digico×Soundscape",
            "CFBundleShortVersionString": "0.3.0",
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
        },
    )
else:
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
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_ICO if Path(ICON_ICO).is_file() else None,
    )
