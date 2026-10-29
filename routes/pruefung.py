from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import ollama_lauf
from wrap import ollama_modell

router = APIRouter(prefix="/pruefung", tags=["pruefung"])


class ModellWunsch(BaseModel):
    modell: str
    zustimmung: bool = False


@router.get("/lage")
async def pruef_lage():
    return await ollama_lauf.lage()


@router.get("/modell")
def modell_fortschritt():
    return ollama_lauf._job_kopie()


@router.post("/modell")
async def modell_waehlen(wunsch: ModellWunsch):
    name = (wunsch.modell or "").strip()
    if not wunsch.zustimmung:
        raise HTTPException(status_code=400, detail="Zustimmung fehlt. Das Modell wird nicht geladen.")
    if not ollama_lauf.modell_gueltig(name):
        raise HTTPException(status_code=400, detail="Modellname ungültig.")
    ollama_lauf.modell_merken(name)
    stand = await ollama_lauf.lage()
    if not stand["erreichbar"]:
        raise HTTPException(status_code=409, detail=stand["hinweis"])
    if stand["modell_vorhanden"] and ollama_modell() == name:
        return stand
    ollama_lauf.pull_starten(name)
    stand = await ollama_lauf.lage()
    stand["fortschritt"] = ollama_lauf._job_kopie()
    return stand
