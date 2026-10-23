# ELION

Internes Dokumentationssystem für stationäre Kinder- und Jugendhilfeeinrichtungen (Pilot mit Platzhalter-Daten).

- Backend: Python, FastAPI, SQLite
- Frontend: statisches HTML/JS (`static/`)
- KI-Prüfung: lokales Ollama (`llama3.1`)

## Start

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Dann http://localhost:8000 öffnen.
