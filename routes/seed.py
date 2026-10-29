import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, utc_now
from models import (
    Ampel,
    BerichtStatus,
    BerichtVersion,
    Kind,
    Kontakt,
    KontaktTyp,
    Medikament,
    Schicht,
    Tagesbericht,
)

router = APIRouter(prefix="/seed", tags=["seed"])

KUERZEL = ("AK", "MS", "LS", "BH", "AB", "EST")

_STUNDE = {"frueh": 7, "mittel": 13, "spaet": 18, "nacht": 22}


class SeedErgebnis(BaseModel):
    kinder_neu: int
    kinder_vorhanden: int
    berichte_neu: int
    kuerzel: list[str]


class SeedAus(BaseModel):
    ausgeblendet: int
    kuerzel: list[str]


def _wrap_text(ampel: str, begruendung: str, paare: list[dict], hinweise: list[str]) -> str:
    label = {"gruen": "Grün", "gelb": "Gelb", "rot": "Rot"}[ampel]
    zeilen = [f"Ampel: {label}"]
    if begruendung:
        zeilen.append(begruendung)
    if paare:
        zeilen.append("Formulierungen:")
        zeilen.extend(f"- „{paar['zitat']}“ → {paar['vorschlag']}" for paar in paare)
    if hinweise:
        zeilen.append("Hinweise:")
        zeilen.extend(f"- {hinweis}" for hinweis in hinweise)
    return "\n".join(zeilen)


def _paket(ampel: str, begruendung: str, hinweise: list[str], fassung: str, paare: list[dict] | None = None) -> dict:
    paare = paare or []
    return {
        "ampel": Ampel(ampel),
        "wrap": _wrap_text(ampel, begruendung, paare, hinweise),
        "fassung": fassung,
        "meta": json.dumps(
            {
                "hinweise": hinweise,
                "kurzbegruendung": begruendung,
                "umformulierungen": paare,
                "quelle": "beispiel",
            },
            ensure_ascii=False,
        ),
    }


def _profile() -> list[dict]:
    return [
        {
            "vorname": "AK",
            "paragraph": "§ 34 SGB VIII",
            "besonderheiten": "Braucht nach dem Mittagessen eine ruhige Ecke. Pronomen: sie.",
            "dokumentationshinweise": "Essen, Schlaf und den Weg zur Schule kurz und beobachtbar notieren.",
            "kontakt": {
                "typ": KontaktTyp.eltern,
                "name": "Sorgeberechtigte (Beispiel)",
                "telefon": "0000",
                "hinweis": "Platzhalter für die Verwaltung, keine echte Person.",
            },
        },
        {
            "vorname": "MS",
            "paragraph": "§ 34 SGB VIII",
            "besonderheiten": "Reagiert empfindlich auf laute Gruppen. Pronomen: er.",
            "dokumentationshinweise": "Abendmedikation nur notieren, wenn sie in dieser Schicht gegeben oder ausgelassen wurde.",
            "medikament": {
                "name": "Platzhalter-Saft",
                "dosierung": "5 ml",
                "einnahmezeit": "abends",
                "hinweis": "Beispiel für die Prüfung. Kein echtes Präparat.",
            },
        },
        {
            "vorname": "LS",
            "paragraph": "§ 34 SGB VIII",
            "besonderheiten": "Geht nach der Schule in den Gruppenraum. Pronomen: sie.",
            "dokumentationshinweise": "Schulweg nur schreiben, wenn er an diesem Tag stattgefunden hat.",
            "kontakt": {
                "typ": KontaktTyp.asd,
                "name": "Jugendamt (Beispiel)",
                "telefon": "0000",
                "hinweis": "Platzhalter, keine echte Dienststelle.",
            },
        },
        {
            "vorname": "BH",
            "paragraph": "§ 34 SGB VIII",
            "besonderheiten": "Macht Hausaufgaben lieber am Tisch am Fenster. Pronomen: er.",
            "dokumentationshinweise": "Essen und Hausaufgaben beobachtbar beschreiben.",
        },
        {
            "vorname": "AB",
            "paragraph": "§ 34 SGB VIII",
            "besonderheiten": "Spielt nach dem Essen gern draußen. Pronomen: sie.",
            "dokumentationshinweise": "Frühstück und Mittagessen getrennt notieren.",
        },
        {
            "vorname": "EST",
            "paragraph": "§ 34 SGB VIII",
            "besonderheiten": "Hört abends eine Geschichte. Pronomen: er.",
            "dokumentationshinweise": "Zubettgehzeit notieren.",
        },
    ]


