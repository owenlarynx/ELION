import json
import os
import re
from dataclasses import dataclass, field
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
    hinweise: list[str] = field(default_factory=list)
    verbesserte_fassung: str | None = None
    kurzbegruendung: str | None = None
    umformulierungen: list[dict] = field(default_factory=list)


_SCHICHT_ZEIT = {
    "frueh": ("früh", "frueh", "morgen", "vormittag", "mittag"),
    "mittel": (
        "früh", "frueh", "morgen", "vormittag", "mittag", "nachmittag",
        "abend", "spät", "spaet", "tagsüber", "tagsueber",
    ),
    "spaet": ("nachmittag", "abend", "spät", "spaet"),
    "nacht": ("nacht",),
}
_JEDE_SCHICHT = (
    "täglich", "taeglich", "jeden tag", "bei bedarf", "dauerhaft",
    "alle schichten", "durchgehend",
)
_KEINE_MEDIKATION = (
    "Keine Medikation für diese Schicht hinterlegt. "
    "Medikation weder in den Hinweisen noch in der verbesserten Fassung erwähnen "
    "und nicht als fehlende Angabe werten."
)
PLATZHALTER = re.compile(r"\[Bitte ergänzen:[^\]]+\]", re.IGNORECASE)
_ZITAT_MUSTER = (
    re.compile(r"„([^“]{4,180})“"),
    re.compile(r"«([^»]{4,180})»"),
    re.compile(r"‚([^‘]{4,180})‘"),
    re.compile(r"(?<![\w])\"([^\"]{4,180})\"(?![\w])"),
    re.compile(r"(?<![\w])'([^']{4,180})'(?![\w])"),
)


def _zeitwort(text: str, wort: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(wort)}", text, flags=re.IGNORECASE) is not None


def medikament_passt(einnahmezeit: str | None, schicht: str | None) -> bool:
    """Ob eine Einnahmezeit zu dieser Schicht gehört. Unklare Zeiten gelten für jede Schicht."""
    if schicht not in _SCHICHT_ZEIT:
        return True
    text = (einnahmezeit or "").strip().lower()
    if not text or any(_zeitwort(text, wort) for wort in _JEDE_SCHICHT):
        return True
    if any(_zeitwort(text, wort) for wort in _SCHICHT_ZEIT[schicht]):
        return True
    fremd = [
        wort
        for schluessel, woerter in _SCHICHT_ZEIT.items()
        if schluessel != schicht
        for wort in woerter
    ]
    if any(_zeitwort(text, wort) for wort in fremd):
        return False
    return True


def anrede_anweisung(vorname: str | None, besonderheiten: str | None, dokumentationshinweise: str | None) -> str:
    name = (vorname or "").strip() or "das Kind"
    text = f"{besonderheiten or ''}\n{dokumentationshinweise or ''}".lower()
    sie = re.search(r"pronomen\s*:\s*sie\b|geschlecht\s*:\s*w|\bweiblich\b|\bmädchen\b", text)
    er = re.search(r"pronomen\s*:\s*er\b|geschlecht\s*:\s*m|\bmännlich\b|\bjunge\b", text)
    verbot = "Niemals „der Jugendliche“, „die Jugendliche“ oder „Jugendlicher“."
    if sie and not er:
        return f"Das Kind heißt {name}. Verwende den Namen {name} oder das Pronomen „sie“. {verbot}"
    if er and not sie:
        return f"Das Kind heißt {name}. Verwende den Namen {name} oder das Pronomen „er“. {verbot}"
    return (
        f"Das Kind heißt {name}. Verwende ausschließlich den Namen {name}, kein erratenes er oder sie. {verbot}"
    )


def kind_profiltext(vorname: str, nachname: str | None, besonderheiten: str | None, dokumentationshinweise: str | None) -> str:
    name = vorname + (f" {nachname}" if nachname else "")
    return (
        f"Name: {name}\n"
        f"Besonderheiten: {besonderheiten.strip() if besonderheiten and besonderheiten.strip() else 'keine Angaben'}\n"
        f"Dokumentationshinweise: {dokumentationshinweise.strip() if dokumentationshinweise and dokumentationshinweise.strip() else 'keine Angaben'}"
    )


