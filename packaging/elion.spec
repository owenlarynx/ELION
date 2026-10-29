# -*- mode: python ; coding: utf-8 -*-
# Aufruf aus dem Projektordner: pyinstaller packaging/elion.spec --noconfirm
from PyInstaller.utils.hooks import collect_submodules

hidden = []
for paket in ("uvicorn", "sqlalchemy", "starlette", "fastapi", "anyio", "pydantic"):
    hidden += collect_submodules(paket)

a = Analysis(
    ["packaging/elion_start.py"],
    pathex=["."],
    binaries=[],
    datas=[("static", "static"), ("prompts", "prompts")],
    hiddenimports=hidden + [
        "main",
        "database",
        "models",
        "wrap",
        "ollama_lauf",
        "pfade",
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
