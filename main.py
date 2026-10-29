from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import models  # noqa: F401  (registriert die Tabellen)
from database import ensure_schema

ensure_schema()

app = FastAPI(title="Elion API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import berichte, kinder, kontakte, medikamente, seed

app.include_router(kinder.router)
app.include_router(berichte.router)
app.include_router(medikamente.router)
app.include_router(kontakte.router)
app.include_router(seed.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
