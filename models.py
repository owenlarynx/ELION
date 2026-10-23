from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base, utc_now
import enum


class Rolle(enum.Enum):
    fachkraft = "fachkraft"
    leitung = "leitung"


class Ampel(enum.Enum):
    gruen = "gruen"
    gelb = "gelb"
    rot = "rot"


class BerichtStatus(enum.Enum):
    entwurf = "entwurf"
    freigegeben = "freigegeben"


class Schicht(enum.Enum):
    frueh = "frueh"
    mittel = "mittel"
    spaet = "spaet"
    nacht = "nacht"


SCHICHT_REIHENFOLGE = {
    "frueh": 0,
    "mittel": 1,
    "spaet": 2,
    "nacht": 3,
}


class KontaktTyp(enum.Enum):
    eltern = "eltern"
    asd = "asd"
    vormund = "vormund"
    sonstige = "sonstige"


class Mitarbeiter(Base):
    __tablename__ = "mitarbeiter"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String)
    passwort_hash = Column(String)
    rolle = Column(Enum(Rolle), default=Rolle.fachkraft)
    aktiv = Column(Boolean, default=True)


class Kind(Base):
    __tablename__ = "kinder"
    id = Column(Integer, primary_key=True, index=True)
    vorname = Column(String, nullable=False)
    nachname = Column(String, nullable=True)
    aktiv = Column(Boolean, default=True)
    paragraph = Column(String, nullable=True)
    besonderheiten = Column(Text, nullable=True)
    dokumentationshinweise = Column(Text, nullable=True)
    erstellt_am = Column(DateTime, default=utc_now)
    geaendert_am = Column(DateTime, default=utc_now, onupdate=utc_now)
    medikamente = relationship("Medikament", back_populates="kind")
    kontakte = relationship("Kontakt", back_populates="kind")
    berichte = relationship("Tagesbericht", back_populates="kind")


class Medikament(Base):
    __tablename__ = "medikamente"
    id = Column(Integer, primary_key=True, index=True)
    kind_id = Column(Integer, ForeignKey("kinder.id"))
    name = Column(String, nullable=False)
    dosierung = Column(String, nullable=True)
    einnahmezeit = Column(String, nullable=True)
    hinweis = Column(Text, nullable=True)
    aktiv = Column(Boolean, default=True)
    kind = relationship("Kind", back_populates="medikamente")


class Kontakt(Base):
    __tablename__ = "kontakte"
    id = Column(Integer, primary_key=True, index=True)
    kind_id = Column(Integer, ForeignKey("kinder.id"))
    typ = Column(Enum(KontaktTyp))
    name = Column(String, nullable=False)
    telefon = Column(String, nullable=True)
    email = Column(String, nullable=True)
    hinweis = Column(Text, nullable=True)
    aktiv = Column(Boolean, default=True)
    kind = relationship("Kind", back_populates="kontakte")


class Tagesbericht(Base):
    __tablename__ = "tagesberichte"
    id = Column(Integer, primary_key=True, index=True)
    kind_id = Column(Integer, ForeignKey("kinder.id"))
    datum = Column(DateTime, nullable=False)
    schicht = Column(Enum(Schicht), nullable=True)
    rohtext = Column(Text, nullable=False)
    wrap_ergebnis = Column(Text, nullable=True)
    ampel = Column(Enum(Ampel), nullable=True)
    status = Column(Enum(BerichtStatus), default=BerichtStatus.entwurf)
    erstellt_von = Column(String, nullable=True)
    freigegeben_von = Column(String, nullable=True)
    erstellt_am = Column(DateTime, default=utc_now)
    freigegeben_am = Column(DateTime, nullable=True)
    kind = relationship("Kind", back_populates="berichte")
    versionen = relationship("BerichtVersion", back_populates="bericht")


class BerichtVersion(Base):
    __tablename__ = "bericht_versionen"
    id = Column(Integer, primary_key=True, index=True)
    bericht_id = Column(Integer, ForeignKey("tagesberichte.id"), nullable=False, index=True)
    rohtext = Column(Text, nullable=False)
    schicht = Column(Enum(Schicht), nullable=True)
    ampel = Column(Enum(Ampel), nullable=True)
    wrap_ergebnis = Column(Text, nullable=True)
    freigegeben_am = Column(DateTime, nullable=True)
    freigegeben_von = Column(String, nullable=True)
    geaendert_von = Column(String, nullable=True)
    archiviert_am = Column(DateTime, default=utc_now, nullable=False)
    bericht = relationship("Tagesbericht", back_populates="versionen")
