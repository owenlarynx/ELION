"""Lokale Ollama-Lage und Modell-Download. Kein Cloud-Aufruf, keine Telemetrie."""

import json
import os
import re
import shutil
import subprocess
import sys
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
_GEMERKT = {"basis": ""}
_DIENST_VERSUCHT = False

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


def adressen() -> list[str]:
    """127.0.0.1 zuerst. Unter Windows zeigt localhost oft auf IPv6, Ollama hört auf IPv4."""
    gesetzt = os.environ.get("OLLAMA_URL", "").strip().rstrip("/")
    if gesetzt:
        endung = "/api/chat"
        if gesetzt.endswith(endung):
            gesetzt = gesetzt[: -len(endung)]
        return [gesetzt]
    liste = []
    if _GEMERKT["basis"]:
        liste.append(_GEMERKT["basis"])
    for kandidat in ("http://127.0.0.1:11434", "http://localhost:11434"):
        if kandidat not in liste:
            liste.append(kandidat)
    return liste


def ollama_programm() -> str | None:
    fund = shutil.which("ollama")
    if fund:
        return fund
    if sys.platform != "win32":
        return None
    kandidaten = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        kandidaten.append(Path(local) / "Programs" / "Ollama" / "ollama.exe")
    programme = os.environ.get("ProgramFiles", "")
    if programme:
        kandidaten.append(Path(programme) / "Ollama" / "ollama.exe")
    for pfad in kandidaten:
        if pfad.is_file():
            return str(pfad)
    return None


def dienst_starten() -> bool:
    exe = ollama_programm()
    if not exe:
        return False
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        kwargs["cwd"] = str(Path(exe).parent)
    subprocess.Popen([exe, "serve"], **kwargs)
    return True


async def _tags(basis: str):
    timeout = httpx.Timeout(2.0, connect=1.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        antwort = await client.get(basis.rstrip("/") + "/api/tags")
        antwort.raise_for_status()
        return antwort.json()


async def verbinden():
    letzter_fehler = None
    for basis in adressen():
        try:
            daten = await _tags(basis)
        except httpx.HTTPError as fehler:
            letzter_fehler = fehler
            continue
        _GEMERKT["basis"] = basis
        return daten, basis
    return None, letzter_fehler


def gemerkte_basis() -> str:
    return _GEMERKT["basis"]


def _basis() -> str:
    if _GEMERKT["basis"]:
        return _GEMERKT["basis"]
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
    global _DIENST_VERSUCHT
    from wrap import ollama_modell
    modell = ollama_modell()
    daten, _fehler = await verbinden()
    if daten is None and sys.platform == "win32" and not _DIENST_VERSUCHT and ollama_programm():
        _DIENST_VERSUCHT = True
        if dienst_starten():
            import asyncio
            await asyncio.sleep(1.2)
            daten, _fehler = await verbinden()
    vorschlaege = list(VORSCHLAEGE)
    fortschritt = _job_kopie()
    if daten is None:
        programm = ollama_programm()
        if programm:
            hinweis = (
                "Ollama ist installiert, der Dienst antwortet aber nicht. "
                "Bitte Ollama starten. Eine neue Prüfung setzt keine Ampel."
            )
            dienst = "gestoppt"
            grund = "Modell laden wartet, bis Ollama antwortet. Zuerst „Ollama starten“ oder „Erneut prüfen“."
        else:
            hinweis = (
                "Ollama ist nicht erreichbar. Eine neue Prüfung setzt keine Ampel. "
                "Beispielampeln aus den Testdaten sind gekennzeichnet und keine KI-Prüfung."
            )
            dienst = "fehlt"
            grund = "Modell laden bleibt aus, solange Ollama nicht antwortet. Ollama ist ein separates Programm."
        return {
            "erreichbar": False,
            "modell": modell,
            "modell_vorhanden": False,
            "hinweis": hinweis,
            "dienst": dienst,
            "grund": grund,
            "programm": bool(programm),
            "vorschlaege": vorschlaege,
            "fortschritt": fortschritt,
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
        "dienst": "laeuft",
        "grund": "",
        "programm": True,
        "vorschlaege": vorschlaege,
        "fortschritt": fortschritt,
    }


async def dienst_neu() -> dict:
    global _DIENST_VERSUCHT
    _DIENST_VERSUCHT = True
    gestartet = dienst_starten()
    if gestartet:
        import asyncio
        ende = asyncio.get_running_loop().time() + 6
        while asyncio.get_running_loop().time() < ende:
            daten, _fehler = await verbinden()
            if daten is not None:
                break
            await asyncio.sleep(0.4)
    stand = await lage()
    stand["start_versucht"] = gestartet
    return stand


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
