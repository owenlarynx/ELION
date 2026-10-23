from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Elion API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import kinder, berichte, medikamente, kontakte
app.include_router(kinder.router)
app.include_router(berichte.router)
app.include_router(medikamente.router)
app.include_router(kontakte.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
