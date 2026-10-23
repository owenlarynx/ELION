import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool


def utc_now():
    """Naive UTC timestamp. SQLite DateTime columns have no timezone."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def database_url() -> str:
    return os.environ.get("ELION_DATABASE_URL", "sqlite:///./elion.db")


def _engine_for(url: str):
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )
    return create_engine(url)


DATABASE_URL = database_url()
engine = _engine_for(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema(bind=None):
    """Create tables and add columns introduced after the first pilot database."""
    ziel = bind or engine
    Base.metadata.create_all(bind=ziel)
    if ziel.dialect.name != "sqlite":
        return
    with ziel.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(tagesberichte)")).fetchall()
        if not rows:
            return
        spalten = {row[1] for row in rows}
        if "schicht" not in spalten:
            conn.execute(text("ALTER TABLE tagesberichte ADD COLUMN schicht VARCHAR"))
