# ELION

Internes Dokumentationssystem für stationäre Kinder- und Jugendhilfeeinrichtungen.
Der Pilot arbeitet mit Platzhalter-Daten (Katzen). Keine echten Personendaten eintragen.

- Backend: Python, FastAPI, SQLAlchemy, SQLite
- Frontend: statisches HTML/JS (`static/`)
- KI-Prüfung: lokales Ollama (`llama3.1`), erreichbar unter `http://localhost:11434`

## Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Dann http://localhost:8000 öffnen.

Die Oberfläche hat drei Arbeitsansichten: die Tagesübersicht, den Bericht eines Kindes und das Wochenraster. Kinder, Medikamente und Kontakte liegen unter Verwaltung.

Die Prüfung eines Berichts läuft über Ollama und erwartet eine JSON-Antwort mit Ampel, Hinweisen und kurzer Begründung. Wenn Ollama nicht erreichbar ist, bleibt die Ampel leer; es wird kein Grün gesetzt.

## Konfiguration

Die Datenbank lässt sich über `ELION_DATABASE_URL` setzen. Standard ist `sqlite:///./elion.db`.

```bash
export ELION_DATABASE_URL=sqlite:///./elion.db
```

Optional: `ELION_OLLAMA_URL` (Standard `http://localhost:11434/api/chat`) und `ELION_OLLAMA_MODELL` (Standard `llama3.1`).

Beim Start wird eine fehlende Spalte `schicht` in einer bestehenden SQLite-Datei ergänzt. Werte sind `frueh` und `spaet`; ohne Schicht bleibt das Feld leer. Liegen für einen Tag Schichtberichte vor, zeigt das Wochenraster zwei Punkte (links Frühdienst, rechts Spätdienst).

## Tests

```bash
pip install -r requirements.txt
pytest
```

Die Tests nutzen eine temporäre SQLite-Datei und ein nachgestelltes Ollama. Ein laufendes Modell ist dafür nicht nötig.
