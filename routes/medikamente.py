from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from database import get_db
from models import Medikament, Kind

router = APIRouter(prefix="/medikamente", tags=["medikamente"])


class MedikamentCreate(BaseModel):
    kind_id: int
    name: str = Field(min_length=1)
    dosierung: Optional[str] = None
    einnahmezeit: Optional[str] = None
    hinweis: Optional[str] = None


class MedikamentUpdate(BaseModel):
    name: Optional[str] = None
    dosierung: Optional[str] = None
    einnahmezeit: Optional[str] = None
    hinweis: Optional[str] = None
    aktiv: Optional[bool] = None


class MedikamentOut(BaseModel):
    id: int
    kind_id: int
    name: str
    dosierung: Optional[str]
    einnahmezeit: Optional[str]
    hinweis: Optional[str]
    aktiv: bool
    model_config = ConfigDict(from_attributes=True)


def _medikament_oder_404(db: Session, medikament_id: int) -> Medikament:
    medikament = db.query(Medikament).filter(Medikament.id == medikament_id).first()
    if not medikament:
        raise HTTPException(status_code=404, detail="Medikament nicht gefunden")
    return medikament


@router.post("/", response_model=MedikamentOut)
def medikament_anlegen(med: MedikamentCreate, db: Session = Depends(get_db)):
    kind = db.query(Kind).filter(Kind.id == med.kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    name = med.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name fehlt")
    neu = Medikament(
        kind_id=med.kind_id,
        name=name,
        dosierung=med.dosierung,
        einnahmezeit=med.einnahmezeit,
        hinweis=med.hinweis,
    )
    db.add(neu)
    db.commit()
    db.refresh(neu)
    return neu


@router.get("/kind/{kind_id}", response_model=List[MedikamentOut])
def medikamente_eines_kindes(kind_id: int, inkl_inaktiv: bool = False, db: Session = Depends(get_db)):
    abfrage = db.query(Medikament).filter(Medikament.kind_id == kind_id)
    if not inkl_inaktiv:
        abfrage = abfrage.filter(Medikament.aktiv == True)  # noqa: E712
    return abfrage.order_by(Medikament.name).all()


@router.put("/{medikament_id}", response_model=MedikamentOut)
def medikament_aendern(medikament_id: int, daten: MedikamentUpdate, db: Session = Depends(get_db)):
    medikament = _medikament_oder_404(db, medikament_id)
    geaendert = daten.model_dump(exclude_unset=True)
    if "name" in geaendert:
        name = (geaendert["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name fehlt")
        geaendert["name"] = name
    for feld, wert in geaendert.items():
        setattr(medikament, feld, wert)
    db.commit()
    db.refresh(medikament)
    return medikament


@router.delete("/{medikament_id}", response_model=MedikamentOut)
def medikament_deaktivieren(medikament_id: int, db: Session = Depends(get_db)):
    medikament = _medikament_oder_404(db, medikament_id)
    medikament.aktiv = False
    db.commit()
    db.refresh(medikament)
    return medikament
