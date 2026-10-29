import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, date, time, timedelta, timezone
from database import get_db, utc_now
from models import Tagesbericht, BerichtVersion, Kind, Medikament, BerichtStatus, Ampel, Schicht, SCHICHT_REIHENFOLGE
from wrap import anrede_anweisung, pruefe_bericht, kind_profiltext, medikamente_text

router = APIRouter(prefix="/tagesberichte", tags=["berichte"])


class BerichtCreate(BaseModel):
    kind_id: int
    datum: datetime
    rohtext: str = Field(min_length=1)
    schicht: Optional[Schicht] = None


class BerichtUpdate(BaseModel):
    rohtext: Optional[str] = None
    schicht: Optional[Schicht] = None
    von: Optional[str] = None


class UmformulierungOut(BaseModel):
    zitat: str
    vorschlag: str


class BerichtOut(BaseModel):
    id: int
    kind_id: int
    datum: datetime
    schicht: Optional[Schicht]
    rohtext: str
    wrap_ergebnis: Optional[str]
    verbesserte_fassung: Optional[str] = None
    hinweise: List[str] = []
    umformulierungen: List[UmformulierungOut] = []
    kurzbegruendung: Optional[str] = None
    ampel: Optional[Ampel]
    status: BerichtStatus
    erstellt_von: Optional[str]
    freigegeben_von: Optional[str]
    erstellt_am: datetime
    freigegeben_am: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class WochenEintrag(BaseModel):
    bericht_id: int
    ampel: Optional[Ampel]
    status: BerichtStatus
    schicht: Optional[Schicht]


class WochenTag(BaseModel):
    datum: date
    ampel: Optional[Ampel] = None
    hinweis: Optional[str] = None
    eintraege: List[WochenEintrag]


class WochenKind(BaseModel):
    id: int
    vorname: str
    nachname: Optional[str]
    paragraph: Optional[str] = None
    tage: List[WochenTag]


class VersionOut(BaseModel):
    id: int
    bericht_id: int
    rohtext: str
    schicht: Optional[Schicht]
    ampel: Optional[Ampel]
    wrap_ergebnis: Optional[str]
    freigegeben_am: Optional[datetime]
    freigegeben_von: Optional[str]
    geaendert_von: Optional[str]
    archiviert_am: datetime
    model_config = ConfigDict(from_attributes=True)


class WochenUebersicht(BaseModel):
    von: date
    bis: date
    kinder: List[WochenKind]


def _als_naiv(wert: datetime) -> datetime:
    if wert.tzinfo is not None:
        return wert.astimezone(timezone.utc).replace(tzinfo=None)
    return wert


def _bericht_oder_404(db: Session, bericht_id: int) -> Tagesbericht:
    bericht = db.query(Tagesbericht).filter(Tagesbericht.id == bericht_id).first()
    if not bericht:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
    return bericht


AMPEL_RANG = {Ampel.gruen: 1, Ampel.gelb: 2, Ampel.rot: 3}
SCHICHT_KURZ = (
    ("frueh", "Früh"),
    ("mittel", "Mittel"),
    ("spaet", "Spät"),
    ("nacht", "Nacht"),
)


def _schichtwert(schicht) -> Optional[str]:
    if schicht is None:
        return None
    return schicht.value if hasattr(schicht, "value") else schicht


def schlechteste_ampel(eintraege) -> Optional[Ampel]:
    gewinner = None
    for eintrag in eintraege:
        if eintrag.ampel is None:
            continue
        if gewinner is None or AMPEL_RANG[eintrag.ampel] > AMPEL_RANG[gewinner]:
            gewinner = eintrag.ampel
    return gewinner


def _aufzaehlung(namen: List[str]) -> str:
    if len(namen) == 1:
        return namen[0]
    if len(namen) == 2:
        return f"{namen[0]} und {namen[1]}"
    return ", ".join(namen[:-1]) + " und " + namen[-1]


def tageshinweis(eintraege) -> Optional[str]:
    """Kurzer Hinweis, wenn Schichten fehlen oder noch keine Ampel haben."""
    if not eintraege:
        return None
    if not any(_schichtwert(eintrag.schicht) for eintrag in eintraege):
        return "ungeprüft" if any(eintrag.ampel is None for eintrag in eintraege) else None
    fehlt = []
    ungeprueft = []
    for schluessel, kurz in SCHICHT_KURZ:
        treffer = next((eintrag for eintrag in eintraege if _schichtwert(eintrag.schicht) == schluessel), None)
        if treffer is None:
            fehlt.append(kurz)
        elif treffer.ampel is None:
            ungeprueft.append(kurz)
    stuecke = []
    if fehlt:
        stuecke.append(_aufzaehlung(fehlt) + (" fehlt" if len(fehlt) == 1 else " fehlen"))
    if ungeprueft:
        stuecke.append(_aufzaehlung(ungeprueft) + " ungeprüft")
    return " · ".join(stuecke) or None


