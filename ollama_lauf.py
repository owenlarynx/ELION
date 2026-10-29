"""Lokale Ollama-Lage und Modell-Download. Kein Cloud-Aufruf, keine Telemetrie."""

import json
import re
import threading
from pathlib import Path

import httpx

from database import database_url

VORSCHLAEGE = ("llama3.1:8b", "qwen2.5:7b", "qwen2.5:14b")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,80}$")
_SPERR = threading.Lock()
_JOB = {
    "laeuft": False,
    "fertig": False,
    "fehler": None,
    "status": "",
    "prozent": None,
    "modell": None,
}


def modell_gueltig(name: str) -> bool:
    return bool(_NAME.match(name or ""))


def einstellungsdatei() -> Path:
    url = database_url()
    if url.startswith("sqlite:///"):
        roh = url[len("sqlite:///") :]
        return Path(roh).expanduser().resolve().with_name("elion_modell.json")
    return Path("elion_modell.json").resolve()


def gespeichertes_modell() -> str | None:
    try:
        daten = json.loads(einstellungsdatei().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(daten, dict):
        return None
    name = daten.get("modell")
    if isinstance(name, str) and modell_gueltig(name.strip()):
        return name.strip()
    return None


def modell_merken(name: str) -> None:
    pfad = einstellungsdatei()
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps({"modell": name}, ensure_ascii=False), encoding="utf-8")


def fortschritt_aus_objekt(obj: dict) -> dict:
    total = obj.get("total") or 0
    completed = obj.get("completed") or 0
    try:
        prozent = int(int(completed) * 100 / int(total)) if int(total) else None
    except (TypeError, ValueError, ZeroDivisionError):
        prozent = None
    if prozent is not None:
        prozent = max(0, min(100, prozent))
    return {"status": str(obj.get("status") or ""), "prozent": prozent}


def _job_kopie() -> dict:
    with _SPERR:
        return dict(_JOB)


def _basis() -> str:
    from wrap import ollama_basis
    return ollama_basis()


def _namen(daten) -> list[str]:
    if not isinstance(daten, dict):
        return []
    namen = []
    for eintrag in daten.get("models") or []:
        if isinstance(eintrag, dict) and eintrag.get("name"):
            namen.append(str(eintrag["name"]))
    return namen


def modell_passt(vorhanden: str, gesucht: str) -> bool:
    return vorhanden == gesucht or vorhanden.startswith(gesucht + "-")


async def lage() -> dict:
    from wrap import ollama_modell
    modell = ollama_modell()
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            antwort = await client.get(_basis() + "/api/tags")
            antwort.raise_for_status()
            daten = antwort.json()
    except httpx.HTTPError:
        return {
            "erreichbar": False,
            "modell": modell,
            "modell_vorhanden": False,
            "hinweis": (
                "Ollama ist nicht erreichbar. Eine neue Prüfung setzt keine Ampel. "
                "Beispielampeln aus den Testdaten sind gekennzeichnet und keine KI-Prüfung."
            ),
            "vorschlaege": list(VORSCHLAEGE),
            "fortschritt": _job_kopie(),
        }
    vorhanden = any(modell_passt(name, modell) for name in _namen(daten))
    if vorhanden:
        hinweis = f"Prüfung bereit. Modell {modell}."
    else:
        hinweis = (
            f"Ollama läuft. Das Modell {modell} ist noch nicht geladen. "
            "Der Download startet erst nach Zustimmung."
        )
    return {
        "erreichbar": True,
        "modell": modell,
        "modell_vorhanden": vorhanden,
        "hinweis": hinweis,
        "vorschlaege": list(VORSCHLAEGE),
        "fortschritt": _job_kopie(),
    }


def _ziehen(modell: str) -> None:
    try:
        with httpx.Client(timeout=None) as client:
            with client.stream("POST", _basis() + "/api/pull", json={"name": modell, "stream": True}) as antwort:
                antwort.raise_for_status()
                for zeile in antwort.iter_lines():
                    if not zeile:
                        continue
                    try:
                        obj = json.loads(zeile)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    stand = fortschritt_aus_objekt(obj)
                    with _SPERR:
                        _JOB["status"] = stand["status"]
                        if stand["prozent"] is not None:
                            _JOB["prozent"] = stand["prozent"]
                        if obj.get("error"):
                            _JOB["fehler"] = "Ollama konnte das Modell nicht laden."
                            _JOB["laeuft"] = False
                            return
        with _SPERR:
            _JOB["laeuft"] = False
            _JOB["fertig"] = True
            _JOB["prozent"] = 100
            _JOB["status"] = "fertig"
            _JOB["fehler"] = None
    except httpx.HTTPError:
        with _SPERR:
            _JOB["laeuft"] = False
            _JOB["fertig"] = False
            _JOB["fehler"] = "Ollama hat das Modell nicht geladen. Es wurde keine Ampel gesetzt."


def pull_starten(modell: str) -> dict:
    with _SPERR:
        if _JOB["laeuft"]:
            return dict(_JOB)
        _JOB.update({
            "laeuft": True,
            "fertig": False,
            "fehler": None,
            "status": "Download beginnt",
            "prozent": 0,
            "modell": modell,
        })
    threading.Thread(target=_ziehen, args=(modell,), daemon=True).start()
    return _job_kopie()
