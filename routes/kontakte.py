from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from database import get_db
from models import Kontakt, Kind, KontaktTyp

router = APIRouter(prefix="/kontakte", tags=["kontakte"])


class KontaktCreate(BaseModel):
    kind_id: int
    typ: KontaktTyp
    name: str = Field(min_length=1)
    telefon: Optional[str] = None
    email: Optional[str] = None
    hinweis: Optional[str] = None


class KontaktUpdate(BaseModel):
    typ: Optional[KontaktTyp] = None
    name: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    hinweis: Optional[str] = None
    aktiv: Optional[bool] = None


class KontaktOut(BaseModel):
    id: int
    kind_id: int
    typ: KontaktTyp
    name: str
    telefon: Optional[str]
    email: Optional[str]
    hinweis: Optional[str]
    aktiv: bool
    model_config = ConfigDict(from_attributes=True)


def _kontakt_oder_404(db: Session, kontakt_id: int) -> Kontakt:
    kontakt = db.query(Kontakt).filter(Kontakt.id == kontakt_id).first()
    if not kontakt:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")
    return kontakt


@router.post("/", response_model=KontaktOut)
def kontakt_anlegen(kontakt: KontaktCreate, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == kontakt.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    name = kontakt.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name fehlt")
    neu = Kontakt(
        kind_id=kontakt.kind_id,
        typ=kontakt.typ,
        name=name,
        telefon=kontakt.telefon,
        email=kontakt.email,
        hinweis=kontakt.hinweis,
    )
    db.add(neu)
    db.commit()
    db.refresh(neu)
    return neu


@router.get("/kind/{kind_id}", response_model=List[KontaktOut])
def kontakte_eines_kindes(kind_id: int, inkl_inaktiv: bool = False, db: Session = Depends(get_db)):
    abfrage = db.query(Kontakt).filter(Kontakt.kind_id == kind_id)
    if not inkl_inaktiv:
        abfrage = abfrage.filter(Kontakt.aktiv == True)  # noqa: E712
    return abfrage.order_by(Kontakt.name).all()


@router.put("/{kontakt_id}", response_model=KontaktOut)
def kontakt_aendern(kontakt_id: int, daten: KontaktUpdate, db: Session = Depends(get_db)):
    kontakt = _kontakt_oder_404(db, kontakt_id)
    geaendert = daten.model_dump(exclude_unset=True)
    if "name" in geaendert:
        name = (geaendert["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name fehlt")
        geaendert["name"] = name
    for feld, wert in geaendert.items():
        setattr(kontakt, feld, wert)
    db.commit()
    db.refresh(kontakt)
    return kontakt


@router.delete("/{kontakt_id}", response_model=KontaktOut)
def kontakt_deaktivieren(kontakt_id: int, db: Session = Depends(get_db)):
    kontakt = _kontakt_oder_404(db, kontakt_id)
    kontakt.aktiv = False
    db.commit()
    db.refresh(kontakt)
    return kontakt
