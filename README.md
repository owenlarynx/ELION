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

Die Prüfung eines Berichts läuft über Ollama und erwartet eine JSON-Antwort mit Ampel, Hinweisen und kurzer Begründung. Wenn Ollama nicht erreichbar ist, bleibt die Ampel leer; es wird kein Grün gesetzt. Installation unter Windows und Linux, Docker Compose und die Prüfvorlage stehen in [docs/OLLAMA.md](docs/OLLAMA.md).

## Konfiguration

Die Datenbank lässt sich über `ELION_DATABASE_URL` setzen. Standard ist `sqlite:///./elion.db`.

```bash
export ELION_DATABASE_URL=sqlite:///./elion.db
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1
```

`OLLAMA_URL` ist die Basisadresse. `OLLAMA_MODEL` ist der Modellname. Die Prüfanweisung liegt in `prompts/ra_thor_wrap.md` und lässt sich über `ELION_PROMPT_PATH` auf eine andere Datei legen. Zwischen den Markierungen `<<<RA_THOR_WRAP>>>` und `<<<ENDE_RA_THOR_WRAP>>>` kann später der Ra-Thor-Wrap-Text stehen.

Beim Start werden fehlende Tabellen und Spalten in einer bestehenden SQLite-Datei ergänzt. Schichtwerte sind `frueh`, `mittel`, `spaet` und `nacht` (Frühdienst, Mitteldienst mit etwa 12 Stunden, Spätdienst, Nachtdienst). Bestehende Werte `frueh` und `spaet` bleiben gültig. Startseite und Wochenraster zeigen pro Kind und Tag nur die schlechteste Ampel (Rot vor Gelb vor Grün). Fehlende oder ungeprüfte Schichten stehen als kurzer Hinweis daneben. Die einzelnen Schichten sieht man im Bericht. Ein freigegebener Bericht lässt sich als Nachtrag ändern. Die bisherige Fassung bleibt im Verlauf, die Ampel gilt als veraltet, und der Bericht muss erneut geprüft und freigegeben werden.

## Tests

```bash
pip install -r requirements.txt
pytest
```

Die Tests nutzen eine temporäre SQLite-Datei und ein nachgestelltes Ollama. Ein laufendes Modell ist dafür nicht nötig.
