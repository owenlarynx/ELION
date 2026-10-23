import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

APP_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPT = APP_DIR / "prompts" / "ra_thor_wrap.md"
RA_THOR_START = "<<<RA_THOR_WRAP>>>"
RA_THOR_ENDE = "<<<ENDE_RA_THOR_WRAP>>>"

AMPEL_WERTE = {
    "gruen": "gruen",
    "grün": "gruen",
    "green": "gruen",
    "gelb": "gelb",
    "yellow": "gelb",
    "rot": "rot",
    "red": "rot",
}

AMPEL_LABEL = {"gruen": "Grün", "gelb": "Gelb", "rot": "Rot"}


@dataclass
class PruefErgebnis:
    ampel: str | None
    text: str


def kind_profiltext(vorname: str, nachname: str | None, besonderheiten: str | None, dokumentationshinweise: str | None) -> str:
    name = vorname + (f" {nachname}" if nachname else "")
    return (
        f"Name: {name}\n"
        f"Besonderheiten: {besonderheiten.strip() if besonderheiten and besonderheiten.strip() else 'keine Angaben'}\n"
        f"Dokumentationshinweise: {dokumentationshinweise.strip() if dokumentationshinweise and dokumentationshinweise.strip() else 'keine Angaben'}"
    )


def medikamente_text(medikamente: list) -> str:
    if not medikamente:
        return "Keine aktive Medikation hinterlegt."
    zeilen = []
    for med in medikamente:
        teile = [med.name]
        if med.dosierung:
            teile.append(med.dosierung)
        if med.einnahmezeit:
            teile.append(f"Einnahme: {med.einnahmezeit}")
        zeile = "- " + ", ".join(teile)
        if med.hinweis:
            zeile += f" ({med.hinweis})"
        zeilen.append(zeile)
    return "\n".join(zeilen)


def ollama_chat_url() -> str:
    roh = os.environ.get("OLLAMA_URL", "http://localhost:11434").strip().rstrip("/")
    if roh.endswith("/api/chat"):
        return roh
    return roh + "/api/chat"


def ollama_modell() -> str:
    name = os.environ.get("OLLAMA_MODEL", "llama3.1").strip()
    return name or "llama3.1"


def prompt_pfad() -> Path:
    roh = os.environ.get("ELION_PROMPT_PATH", "").strip()
    if not roh:
        return DEFAULT_PROMPT
    pfad = Path(roh)
    if not pfad.is_absolute():
        return APP_DIR / pfad
    return pfad


def teile_vorlage(text: str) -> tuple[str, str]:
    system: list[str] = []
    auftrag: list[str] = []
    ziel = None
    for zeile in text.splitlines():
        if zeile.strip() == "# System":
            ziel = "system"
            continue
        if zeile.strip() == "# Auftrag":
            ziel = "auftrag"
            continue
        if ziel == "system":
            system.append(zeile)
        elif ziel == "auftrag":
            auftrag.append(zeile)
    if not any(zeile.strip() for zeile in auftrag):
        raise ValueError("Prüfvorlage ohne Abschnitt # Auftrag")
    systemtext = "\n".join(system).strip()
    if not systemtext:
        systemtext = (
            "Du bist eine Fachkraft für Dokumentation in der Kinder- und Jugendhilfe. "
            "Du antwortest nur mit dem geforderten JSON. Du bewertest die Textqualität, nicht das Kind."
        )
    return systemtext, "\n".join(auftrag).strip()


def ohne_ra_thor_marken(text: str) -> str:
    if RA_THOR_START not in text or RA_THOR_ENDE not in text:
        return text
    vorher, rest = text.split(RA_THOR_START, 1)
    innen, nachher = rest.split(RA_THOR_ENDE, 1)
    inhalt = re.sub(r"<!--.*?-->", "", innen, flags=re.DOTALL).strip()
    mitte = f"\n\n{inhalt}\n\n" if inhalt else "\n\n"
    zusammen = vorher.rstrip() + mitte + nachher.lstrip()
    return re.sub(r"\n{3,}", "\n\n", zusammen).strip()