def _datum_von(bericht: Tagesbericht) -> date:
    wert = bericht.datum
    if isinstance(wert, datetime):
        return wert.date()
    return wert


@router.post("/", response_model=BerichtOut)
def bericht_anlegen(bericht: BerichtCreate, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == bericht.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    rohtext = bericht.rohtext.strip()
    if not rohtext:
        raise HTTPException(status_code=400, detail="Berichtstext fehlt")
    neuer_bericht = Tagesbericht(
        kind_id=bericht.kind_id,
        datum=_als_naiv(bericht.datum),
        schicht=bericht.schicht,
        rohtext=rohtext,
        status=BerichtStatus.entwurf,
    )
    db.add(neuer_bericht)
    db.commit()
    db.refresh(neuer_bericht)
    return neuer_bericht


@router.get("/kind/{kind_id}", response_model=List[BerichtOut])
def berichte_eines_kindes(kind_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Tagesbericht)
        .filter(Tagesbericht.kind_id == kind_id)
        .order_by(Tagesbericht.datum.desc(), Tagesbericht.id.desc())
        .all()
    )


@router.get("/woche", response_model=WochenUebersicht)
def wochenuebersicht(von: Optional[date] = None, db: Session = Depends(get_db)):
    if von is None:
        heute = date.today()
        von = heute - timedelta(days=heute.weekday())
    bis = von + timedelta(days=6)
    tage = [von + timedelta(days=versatz) for versatz in range(7)]
    start = datetime.combine(von, time.min)
    ende = datetime.combine(bis, time.max)

    kinder = db.query(Kind).filter(Kind.aktiv == True).all()  # noqa: E712
    kinder.sort(key=lambda kind: ((kind.vorname or "").lower(), kind.id))
    berichte = (
        db.query(Tagesbericht)
        .filter(Tagesbericht.datum >= start, Tagesbericht.datum <= ende)
        .all()
    )

    je_kind = {}
    for bericht in berichte:
        je_kind.setdefault(bericht.kind_id, {}).setdefault(_datum_von(bericht), []).append(bericht)

    antwort = []
    for kind in kinder:
        tag_liste = []
        for tag in tage:
            kandidaten = je_kind.get(kind.id, {}).get(tag, [])
            gewaehlt = {}
            for bericht in kandidaten:
                schluessel = bericht.schicht.value if bericht.schicht else None
                bisher = gewaehlt.get(schluessel)
                if bisher is None or bericht.id > bisher.id:
                    gewaehlt[schluessel] = bericht
            eintraege = [
                WochenEintrag(
                    bericht_id=bericht.id,
                    ampel=bericht.ampel,
                    status=bericht.status,
                    schicht=bericht.schicht,
                )
                for _, bericht in sorted(
                    gewaehlt.items(),
                    key=lambda paar: SCHICHT_REIHENFOLGE.get(paar[0], 99),
                )
            ]
            tag_liste.append(WochenTag(
                datum=tag,
                ampel=schlechteste_ampel(eintraege),
                hinweis=tageshinweis(eintraege),
                eintraege=eintraege,
            ))
        antwort.append(
            WochenKind(
                id=kind.id,
                vorname=kind.vorname,
                nachname=kind.nachname,
                paragraph=kind.paragraph,
                tage=tag_liste,
            )
        )
    return WochenUebersicht(von=von, bis=bis, kinder=antwort)


@router.get("/{bericht_id}", response_model=BerichtOut)
def bericht_anzeigen(bericht_id: int, db: Session = Depends(get_db)):
    return _bericht_oder_404(db, bericht_id)


def _name(wert) -> Optional[str]:
    if wert is None:
        return None
    text = str(wert).strip()
    return text[:80] or None


def _fassung_archivieren(db: Session, bericht: Tagesbericht, geaendert_von: Optional[str]):
    db.add(BerichtVersion(
        bericht_id=bericht.id,
        rohtext=bericht.rohtext,
        schicht=bericht.schicht,
        ampel=bericht.ampel,
        wrap_ergebnis=bericht.wrap_ergebnis,
        verbesserte_fassung=bericht.verbesserte_fassung,
        pruef_meta=bericht.pruef_meta,
        freigegeben_am=bericht.freigegeben_am,
        freigegeben_von=bericht.freigegeben_von,
        geaendert_von=geaendert_von,
        archiviert_am=utc_now(),
    ))


