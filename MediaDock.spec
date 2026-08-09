# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for MediaDock standalone Windows executable."""

import os
from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis

block_cipher = None

# Hidden imports explicitly justified by GSMTCProvider (PyWinRT dynamic bindings)
hidden_imports = [
    "winrt.windows.media.control",
    "winrt.windows.storage.streams",
    "winrt.windows.foundation",
    "winrt.system",
]

a = Analysis(
    ["src/main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
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
    name="MediaDock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
