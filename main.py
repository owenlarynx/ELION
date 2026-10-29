from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import models  # noqa: F401  (registriert die Tabellen)
from database import ensure_schema
from pfade import bundle_root

ensure_schema()

app = FastAPI(title="Elion API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import berichte, kinder, kontakte, medikamente, pruefung, seed

app.include_router(kinder.router)
app.include_router(berichte.router)
app.include_router(medikamente.router)
app.include_router(kontakte.router)
app.include_router(seed.router)
app.include_router(pruefung.router)

STATIC_DIR = bundle_root() / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