@router.get("/{bericht_id}/versionen", response_model=List[VersionOut])
def berichtsversionen(bericht_id: int, db: Session = Depends(get_db)):
    _bericht_oder_404(db, bericht_id)
    return (
        db.query(BerichtVersion)
        .filter(BerichtVersion.bericht_id == bericht_id)
        .order_by(BerichtVersion.archiviert_am.desc(), BerichtVersion.id.desc())
        .all()
    )


@router.put("/{bericht_id}", response_model=BerichtOut)
def bericht_aendern(bericht_id: int, daten: BerichtUpdate, db: Session = Depends(get_db)):
    bericht = _bericht_oder_404(db, bericht_id)
    geaendert = daten.model_dump(exclude_unset=True)
    neuer_text = None
    if "rohtext" in geaendert:
        neuer_text = (geaendert["rohtext"] or "").strip()
        if not neuer_text:
            raise HTTPException(status_code=400, detail="Berichtstext fehlt")
    text_aendert = neuer_text is not None and neuer_text != bericht.rohtext
    schicht_aendert = "schicht" in geaendert and geaendert["schicht"] != bericht.schicht
    if not text_aendert and not schicht_aendert:
        return bericht
    if bericht.status == BerichtStatus.freigegeben:
        _fassung_archivieren(db, bericht, _name(geaendert.get("von")))
        bericht.status = BerichtStatus.entwurf
        bericht.freigegeben_am = None
        bericht.freigegeben_von = None
    bericht.ampel = None
    bericht.wrap_ergebnis = None
    bericht.verbesserte_fassung = None
    bericht.pruef_meta = None
    if text_aendert:
        bericht.rohtext = neuer_text
    if schicht_aendert:
        bericht.schicht = geaendert["schicht"]
    db.commit()
    db.refresh(bericht)
    return bericht


@router.post("/{bericht_id}/pruefen", response_model=BerichtOut)
async def bericht_pruefen(bericht_id: int, db: Session = Depends(get_db)):
    bericht = _bericht_oder_404(db, bericht_id)
    if bericht.status == BerichtStatus.freigegeben:
        raise HTTPException(
            status_code=409,
            detail="Freigegebene Berichte werden nicht erneut geprüft. Bitte zuerst einen Nachtrag speichern.",
        )
    kind = db.query(Kind).filter(Kind.id == bericht.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    medikamente = (
        db.query(Medikament)
        .filter(Medikament.kind_id == kind.id, Medikament.aktiv == True)  # noqa: E712
        .order_by(Medikament.name)
        .all()
    )
    profil = kind_profiltext(
        kind.vorname,
        kind.nachname,
        kind.besonderheiten,
        kind.dokumentationshinweise,
    )
    schicht = bericht.schicht.value if bericht.schicht else None
    ergebnis = await pruefe_bericht(
        profil,
        medikamente_text(medikamente, schicht),
        bericht.rohtext,
        schicht,
        vorname=kind.vorname,
        medikamente_vorhanden=bool(medikamente),
        anrede=anrede_anweisung(kind.vorname, kind.besonderheiten, kind.dokumentationshinweise),
    )
    bericht.wrap_ergebnis = ergebnis.text
    bericht.ampel = Ampel(ergebnis.ampel) if ergebnis.ampel else None
    if ergebnis.ampel:
        bericht.verbesserte_fassung = ergebnis.verbesserte_fassung
        bericht.pruef_meta = json.dumps(
            {
                "hinweise": ergebnis.hinweise,
                "kurzbegruendung": ergebnis.kurzbegruendung or "",
                "umformulierungen": ergebnis.umformulierungen,
            },
            ensure_ascii=False,
        )
    else:
        bericht.verbesserte_fassung = None
        bericht.pruef_meta = None
    db.commit()
    db.refresh(bericht)
    return bericht


@router.post("/{bericht_id}/freigeben", response_model=BerichtOut)
def bericht_freigeben(bericht_id: int, db: Session = Depends(get_db)):
    bericht = _bericht_oder_404(db, bericht_id)
    bericht.status = BerichtStatus.freigegeben
    bericht.freigegeben_am = utc_now()
    db.commit()
    db.refresh(bericht)
    return bericht
