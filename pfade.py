"""Pfade für den normalen Start und für die gepackte Windows-App."""

import os
import sys
from pathlib import Path


def ist_gepackt() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def bundle_root() -> Path:
    if ist_gepackt():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def daten_verzeichnis() -> Path:
    """Beschreibbarer Ordner. In der Einrichtung unter dem Benutzerkonto, nicht im Programmordner."""
    if ist_gepackt():
        basis = os.environ.get("LOCALAPPDATA") or str(Path.home())
        ziel = Path(basis) / "ELION"
        ziel.mkdir(parents=True, exist_ok=True)
        return ziel
    return Path.cwd()
