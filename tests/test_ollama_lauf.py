import httpx

import ollama_lauf


def test_fortschritt_aus_objekt():
    assert ollama_lauf.fortschritt_aus_objekt({"status": "pulling manifest"}) == {
        "status": "pulling manifest",
        "prozent": None,
    }
    assert ollama_lauf.fortschritt_aus_objekt({"status": "downloading", "total": 200, "completed": 50}) == {
        "status": "downloading",
        "prozent": 25,
    }


def test_lage_ohne_ollama_setzt_keine_ampel(monkeypatch):
    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            raise httpx.ConnectError("nein")

    monkeypatch.setattr(ollama_lauf.httpx, "AsyncClient", Client)
    import asyncio
    stand = asyncio.run(ollama_lauf.lage())
    assert stand["erreichbar"] is False
    assert stand["modell_vorhanden"] is False
    assert "keine Ampel" in stand["hinweis"]
    assert "Grün" not in stand["hinweis"]


def test_modell_ohne_zustimmung_wird_nicht_geladen(client):
    antwort = client.post("/pruefung/modell", json={"modell": "llama3.1:8b", "zustimmung": False})
    assert antwort.status_code == 400
    assert "nicht geladen" in antwort.json()["detail"]


def test_modell_mit_zustimmung_startet_download(client, monkeypatch):
    async def lage():
        return {
            "erreichbar": True,
            "modell": "llama3.1:8b",
            "modell_vorhanden": False,
            "hinweis": "noch nicht da",
            "vorschlaege": ["llama3.1:8b"],
            "fortschritt": {},
        }

    gestartet = {}

    def starten(name):
        gestartet["name"] = name
        return {"laeuft": True, "modell": name, "prozent": 0, "status": "Download beginnt", "fehler": None, "fertig": False}

    monkeypatch.setattr("routes.pruefung.ollama_lauf.lage", lage)
    monkeypatch.setattr("routes.pruefung.ollama_lauf.pull_starten", starten)
    monkeypatch.setattr("routes.pruefung.ollama_lauf._job_kopie", lambda: starten("llama3.1:8b"))
    antwort = client.post("/pruefung/modell", json={"modell": "llama3.1:8b", "zustimmung": True})
    assert antwort.status_code == 200, antwort.text
    assert gestartet["name"] == "llama3.1:8b"
