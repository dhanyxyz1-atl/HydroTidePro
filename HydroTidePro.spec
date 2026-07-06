# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_ROOT = Path(globals().get("SPECPATH", ".")).resolve()
ICON_PATH = PROJECT_ROOT / "assets" / "branding" / "option_b_coastal_staff" / "icon.ico"


hiddenimports = (
    collect_submodules("matplotlib.backends")
    + [
        "openpyxl",
        "pandas",
        "numpy",
        "PyQt6",
    ]
)

datas = [
    (str(PROJECT_ROOT / "sample_data"), "sample_data"),
    (str(PROJECT_ROOT / "assets"), "assets"),
]


a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["utide"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HydroTidePro",
    icon=str(ICON_PATH),
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HydroTidePro",
)