def _berichte(kuerzel: str, heute: date, zweittag: date) -> list[dict]:
    if kuerzel == "AK":
        frueh = (
            "AK ist um 7:10 aufgestanden und hat eine Schale Haferbrei gegessen. "
            "Danach hat AK die Jacke angezogen. Die Fachkraft hat AK um 7:55 zum Schulweg an die Tür gebracht. "
            "AK ist ruhig losgegangen."
        )
        return [
            {
                "tag": heute,
                "schicht": "frueh",
                "rohtext": frueh,
                "status": "freigegeben",
                "pruefung": _paket(
                    "gruen",
                    "Der Text ist beobachtbar und für die Akte ausreichend.",
                    ["Aufstehen, Frühstück und der Schulweg sind mit Uhrzeit notiert."],
                    frueh,
                ),
            },
            {
                "tag": heute,
                "schicht": "mittel",
                "rohtext": (
                    "AK kam um 13:20 aus der Schule zurück, hat Nudeln gegessen und danach in der ruhigen Ecke gemalt. "
                    "Um 15:00 ist AK in den Gruppenraum gegangen."
                ),
                "status": "entwurf",
            },
            {
                "tag": zweittag,
                "schicht": "frueh",
                "rohtext": "AK hat um 7:20 gefrühstückt und ist danach zur Schule gegangen. Besondere Vorkommnisse gab es nicht.",
                "status": "freigegeben",
                "pruefung": _paket(
                    "gruen",
                    "Frühstück und Schulweg sind knapp, aber nachvollziehbar dokumentiert.",
                    ["Frühstück und der Weg zur Schule stehen im Text."],
                    "AK hat um 7:20 gefrühstückt und ist danach zur Schule gegangen. Besondere Vorkommnisse gab es nicht.",
                ),
            },
        ]
    if kuerzel == "MS":
        roh = (
            "MS war beim Abendbrot total anstrengend und hat kaum etwas gegessen. "
            "Der Platzhalter-Saft wurde um 19:00 gegeben. Danach hat MS ferngesehen."
        )
        return [
            {
                "tag": heute,
                "schicht": "spaet",
                "rohtext": roh,
                "status": "entwurf",
                "pruefung": _paket(
                    "gelb",
                    "Der Spätdienst ist brauchbar, zwei Formulierungen sind noch nicht beobachtbar.",
                    [
                        "Die Wendung „total anstrengend“ steht wertend im Text.",
                        "„Kaum etwas“ lässt die Menge des Essens unscharf.",
                    ],
                    (
                        "MS war beim Abendbrot [Bitte ergänzen: was genau beobachtbar war] und hat kaum etwas gegessen. "
                        "Der Platzhalter-Saft wurde um 19:00 gegeben. Danach hat MS ferngesehen."
                    ),
                    [{"zitat": "total anstrengend", "vorschlag": "MS war beim Abendbrot [Bitte ergänzen: was genau beobachtbar war]"}],
                ),
            }
        ]
    if kuerzel == "LS":
        roh = (
            "LS ist nach dem Frühstück ohne Absprache vom Gelände gegangen und nach etwa zwanzig Minuten zurückgekommen. "
            "LS wirkte cool und hat nicht gesagt, wo LS war."
        )
        return [
            {
                "tag": heute,
                "schicht": "frueh",
                "rohtext": roh,
                "status": "entwurf",
                "pruefung": _paket(
                    "rot",
                    "Ein melderelevantes Vorkommnis steht im Text, die Mitteilung fehlt. Eine Wendung ist wertend.",
                    [
                        "Das Verlassen des Geländes ist beschrieben. Eine Mitteilung an Jugendamt oder Sorgeberechtigte steht nicht im Text.",
                        "„Cool“ bewertet den Eindruck und beschreibt nicht, was LS getan hat.",
                    ],
                    (
                        "LS ist nach dem Frühstück ohne Absprache vom Gelände gegangen und nach etwa zwanzig Minuten zurückgekommen. "
                        "LS hat nicht gesagt, wo LS war. [Bitte ergänzen: ob jemand informiert wurde.]"
                    ),
                    [{"zitat": "wirkte cool", "vorschlag": "LS hat wenig gesagt"}],
                ),
            }
        ]
    if kuerzel == "BH":
        roh = "BH hat mittags wenig gegessen und war danach irgendwie durch den Wind. Die Hausaufgaben hat BH angefangen."
        return [
            {
                "tag": zweittag,
                "schicht": "mittel",
                "rohtext": roh,
                "status": "entwurf",
                "pruefung": _paket(
                    "gelb",
                    "Essen und Hausaufgaben stehen im Text, eine Wendung bleibt unscharf.",
                    ["„Durch den Wind“ beschreibt noch nicht, was BH getan oder gelassen hat."],
                    "BH hat mittags wenig gegessen und war danach [Bitte ergänzen: was genau beobachtbar war]. Die Hausaufgaben hat BH angefangen.",
                    [{"zitat": "irgendwie durch den Wind", "vorschlag": "BH war danach [Bitte ergänzen: was genau beobachtbar war]"}],
                ),
            }
        ]
    if kuerzel == "AB":
        mittel = (
            "AB hat beim Mittagessen den Teller weggeschoben und gesagt, die Nudeln seien eklig. "
            "Danach war AB ganz okay und hat im Garten mit einem Ball gespielt."
        )
        return [
            {
                "tag": heute,
                "schicht": "frueh",
                "rohtext": "AB hat die anderen ständig genervt und wollte nur Aufmerksamkeit. Das Frühstück verlief eher nicht so gut.",
                "status": "entwurf",
            },
            {
                "tag": heute,
                "schicht": "mittel",
                "rohtext": mittel,
                "status": "entwurf",
                "pruefung": _paket(
                    "gelb",
                    "Der Mitteldienst ist weitgehend beobachtbar, eine Wendung bleibt vage.",
                    ["„Ganz okay“ beschreibt nicht, was nach dem Essen zu sehen war."],
                    (
                        "AB hat beim Mittagessen den Teller weggeschoben und gesagt, die Nudeln seien eklig. "
                        "Danach hat AB im Garten mit einem Ball gespielt."
                    ),
                    [{"zitat": "ganz okay", "vorschlag": "AB hat im Garten mit einem Ball gespielt"}],
                ),
            },
        ]
    if kuerzel == "EST":
        aktuell = (
            "EST hat um 18:30 Brot mit Käse gegessen und ist um 20:10 ins Bett gegangen. "
            "Vorher hat EST eine Geschichte gehört und lag danach still."
        )
        return [
            {
                "tag": heute,
                "schicht": "spaet",
                "rohtext": aktuell,
                "status": "freigegeben",
                "pruefung": _paket(
                    "gruen",
                    "Der Spätdienst ist sachlich und nachvollziehbar.",
                    ["Essen, Geschichte und die Zubettgehzeit sind notiert."],
                    aktuell,
                ),
                "verlauf": {
                    "rohtext": "EST hat genervt rumgezickt beim Abendbrot und wollte nicht ins Bett.",
                    "pruefung": _paket(
                        "gelb",
                        "Der Text bewertet, ohne den Ablauf zu beschreiben.",
                        ["„Rumgezickt“ ist abwertend und nicht beobachtbar formuliert."],
                        "EST hat beim Abendbrot [Bitte ergänzen: was genau zu sehen war] und wollte nicht ins Bett.",
                        [{"zitat": "genervt rumgezickt", "vorschlag": "EST hat beim Abendbrot [Bitte ergänzen: was genau zu sehen war]"}],
                    ),
                },
            }
        ]
    return []


