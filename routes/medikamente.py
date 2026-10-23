from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import Medikament, Kind

router = APIRouter(prefix="/medikamente", tags=["medikamente"])

class MedikamentCreate(BaseModel):
    kind_id: int
    name: str
    dosierung: Optional[str] = None
    einnahmezeit: Optional[str] = None
    hinweis: Optional[str] = None

class MedikamentOut(BaseModel):
    id: int
    kind_id: int
    name: str
    dosierung: Optional[str]
    einnahmezeit: Optional[str]
    hinweis: Optional[str]
    aktiv: bool
    class Config:
        from_attributes = True

@router.post("/", response_model=MedikamentOut)
def medikament_anlegen(med: MedikamentCreate, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == med.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    neu = Medikament(**med.dict())
    db.add(neu)
    db.commit()
    db.refresh(neu)
    return neu

@router.get("/kind/{kind_id}", response_model=List[MedikamentOut])
def medikamente_eines_kindes(kind_id: int, db: Session = Depends(get_db)):
    return db.query(Medikament).filter(Medikament.kind_id == kind_id, Medikament.aktiv == True).all()
