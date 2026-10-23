import json
import os
import re
from dataclasses import dataclass

import httpx

OLLAMA_URL = os.environ.get("ELION_OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODELL = os.environ.get("ELION_OLLAMA_MODELL", "llama3.1")

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


def baue_prompt(profil: str, medikation: str, rohtext: str, schicht: str | None) -> str:
    schicht_label = {"frueh": "Frühdienst", "spaet": "Spätdienst"}.get(schicht, "nicht angegeben")
    return f"""Du prüfst die Dokumentationsqualität eines Tagesberichts in einer stationären Einrichtung der Kinder- und Jugendhilfe.
Bewerte nicht das Kind und nicht sein Verhalten. Beurteile nur, ob der Text fachlich brauchbar dokumentiert ist.

Prüfe insbesondere:
- sachliche, beschreibende Formulierungen statt wertender oder abwertender Zuschreibungen
- fehlende Angaben, die für den Tagesverlauf erkennbar nötig wären
- Medikation: ob bei hinterlegter Medikation die Gabe oder die bewusste Nicht-Gabe dokumentiert ist
- Vorkommnisse, die eine Mitteilung an Sorgeberechtigte oder das Jugendamt nahelegen, und ob diese Mitteilung im Text steht
- die Dokumentationshinweise und Besonderheiten aus dem Profil

Schicht: {schicht_label}

Profil:
{profil}

Aktive Medikation:
{medikation}

Tagesbericht:
{rohtext}

Antworte ausschließlich mit einem JSON-Objekt, ohne Markdown und ohne weiteren Text:
{{"ampel": "gruen", "hinweise": ["kurzer Hinweis"], "kurzbegruendung": "ein bis zwei Sätze zur Dokumentationsqualität"}}

Zulässige Werte für ampel sind nur gruen, gelb oder rot.
- gruen: nachvollziehbar und für die Akte ausreichend
- gelb: brauchbar, aber mit Lücken oder unscharfen Formulierungen
- rot: wesentliche Lücken, unsachliche Sprache oder ein melderelevantes Vorkommnis ohne dokumentierte Mitteilung"""


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
    prompt = baue_prompt(profil, medikation, rohtext, schicht)
    payload = {
        "model": OLLAMA_MODELL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist eine Fachkraft für Dokumentation in der Kinder- und Jugendhilfe. "
                    "Du antwortest nur mit dem geforderten JSON. Du bewertest die Textqualität, nicht das Kind."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            antwort = await client.post(OLLAMA_URL, json=payload)
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