def baue_prompt(profil: str, medikation: str, rohtext: str, schicht: str | None) -> tuple[str, str]:
    pfad = prompt_pfad()
    try:
        vorlage = pfad.read_text(encoding="utf-8")
    except FileNotFoundError as fehler:
        raise FileNotFoundError(pfad.name) from fehler
    system, auftrag = teile_vorlage(vorlage)
    auftrag = ohne_ra_thor_marken(auftrag)
    schicht_label = {"frueh": "Frühdienst", "spaet": "Spätdienst"}.get(schicht, "nicht angegeben")
    ersatz = {
        "{schicht}": schicht_label,
        "{profil}": profil,
        "{medikation}": medikation,
        "{rohtext}": rohtext,
    }
    for token, wert in ersatz.items():
        system = system.replace(token, wert)
        auftrag = auftrag.replace(token, wert)
    return system, auftrag


def _json_objekt(roh: str):
    text = (roh or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        daten = json.loads(text)
        if isinstance(daten, dict):
            return daten
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    ende = text.rfind("}")
    if start != -1 and ende > start:
        try:
            daten = json.loads(text[start:ende + 1])
            if isinstance(daten, dict):
                return daten
        except json.JSONDecodeError:
            return None
    return None


def _ampel_aus_wert(wert) -> str | None:
    if not isinstance(wert, str):
        return None
    schluessel = wert.strip().lower().strip(" .,;:")
    return AMPEL_WERTE.get(schluessel)


def _hinweise(wert) -> list[str]:
    if isinstance(wert, str) and wert.strip():
        return [wert.strip()]
    if isinstance(wert, list):
        return [str(eintrag).strip() for eintrag in wert if str(eintrag).strip()]
    return []


def _formatiere(ampel: str, hinweise: list[str], begruendung: str) -> str:
    zeilen = [f"Ampel: {AMPEL_LABEL[ampel]}"]
    if begruendung:
        zeilen.append(begruendung)
    if hinweise:
        zeilen.append("Hinweise:")
        zeilen.extend(f"- {hinweis}" for hinweis in hinweise)
    return "\n".join(zeilen)


def _ohne_ampel(text: str) -> PruefErgebnis:
    return PruefErgebnis(ampel=None, text=text)


def parse_pruef_antwort(roh: str) -> PruefErgebnis:
    daten = _json_objekt(roh)
    if not isinstance(daten, dict):
        return _ohne_ampel(
            "Die Prüfung hat kein lesbares Ergebnis geliefert. Es wurde keine Ampel gesetzt."
        )
    ampel = _ampel_aus_wert(daten.get("ampel"))
    hinweise = _hinweise(daten.get("hinweise"))
    begruendung = daten.get("kurzbegruendung") or daten.get("begruendung") or ""
    if not isinstance(begruendung, str):
        begruendung = str(begruendung)
    begruendung = begruendung.strip()
    if ampel is None:
        teile = ["Die Prüfung enthält keine gültige Ampel. Es wurde keine Ampel gesetzt."]
        if begruendung:
            teile.append(begruendung)
        if hinweise:
            teile.append("Hinweise:")
            teile.extend(f"- {hinweis}" for hinweis in hinweise)
        return _ohne_ampel("\n".join(teile))
    return PruefErgebnis(ampel=ampel, text=_formatiere(ampel, hinweise, begruendung))


def _nicht_moeglich(grund: str) -> PruefErgebnis:
    return _ohne_ampel(f"Prüfung nicht möglich: {grund}. Es wurde keine Ampel gesetzt.")


async def pruefe_bericht(profil: str, medikation: str, rohtext: str, schicht: str | None = None) -> PruefErgebnis:
    try:
        system, prompt = baue_prompt(profil, medikation, rohtext, schicht)
    except FileNotFoundError as fehler:
        return _nicht_moeglich(f"die Prüfvorlage wurde nicht gefunden ({fehler})")
    except UnicodeDecodeError:
        return _nicht_moeglich("die Prüfvorlage konnte nicht gelesen werden")
    except ValueError:
        return _nicht_moeglich("die Prüfvorlage hat keinen Abschnitt # Auftrag")
    except OSError:
        return _nicht_moeglich("die Prüfvorlage konnte nicht gelesen werden")
    payload = {
        "model": ollama_modell(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            antwort = await client.post(ollama_chat_url(), json=payload)
            antwort.raise_for_status()
            body = antwort.json()
    except httpx.HTTPError:
        return _nicht_moeglich("Ollama ist nicht erreichbar")
    except (ValueError, TypeError):
        return _nicht_moeglich("die Antwort von Ollama war unvollständig")

    message = body.get("message") if isinstance(body, dict) else None
    inhalt = message.get("content") if isinstance(message, dict) else None
    if not isinstance(inhalt, str):
        return _nicht_moeglich("die Antwort von Ollama war unvollständig")
    return parse_pruef_antwort(inhalt)
