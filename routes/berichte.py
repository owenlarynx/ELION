from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db
from models import Tagesbericht, Kind, BerichtStatus, Ampel
from wrap import pruefe_bericht

router = APIRouter(prefix="/tagesberichte", tags=["berichte"])

class BerichtCreate(BaseModel):
    kind_id: int
    datum: datetime
    rohtext: str

class BerichtOut(BaseModel):
    id: int
    kind_id: int
    datum: datetime
    rohtext: str
    wrap_ergebnis: Optional[str]
    ampel: Optional[Ampel]
    status: BerichtStatus
    erstellt_von: Optional[str]
    freigegeben_von: Optional[str]
    erstellt_am: datetime
    freigegeben_am: Optional[datetime]

    class Config:
        from_attributes = True

@router.post("/", response_model=BerichtOut)
def bericht_anlegen(bericht: BerichtCreate, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == bericht.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    neuer_bericht = Tagesbericht(
        kind_id=bericht.kind_id,
        datum=bericht.datum,
        rohtext=bericht.rohtext,
        status=BerichtStatus.entwurf
    )
    db.add(neuer_bericht)
    db.commit()
    db.refresh(neuer_bericht)
    return neuer_bericht

@router.get("/kind/{kind_id}", response_model=List[BerichtOut])
def berichte_eines_kindes(kind_id: int, db: Session = Depends(get_db)):
    return db.query(Tagesbericht).filter(Tagesbericht.kind_id == kind_id).order_by(Tagesbericht.datum.desc()).all()

@router.get("/{bericht_id}", response_model=BerichtOut)
def bericht_anzeigen(bericht_id: int, db: Session = Depends(get_db)):
    bericht = db.query(Tagesbericht).filter(Tagesbericht.id == bericht_id).first()
    if not bericht:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
    return bericht

@router.post("/{bericht_id}/pruefen", response_model=BerichtOut)
async def bericht_pruefen(bericht_id: int, db: Session = Depends(get_db)):
    bericht = db.query(Tagesbericht).filter(Tagesbericht.id == bericht_id).first()
    if not bericht:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
    kind = db.query(Kind).filter(Kind.id == bericht.kind_id).first()
    kind_info = f"Name: {kind.vorname} {kind.nachname or ''}\nBesonderheiten: {kind.besonderheiten or '-'}\nHinweise: {kind.dokumentationshinweise or '-'}"
    ergebnis = await pruefe_bericht(kind_info, bericht.rohtext)
    bericht.wrap_ergebnis = ergebnis
    text = ergebnis.lower()
    if "rot" in text:
        bericht.ampel = Ampel.rot
    elif "gelb" in text:
        bericht.ampel = Ampel.gelb
    else:
        bericht.ampel = Ampel.gruen
    db.commit()
    db.refresh(bericht)
    return bericht

@router.post("/{bericht_id}/freigeben", response_model=BerichtOut)
def bericht_freigeben(bericht_id: int, db: Session = Depends(get_db)):
    bericht = db.query(Tagesbericht).filter(Tagesbericht.id == bericht_id).first()
    if not bericht:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
    bericht.status = BerichtStatus.freigegeben
    bericht.freigegeben_am = datetime.utcnow()
    db.commit()
    db.refresh(bericht)
    return bericht
