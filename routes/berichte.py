from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, date, time, timedelta, timezone
from database import get_db, utc_now
from models import Tagesbericht, Kind, Medikament, BerichtStatus, Ampel, Schicht
from wrap import pruefe_bericht, kind_profiltext, medikamente_text

router = APIRouter(prefix="/tagesberichte", tags=["berichte"])


class BerichtCreate(BaseModel):
    kind_id: int
    datum: datetime
    rohtext: str = Field(min_length=1)
    schicht: Optional[Schicht] = None


class BerichtUpdate(BaseModel):
    rohtext: Optional[str] = None
    schicht: Optional[Schicht] = None


class BerichtOut(BaseModel):
    id: int
    kind_id: int
    datum: datetime
    schicht: Optional[Schicht]
    rohtext: str
    wrap_ergebnis: Optional[str]
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
    eintraege: List[WochenEintrag]


class WochenKind(BaseModel):
    id: int
    vorname: str
    nachname: Optional[str]
    tage: List[WochenTag]


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
                    key=lambda paar: (paar[0] is None, paar[0] or ""),
                )
            ]
            tag_liste.append(WochenTag(datum=tag, eintraege=eintraege))
        antwort.append(
            WochenKind(
                id=kind.id,
                vorname=kind.vorname,
                nachname=kind.nachname,
                tage=tag_liste,
            )
        )
    return WochenUebersicht(von=von, bis=bis, kinder=antwort)


@router.get("/{bericht_id}", response_model=BerichtOut)
def bericht_anzeigen(bericht_id: int, db: Session = Depends(get_db)):
    return _bericht_oder_404(db, bericht_id)


@router.put("/{bericht_id}", response_model=BerichtOut)
def bericht_aendern(bericht_id: int, daten: BerichtUpdate, db: Session = Depends(get_db)):
    bericht = _bericht_oder_404(db, bericht_id)
    if bericht.status == BerichtStatus.freigegeben:
        raise HTTPException(status_code=409, detail="Freigegebene Berichte können nicht geändert werden.")
    geaendert = daten.model_dump(exclude_unset=True)
    if "rohtext" in geaendert:
        rohtext = (geaendert["rohtext"] or "").strip()
        if not rohtext:
            raise HTTPException(status_code=400, detail="Berichtstext fehlt")
        if rohtext != bericht.rohtext:
            bericht.rohtext = rohtext
            bericht.wrap_ergebnis = None
            bericht.ampel = None
    if "schicht" in geaendert and geaendert["schicht"] != bericht.schicht:
        bericht.schicht = geaendert["schicht"]
        bericht.wrap_ergebnis = None
        bericht.ampel = None
    db.commit()
    db.refresh(bericht)
    return bericht


@router.post("/{bericht_id}/pruefen", response_model=BerichtOut)
async def bericht_pruefen(bericht_id: int, db: Session = Depends(get_db)):
    bericht = _bericht_oder_404(db, bericht_id)
    if bericht.status == BerichtStatus.freigegeben:
        raise HTTPException(status_code=409, detail="Freigegebene Berichte können nicht geändert werden.")
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
    ergebnis = await pruefe_bericht(
        profil,
        medikamente_text(medikamente),
        bericht.rohtext,
        bericht.schicht.value if bericht.schicht else None,
    )
    bericht.wrap_ergebnis = ergebnis.text
    bericht.ampel = Ampel(ergebnis.ampel) if ergebnis.ampel else None
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