def _bericht_anlegen(db: Session, kind_id: int, spec: dict) -> Tagesbericht:
    schicht = spec["schicht"]
    bericht = Tagesbericht(
        kind_id=kind_id,
        datum=datetime.combine(spec["tag"], time(_STUNDE[schicht], 0)),
        schicht=Schicht(schicht),
        rohtext=spec["rohtext"],
        status=BerichtStatus(spec["status"]),
        erstellt_von="Pilot",
    )
    pruefung = spec.get("pruefung")
    if pruefung:
        bericht.ampel = pruefung["ampel"]
        bericht.wrap_ergebnis = pruefung["wrap"]
        bericht.verbesserte_fassung = pruefung["fassung"]
        bericht.pruef_meta = pruefung["meta"]
    if spec["status"] == "freigegeben":
        bericht.freigegeben_am = utc_now()
        bericht.freigegeben_von = "Pilot"
    db.add(bericht)
    db.flush()
    verlauf = spec.get("verlauf")
    if verlauf:
        alt = verlauf["pruefung"]
        db.add(
            BerichtVersion(
                bericht_id=bericht.id,
                rohtext=verlauf["rohtext"],
                schicht=Schicht(schicht),
                ampel=alt["ampel"],
                wrap_ergebnis=alt["wrap"],
                verbesserte_fassung=alt["fassung"],
                pruef_meta=alt["meta"],
                freigegeben_am=utc_now(),
                freigegeben_von="Pilot",
                geaendert_von="Pilot",
                archiviert_am=utc_now(),
            )
        )
    return bericht