def medikamente_text(medikamente: list, schicht: str | None = None) -> str:
    passend = [med for med in medikamente if medikament_passt(getattr(med, "einnahmezeit", None), schicht)]
    if not passend:
        return _KEINE_MEDIKATION
    zeilen = ["Nur diese Medikation ist für die Schicht relevant. Andere Zeiten nicht ansprechen."]
    for med in passend:
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


def ollama_basis() -> str:
    url = ollama_chat_url()
    endung = "/api/chat"
    if url.endswith(endung):
        return url[: -len(endung)]
    return url


def ollama_modell() -> str:
    name = os.environ.get("OLLAMA_MODEL", "").strip()
    if name:
        return name
    try:
        from ollama_lauf import gespeichertes_modell
        gespeichert = gespeichertes_modell()
    except Exception:
        gespeichert = None
    if gespeichert:
        return gespeichert
    return "llama3.1:8b"


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


def baue_prompt(profil: str, medikation: str, rohtext: str, schicht: str | None, anrede: str | None = None) -> tuple[str, str]:
    pfad = prompt_pfad()
    try:
        vorlage = pfad.read_text(encoding="utf-8")
    except FileNotFoundError as fehler:
        raise FileNotFoundError(pfad.name) from fehler
    system, auftrag = teile_vorlage(vorlage)
    auftrag = ohne_ra_thor_marken(auftrag)
    schicht_label = {
        "frueh": "Frühdienst",
        "mittel": "Mitteldienst (etwa 12 Stunden)",
        "spaet": "Spätdienst",
        "nacht": "Nachtdienst",
    }.get(schicht, "nicht angegeben")
    ersatz = {
        "{schicht}": schicht_label,
        "{profil}": profil,
        "{medikation}": medikation,
        "{rohtext}": rohtext,
        "{anrede}": anrede or "Verwende den Vornamen aus dem Profil. Niemals „der Jugendliche“ oder „die Jugendliche“.",
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


def hat_platzhalter(text: str | None) -> bool:
    return bool(text and PLATZHALTER.search(text))


def zitate(text: str) -> list[str]:
    if not text:
        return []
    funde = []
    for muster in _ZITAT_MUSTER:
        funde.extend(treffer.strip() for treffer in muster.findall(text) if treffer and treffer.strip())
    return funde


def _norm(text: str) -> str:
    text = text.lower().replace("ß", "ss")
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def zitat_belegt(zitat: str, rohtext: str) -> bool:
    if not (rohtext or "").strip():
        return True
    normal = _norm(zitat)
    quelle = _norm(rohtext)
    if normal and normal in quelle:
        return True
    knapp = re.sub(r"[^\w\s]", "", normal, flags=re.UNICODE)
    quelle_knapp = re.sub(r"[^\w\s]", "", quelle, flags=re.UNICODE)
    return bool(knapp) and knapp in quelle_knapp


def hinweise_filtern(hinweise: list[str], rohtext: str) -> list[str]:
    behalten = []
    for hinweis in hinweise:
        if all(zitat_belegt(zitat, rohtext) for zitat in zitate(hinweis)):
            behalten.append(hinweis)
    return behalten


def begruendung_filtern(text: str, rohtext: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    saetze = re.split(r"(?<=[.!?])\s+", text)
    behalten = [
        satz
        for satz in saetze
        if all(zitat_belegt(zitat, rohtext) for zitat in zitate(satz))
    ]
    return " ".join(behalten).strip()


_MED_WORT = re.compile(
    r"medikation|medikament|\bmedis\b|tablette|tropfen|dosierung|einnahme",
    re.IGNORECASE,
)
_MELDUNG = re.compile(r"jugendamt|sorgeberechtigt", re.IGNORECASE)
_VORFALL = re.compile(
    r"verletz|gewalt|entweich|selbstgef|fremdgef|geschlagen|suizid|notarzt",
    re.IGNORECASE,
)
_JUGENDLICH = re.compile(
    r"\b(?:der|die|dem|den|des|einem|einer|eines)\s+jugendlich\w*\b",
    re.IGNORECASE,
)
_ECHO = (
    "verwenden sachlicher",
    "abwertender zuschreibung",
    "vorkommnisse, die eine mitteilung",
    "fehlende angaben wie",
    "pruefe insbesondere",
)


def enthaelt_medikation(text: str | None) -> bool:
    return bool(text and _MED_WORT.search(text))


def _saetze(text: str) -> list[str]:
    return [satz.strip() for satz in re.split(r"(?<=[.!?])\s+", text or "") if satz.strip()]


def _satz_ohne_medikation(satz: str) -> str:
    if not enthaelt_medikation(satz):
        return satz
    teile = re.split(r"(?<=,)\s+|\s+\bund\b\s+", satz)
    behalten = [teil.strip(" ,") for teil in teile if teil.strip(" ,") and not enthaelt_medikation(teil)]
    if not behalten:
        return ""
    text = " ".join(behalten)
    if satz.rstrip().endswith((".", "!", "?")) and not text.endswith((".", "!", "?")):
        text += satz.rstrip()[-1]
    return text


def ohne_medikationstext(text: str | None) -> str:
    if not text:
        return ""
    ohne_platzhalter = PLATZHALTER.sub(
        lambda fund: "" if enthaelt_medikation(fund.group(0)) else fund.group(0),
        text,
    )
    behalten = [satz for satz in (_satz_ohne_medikation(satz) for satz in _saetze(ohne_platzhalter)) if satz]
    return re.sub(r"[ \t]{2,}", " ", " ".join(behalten)).strip()


def meldung_erlaubt(rohtext: str | None) -> bool:
    quelle = rohtext or ""
    return bool(_VORFALL.search(quelle) or _MELDUNG.search(quelle))


def ohne_uebergriff(text: str | None, rohtext: str) -> str:
    if not text or meldung_erlaubt(rohtext):
        return text or ""
    behalten = [satz for satz in _saetze(text) if not _MELDUNG.search(satz)]
    return " ".join(behalten).strip()


def namen_setzen(text: str | None, vorname: str | None) -> str | None:
    if not text or not (vorname or "").strip():
        return text
    return _JUGENDLICH.sub(vorname.strip(), text)


def hinweis_behaltbar(hinweis: str, rohtext: str, medikamente_vorhanden: bool) -> bool:
    if any(teil in _norm(hinweis) for teil in _ECHO):
        return False
    if not medikamente_vorhanden and enthaelt_medikation(hinweis):
        return False
    if _MELDUNG.search(hinweis) and not meldung_erlaubt(rohtext):
        return False
    if _MELDUNG.search(hinweis) and meldung_erlaubt(rohtext):
        return True
    return hinweis_geerdet(hinweis, rohtext)


_STOPP = {
    "aber", "als", "auch", "auf", "aus", "bei", "bin", "bis", "bist", "da", "dabei", "dadurch",
    "dann", "danach", "dass", "dem", "den", "der", "des", "die", "dies", "diese", "dieser",
    "dieses", "doch", "dort", "du", "durch", "ein", "eine", "einem", "einen", "einer", "er",
    "es", "fuer", "ganz", "gut", "haben", "hat", "hatte", "hier", "hin", "ich", "ihm", "ihn",
    "ihr", "ihre", "ihrem", "ihren", "ihrer", "im", "in", "ist", "ja", "kann", "kein", "keine",
    "konnte", "lassen", "man", "mehr", "mit", "mir", "muss", "musste", "nach", "nicht", "noch",
    "nur", "oder", "ohne", "schon", "sehr", "sein", "seine", "seinem", "seinen", "seiner",
    "sich", "sie", "sind", "so", "soll", "sollte", "ueber", "um", "und", "vom", "von", "vor",
    "viel", "war", "waren", "was", "weil", "wenn", "wer", "wie", "wieder", "wird", "wir",
    "wobei", "wurde", "wurden", "zu", "zum", "zur", "zwischen",
}
_KURZINHALT = {"ass", "fiel", "gab", "ging", "kam", "lag", "rief", "sah"}
_META = {
    "angabe", "angaben", "beobachtbar", "beobachtung", "beobachtungen", "benannt",
    "beschreibt", "beschreibung", "beschrieben", "dokumentation", "dokumentiert",
    "ergaenzen", "ergaenzt", "fehlt", "fehlen", "fehlend", "fehlende", "formulierung",
    "formulierungen", "genauer", "hinweis", "hinweise", "knapp", "luecke", "luecken",
    "notieren", "notiert", "rechtschreibung", "grammatik", "satz", "saetze", "sprache",
    "steht", "stehen", "stimmung", "text", "texte", "wendung", "wendungen",
}
_LEXIKON_FORM = (
    "aufgefangen", "Bedürfnis", "Betreuer", "Bett", "Essen", "Fahrrad", "Frühstück",
    "gefrühstückt", "geschlafen", "herausgefunden", "Hort", "Kontakt", "konzentrieren",
    "genommen", "provozieren", "ruhig", "Tropfen", "unruhig", "verletzt",
)
_LEXIKON = {_norm(wort): wort for wort in _LEXIKON_FORM}


def _damerau(a: str, b: str) -> int:
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            kosten = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + kosten)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


def _stamm(wort: str) -> str:
    w = _norm(wort)
    if w.startswith("ge") and len(w) > 6:
        w = w[2:]
    for endung in ("ierungen", "ierung", "ieren", "iert", "ungen", "ende", "end", "ung", "ern", "en", "em", "er", "es", "et", "te", "st", "t", "e"):
        if len(w) - len(endung) >= 4 and w.endswith(endung):
            return w[: -len(endung)]
    return w


def _tokens(text: str) -> list[str]:
    rein = PLATZHALTER.sub(" ", text or "")
    return re.findall(r"[A-Za-zÄÖÜäöüß]+", rein)


def _inhalt(text: str, vorname: str | None = None) -> list[str]:
    name = _norm(vorname or "")
    woerter = []
    for token in _tokens(text):
        normal = _norm(token)
        if not normal or normal == name or normal in _STOPP or normal in _META:
            continue
        if len(normal) >= 4 or normal in _KURZINHALT:
            woerter.append(token)
    return woerter


def wort_belegt(wort: str, quelle: str) -> bool:
    ziel = _norm(wort)
    if not ziel:
        return False
    stamm = _stamm(wort)
    for token in _tokens(quelle):
        normal = _norm(token)
        if not normal:
            continue
        if ziel == normal or stamm == _stamm(token):
            return True
        kuerzer = min(len(ziel), len(normal))
        gemeinsam = 0
        while gemeinsam < kuerzer and ziel[gemeinsam] == normal[gemeinsam]:
            gemeinsam += 1
        if gemeinsam >= 5:
            return True
        if len(ziel) >= 6 and len(normal) >= 6 and _damerau(ziel, normal) <= 2:
            return True
    return False


def satz_hat_neuen_inhalt(satz: str, quelle: str, vorname: str | None = None) -> bool:
    woerter = _inhalt(satz, vorname)
    if not woerter:
        return False
    neu = [wort for wort in woerter if not wort_belegt(wort, quelle)]
    alt = [wort for wort in woerter if wort_belegt(wort, quelle)]
    return len(neu) >= 2 or (len(neu) >= 1 and not alt)


def fakten_gedeckt(text: str, quelle: str, vorname: str | None = None) -> bool:
    return all(wort_belegt(wort, text) for wort in _inhalt(quelle, vorname))


def hinweis_geerdet(hinweis: str, rohtext: str) -> bool:
    if re.search(r"\bwieder\b", hinweis or "", flags=re.IGNORECASE) and not re.search(
        r"\bwieder\b", rohtext or "", flags=re.IGNORECASE
    ):
        return False
    return all(wort_belegt(wort, rohtext) for wort in _inhalt(hinweis))


def _lexikon_form(token: str) -> str | None:
    normal = _norm(token)
    if normal in _LEXIKON:
        return _LEXIKON[normal]
    if len(normal) < 6:
        return None
    treffer = [form for key, form in _LEXIKON.items() if abs(len(key) - len(normal)) <= 2 and _damerau(normal, key) <= 2]
    if len(treffer) == 1:
        return treffer[0]
    return None


def korrigiere_minimal(text: str | None) -> str:
    if not text:
        return ""

    def ersetzen(fund: re.Match) -> str:
        form = _lexikon_form(fund.group(0))
        return form if form else fund.group(0)

    korrigiert = re.sub(r"[A-Za-zÄÖÜäöüß]+", ersetzen, text)
    korrigiert = re.sub(
        r"\bmir\b(?=\s+(?:seinem|seiner|seinen|ihrem|ihrer|ihren|einem)\b)",
        "mit",
        korrigiert,
        flags=re.IGNORECASE,
    )
    korrigiert = re.sub(r"\bdan\b", "dann", korrigiert, flags=re.IGNORECASE)
    return re.sub(r"[ \t]{2,}", " ", korrigiert).strip()


def fassung_erden(fassung: str | None, rohtext: str, vorname: str | None, medikamente_vorhanden: bool) -> str | None:
    quelle = rohtext or ""
    if not medikamente_vorhanden:
        quelle = ohne_medikationstext(quelle)
    if not (fassung or "").strip():
        return None
    behalten = []
    for satz in _saetze(fassung):
        if meldung_erlaubt(rohtext) and _MELDUNG.search(satz):
            behalten.append(satz)
            continue
        if satz_hat_neuen_inhalt(satz, quelle, vorname):
            continue
        behalten.append(satz)
    text = " ".join(behalten).strip()
    if not text or not fakten_gedeckt(text, quelle, vorname):
        text = korrigiere_minimal(quelle)
    return text.strip() or None


def _paare(wert) -> list[dict]:
    if isinstance(wert, dict):
        wert = [wert]
    if not isinstance(wert, list):
        return []
    paare = []
    for eintrag in wert:
        if isinstance(eintrag, dict):
            zitat = str(eintrag.get("zitat") or eintrag.get("original") or "").strip()
            vorschlag = str(eintrag.get("vorschlag") or eintrag.get("besser") or "").strip()
        elif isinstance(eintrag, str) and "→" in eintrag:
            zitat, vorschlag = [teil.strip() for teil in eintrag.split("→", 1)]
        else:
            continue
        if zitat and vorschlag:
            paare.append({"zitat": zitat[:300], "vorschlag": vorschlag[:500]})
    return paare


def paare_filtern(paare: list[dict], rohtext: str, medikamente_vorhanden: bool, vorname: str | None) -> list[dict]:
    behalten = []
    for paar in paare:
        zitat = paar["zitat"].strip()
        vorschlag = (namen_setzen(paar["vorschlag"], vorname) or "").strip()
        if len(_norm(zitat)) < 4 or not zitat_belegt(zitat, rohtext):
            continue
        if not medikamente_vorhanden and (enthaelt_medikation(zitat) or enthaelt_medikation(vorschlag)):
            continue
        if _MELDUNG.search(vorschlag) and not meldung_erlaubt(rohtext):
            continue
        if satz_hat_neuen_inhalt(vorschlag, rohtext, vorname):
            continue
        if not vorschlag:
            continue
        behalten.append({"zitat": zitat, "vorschlag": vorschlag})
    return behalten[:8]


def _fassung(wert) -> str | None:
    if not isinstance(wert, str):
        return None
    text = wert.strip()
    if not text:
        return None
    return text[:8000]


def _hinweise(wert) -> list[str]:
    if isinstance(wert, str) and wert.strip():
        return [wert.strip()]
    if isinstance(wert, list):
        return [str(eintrag).strip() for eintrag in wert if str(eintrag).strip()]
    return []


def _formatiere(ampel: str, hinweise: list[str], begruendung: str, paare: list[dict] | None = None) -> str:
    zeilen = [f"Ampel: {AMPEL_LABEL[ampel]}"]
    if begruendung:
        zeilen.append(begruendung)
    if paare:
        zeilen.append("Formulierungen:")
        zeilen.extend(f"- „{paar['zitat']}“ → {paar['vorschlag']}" for paar in paare)
    if hinweise:
        zeilen.append("Hinweise:")
        zeilen.extend(f"- {hinweis}" for hinweis in hinweise)
    return "\n".join(zeilen)


def _ohne_ampel(text: str) -> PruefErgebnis:
    return PruefErgebnis(ampel=None, text=text)


def parse_pruef_antwort(
    roh: str,
    rohtext: str = "",
    vorname: str | None = None,
    medikamente_vorhanden: bool = True,
) -> PruefErgebnis:
    daten = _json_objekt(roh)
    if not isinstance(daten, dict):
        return _ohne_ampel(
            "Die Prüfung hat kein lesbares Ergebnis geliefert. Es wurde keine Ampel gesetzt."
        )
    ampel = _ampel_aus_wert(daten.get("ampel"))
    hinweise = [
        namen_setzen(hinweis, vorname) or hinweis
        for hinweis in hinweise_filtern(_hinweise(daten.get("hinweise")), rohtext)
        if hinweis_behaltbar(hinweis, rohtext, medikamente_vorhanden)
    ][:3]
    begruendung = daten.get("kurzbegruendung") or daten.get("begruendung") or ""
    if not isinstance(begruendung, str):
        begruendung = str(begruendung)
    begruendung = namen_setzen(begruendung_filtern(begruendung, rohtext), vorname) or ""
    if not medikamente_vorhanden:
        begruendung = ohne_medikationstext(begruendung)
    begruendung = ohne_uebergriff(begruendung, rohtext)
    fassung = _fassung(
        daten.get("verbesserte_fassung")
        or daten.get("verbesserteFassung")
        or daten.get("fassung")
    )
    if fassung:
        if not medikamente_vorhanden:
            fassung = ohne_medikationstext(fassung)
        fassung = ohne_uebergriff(fassung, rohtext)
        fassung = (namen_setzen(fassung, vorname) or "").strip() or None
        fassung = fassung_erden(fassung, rohtext, vorname, medikamente_vorhanden)
    paare = paare_filtern(
        _paare(daten.get("umformulierungen") or daten.get("paare")),
        rohtext,
        medikamente_vorhanden,
        vorname,
    )
    if ampel is None:
        teile = ["Die Prüfung enthält keine gültige Ampel. Es wurde keine Ampel gesetzt."]
        if begruendung:
            teile.append(begruendung)
        if hinweise:
            teile.append("Hinweise:")
            teile.extend(f"- {hinweis}" for hinweis in hinweise)
        return _ohne_ampel("\n".join(teile))
    return PruefErgebnis(
        ampel=ampel,
        text=_formatiere(ampel, hinweise, begruendung, paare),
        hinweise=hinweise,
        verbesserte_fassung=fassung,
        kurzbegruendung=begruendung or None,
        umformulierungen=paare,
    )


def _nicht_moeglich(grund: str) -> PruefErgebnis:
    return _ohne_ampel(f"Prüfung nicht möglich: {grund}. Es wurde keine Ampel gesetzt.")


async def pruefe_bericht(
    profil: str,
    medikation: str,
    rohtext: str,
    schicht: str | None = None,
    vorname: str | None = None,
    medikamente_vorhanden: bool = True,
    anrede: str | None = None,
) -> PruefErgebnis:
    try:
        system, prompt = baue_prompt(profil, medikation, rohtext, schicht, anrede)
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
        "options": {"temperature": 0, "top_p": 0.1},
    }
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
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
    return parse_pruef_antwort(
        inhalt,
        rohtext,
        vorname=vorname,
        medikamente_vorhanden=medikamente_vorhanden,
    )
