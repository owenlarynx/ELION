from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db
from models import Kind

router = APIRouter(prefix="/kinder", tags=["kinder"])

class KindCreate(BaseModel):
    vorname: str
    nachname: Optional[str] = None
    paragraph: Optional[str] = None
    besonderheiten: Optional[str] = None
    dokumentationshinweise: Optional[str] = None

class KindOut(BaseModel):
    id: int
    vorname: str
    nachname: Optional[str]
    aktiv: bool
    paragraph: Optional[str]
    besonderheiten: Optional[str]
    dokumentationshinweise: Optional[str]
    erstellt_am: datetime
    geaendert_am: datetime
    class Config:
        from_attributes = True

@router.get("/", response_model=List[KindOut])
def liste_kinder(db: Session = Depends(get_db)):
    return db.query(Kind).filter(Kind.aktiv == True).all()

@router.post("/", response_model=KindOut)
def kind_anlegen(kind: KindCreate, db: Session = Depends(get_db)):
    neues_kind = Kind(
        vorname=kind.vorname,
        nachname=kind.nachname,
        paragraph=kind.paragraph,
        besonderheiten=kind.besonderheiten,
        dokumentationshinweise=kind.dokumentationshinweise
    )
    db.add(neues_kind)
    db.commit()
    db.refresh(neues_kind)
    return neues_kind

@router.get("/{kind_id}", response_model=KindOut)
def kind_anzeigen(kind_id: int, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    return kind