def lege_pilot_an(db: Session, heute: date | None = None) -> SeedErgebnis:
    """Legt fehlende Pilotkürzel und Beispielberichte an. Vorhandene Berichte bleiben."""
    heute = heute or date.today()
    montag = heute - timedelta(days=heute.weekday())
    zweittag = montag if montag != heute else heute + timedelta(days=1)
    kinder_neu = 0
    kinder_vorhanden = 0
    berichte_neu = 0

    for profil in _profile():
        kind = db.query(Kind).filter(Kind.vorname == profil["vorname"]).first()
        if kind is None:
            kind = Kind(
                vorname=profil["vorname"],
                paragraph=profil["paragraph"],
                besonderheiten=profil["besonderheiten"],
                dokumentationshinweise=profil["dokumentationshinweise"],
            )
            db.add(kind)
            db.flush()
            kinder_neu += 1
        else:
            kinder_vorhanden += 1
            if not kind.aktiv:
                kind.aktiv = True
        if db.query(Tagesbericht).filter(Tagesbericht.kind_id == kind.id).first() is not None:
            continue
        med = profil.get("medikament")
        if med is not None:
            schon = (
                db.query(Medikament)
                .filter(Medikament.kind_id == kind.id, Medikament.name == med["name"])
                .first()
            )
            if schon is None:
                db.add(Medikament(kind_id=kind.id, **med))
        kontakt = profil.get("kontakt")
        if kontakt is not None:
            schon = (
                db.query(Kontakt)
                .filter(Kontakt.kind_id == kind.id, Kontakt.name == kontakt["name"])
                .first()
            )
            if schon is None:
                db.add(Kontakt(kind_id=kind.id, **kontakt))
        for spec in _berichte(profil["vorname"], heute, zweittag):
            _bericht_anlegen(db, kind.id, spec)
            berichte_neu += 1

    return SeedErgebnis(
        kinder_neu=kinder_neu,
        kinder_vorhanden=kinder_vorhanden,
        berichte_neu=berichte_neu,
        kuerzel=list(KUERZEL),
    )


@router.post("/pilot", response_model=SeedErgebnis)
def pilot_laden(db: Session = Depends(get_db)):
    ergebnis = lege_pilot_an(db)
    db.commit()
    return ergebnis


@router.post("/pilot/aus", response_model=SeedAus)
def pilot_ausblenden(db: Session = Depends(get_db)):
    """Blendet nur die Demo-Kürzel aus. Berichte bleiben in der lokalen Datei."""
    ausgeblendet = 0
    for name in KUERZEL:
        kind = db.query(Kind).filter(Kind.vorname == name, Kind.aktiv == True).first()  # noqa: E712
        if kind is None:
            continue
        kind.aktiv = False
        ausgeblendet += 1
    db.commit()
    return SeedAus(ausgeblendet=ausgeblendet, kuerzel=list(KUERZEL))
