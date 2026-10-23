from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import Kontakt, Kind, KontaktTyp

router = APIRouter(prefix="/kontakte", tags=["kontakte"])

class KontaktCreate(BaseModel):
    kind_id: int
    typ: KontaktTyp
    name: str
    telefon: Optional[str] = None
    email: Optional[str] = None
    hinweis: Optional[str] = None

class KontaktOut(BaseModel):
    id: int
    kind_id: int
    typ: KontaktTyp
    name: str
    telefon: Optional[str]
    email: Optional[str]
    hinweis: Optional[str]
    aktiv: bool
    class Config:
        from_attributes = True

@router.post("/", response_model=KontaktOut)
def kontakt_anlegen(kontakt: KontaktCreate, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == kontakt.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    neu = Kontakt(**kontakt.dict())
    db.add(neu)
    db.commit()
    db.refresh(neu)
    return neu

@router.get("/kind/{kind_id}", response_model=List[KontaktOut])
def kontakte_eines_kindes(kind_id: int, db: Session = Depends(get_db)):
    return db.query(Kontakt).filter(Kontakt.kind_id == kind_id, Kontakt.aktiv == True).all()
