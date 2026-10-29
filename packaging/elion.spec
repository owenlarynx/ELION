# -*- mode: python ; coding: utf-8 -*-
# Aufruf aus dem Projektordner: pyinstaller packaging/elion.spec --noconfirm
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

root = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))
if root not in sys.path:
    sys.path.insert(0, root)

hidden = []
for paket in ("uvicorn", "starlette", "fastapi", "anyio", "pydantic"):
    hidden += collect_submodules(paket)

a = Analysis(
    [os.path.join(root, "packaging", "elion_start.py")],
    pathex=[root],
    binaries=[],
    datas=[
        (os.path.join(root, "static"), "static"),
        (os.path.join(root, "prompts"), "prompts"),
    ],
    hiddenimports=hidden + [
        "main",
        "database",
        "models",
        "wrap",
        "ollama_lauf",
        "pfade",
        "routes",
        "routes.berichte",
        "routes.kinder",
        "routes.kontakte",
        "routes.medikamente",
        "routes.seed",
        "routes.pruefung",
        "sqlalchemy.dialects.sqlite",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ELION",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ELION",
)
