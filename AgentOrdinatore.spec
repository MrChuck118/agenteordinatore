# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


project_dir = Path(SPECPATH)
app_name = "Agent Ordinatore"

datas = [
    (str(project_dir / "icon.ico"), "."),
    (str(project_dir / "icon.png"), "."),
]

# llama-cpp-python carica DLL native da llama_cpp/lib a runtime.
binaries = collect_dynamic_libs("llama_cpp")
datas += collect_data_files("llama_cpp", includes=["py.typed"])

hiddenimports = [
    "huggingface_hub",
    "platformdirs",
    "psutil",
    "PIL",
]
hiddenimports += collect_submodules("llama_cpp")

excludes = [
    "anthropic",
    "IPython",
    "jupyter",
    "matplotlib",
    "notebook",
    "pytest",
    "tkinter",
    "unittest",
]


a = Analysis(
    [str(project_dir / "gui.py")],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(project_dir / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)
