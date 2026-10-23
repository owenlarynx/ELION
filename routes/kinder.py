from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from database import get_db
from models import Kind

router = APIRouter(prefix="/kinder", tags=["kinder"])


class KindCreate(BaseModel):
    vorname: str = Field(min_length=1)
    nachname: Optional[str] = None
    paragraph: Optional[str] = None
    besonderheiten: Optional[str] = None
    dokumentationshinweise: Optional[str] = None


class KindUpdate(BaseModel):
    vorname: Optional[str] = None
    nachname: Optional[str] = None
    paragraph: Optional[str] = None
    besonderheiten: Optional[str] = None
    dokumentationshinweise: Optional[str] = None
    aktiv: Optional[bool] = None


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
    model_config = ConfigDict(from_attributes=True)


def _kind_oder_404(db: Session, kind_id: int) -> Kind:
    kind = db.query(Kind).filter(Kind.id == kind_id).first()
    if not kind:
        raise HTTPException(status_code=404, detail="Kind nicht gefunden")
    return kind


@router.get("/", response_model=List[KindOut])
def liste_kinder(inkl_inaktiv: bool = False, db: Session = Depends(get_db)):
    abfrage = db.query(Kind)
    if not inkl_inaktiv:
        abfrage = abfrage.filter(Kind.aktiv == True)  # noqa: E712
    kinder = abfrage.all()
    kinder.sort(key=lambda kind: ((kind.vorname or "").lower(), kind.id))
    return kinder


@router.post("/", response_model=KindOut)
def kind_anlegen(kind: KindCreate, db: Session = Depends(get_db)):
    vorname = kind.vorname.strip()
    if not vorname:
        raise HTTPException(status_code=400, detail="Vorname fehlt")
    neues_kind = Kind(
        vorname=vorname,
        nachname=kind.nachname,
        paragraph=kind.paragraph,
        besonderheiten=kind.besonderheiten,
        dokumentationshinweise=kind.dokumentationshinweise,
    )
    db.add(neues_kind)
    db.commit()
    db.refresh(neues_kind)
    return neues_kind


@router.get("/{kind_id}", response_model=KindOut)
def kind_anzeigen(kind_id: int, db: Session = Depends(get_db)):
    return _kind_oder_404(db, kind_id)


@router.put("/{kind_id}", response_model=KindOut)
def kind_aendern(kind_id: int, daten: KindUpdate, db: Session = Depends(get_db)):
    kind = _kind_oder_404(db, kind_id)
    geaendert = daten.model_dump(exclude_unset=True)
    if "vorname" in geaendert:
        vorname = (geaendert["vorname"] or "").strip()
        if not vorname:
            raise HTTPException(status_code=400, detail="Vorname fehlt")
        geaendert["vorname"] = vorname
    for feld, wert in geaendert.items():
        setattr(kind, feld, wert)
    db.commit()
    db.refresh(kind)
    return kind


@router.delete("/{kind_id}", response_model=KindOut)
def kind_deaktivieren(kind_id: int, db: Session = Depends(get_db)):
    kind = _kind_oder_404(db, kind_id)
    kind.aktiv = False
    db.commit()
    db.refresh(kind)
    return kind
