# ELION

Tagesdokumentation für stationäre Kinder- und Jugendhilfe, auf dem Rechner der Einrichtung.
Prüfung und Ampel bleiben vor Ort: lokales Ollama, keine Cloud. Im Pilot nur Kürzel und Beispieltexte verwenden, keine echten Personendaten.

- Backend: Python, FastAPI, SQLAlchemy, SQLite
- Frontend: statisches HTML/JS (`static/`), ohne Build-Schritt
- KI-Prüfung: lokales Ollama (`llama3.1`), erreichbar unter `http://localhost:8000` für ELION und `http://localhost:11434` für Ollama

## Start auf dem Mac

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Dann http://localhost:8000 öffnen.

Unter **Verwaltung → Pilotdaten laden** erscheinen die Kürzel AK, MS, LS, BH, AB und EST mit Beispielberichten. Dieselbe Aktion liegt auf der leeren Startseite und als `POST /seed/pilot`. Ein zweiter Lauf legt nichts doppelt an und überschreibt keine vorhandenen Berichte. Wer neu beginnen will, beendet ELION, löscht `elion.db` und startet erneut.

Für eine neue Prüfung muss Ollama laufen. Die mitgelieferten Ampeln sind schon gespeichert und bleiben sichtbar, auch wenn Ollama aus ist. Installation auf dem Mac, unter Windows und Linux, Docker Compose und die Prüfvorlage stehen in [docs/OLLAMA.md](docs/OLLAMA.md). Kurz auf dem Mac: `brew install ollama` oder der Installer von ollama.com, danach `ollama pull llama3.1`.

## Start unter Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

http://localhost:8000 öffnen, dann wie oben die Pilotdaten laden. Ollama: [docs/OLLAMA.md](docs/OLLAMA.md).

## Docker Compose

```bash
docker compose up --build
```

ELION: http://localhost:8000. Der erste Start lädt das Modell (mehrere GB). Die Datenbank liegt im Volume `elion-data`. Pilotdaten danach in der Verwaltung laden. Einzelheiten in [docs/OLLAMA.md](docs/OLLAMA.md).

## Oberfläche prüfen

1. Heute zeigt die Ampel des Tages und die vier Schichten. Ein Kürzel öffnet den Tagesbericht, eine Schicht direkt diese Schicht.
2. Text schreiben, **Speichern Entwurf**, **Prüfung starten**. Die Prüfung zeigt Ampel, Fazit, gelbe Lücken `[Bitte ergänzen: …]`, Paare von wertend zu pädagogisch und kurze Hinweise.
3. **Übernehmen** setzt den Vorschlag in den Bericht. **Anpassen** öffnet ihn zum Ändern. Danach erneut speichern, bei Bedarf neu prüfen, dann **Freigeben**.
4. **Bearbeiten / Nachtrag** ändert einen freigegebenen Bericht. Die alte Fassung bleibt im Verlauf, die Ampel wird verworfen und muss neu gesetzt werden.
5. Woche stellt Frühdienst und Spätdienst als Hauptfelder dar. Mittel- und Nachtdienst bleiben daneben. Ein Feld öffnet diese Schicht, auch an einem vergangenen Tag.
6. Verwaltung legt Kinder an, deaktiviert sie, pflegt Medikation nur wo sie gilt, und Kontakte. **Bericht öffnen** springt in die Tagesarbeit.

Schichten: Frühdienst, Mitteldienst (etwa 12 Stunden), Spätdienst, Nachtdienst. Ältere Berichte ohne Schicht bleiben gültig. Startseite und Woche zeigen pro Kind und Tag die schlechteste Ampel, Rot vor Gelb vor Grün.

## Prüfung

Die Ampel bewertet die Dokumentation, nicht das Kind. Die Prüfung läuft lokal über Ollama in einem Aufruf und erwartet eine JSON-Antwort mit Ampel, Umformulierungen (Zitat und Vorschlag), kurzen pädagogischen Hinweisen und einer verbesserten Fassung. Die Prüfanweisung samt Ra-Thor-Wrap liegt in `prompts/ra_thor_wrap.md` und wird bei jedem Prüfen neu gelesen (`ELION_PROMPT_PATH`). Fehlende Angaben stehen darin als Platzhalter `[Bitte ergänzen: …]`. Zitate, die im Text nicht vorkommen, werden verworfen. Sätze mit neuen Handlungen, Orten oder Gegenständen ebenfalls. Fehlt danach ein Fakt aus dem Original, bleibt eine rechtschreibkorrigierte Fassung des Originals. Ist keine Medikation hinterlegt, entfallen Medikationshinweise, Medikationsplatzhalter und Sätze wie „Keine Medikation wurde gegeben“. Wenn Ollama nicht erreichbar ist, bleibt die Ampel leer; es wird kein Grün gesetzt.

## Konfiguration

Die Datenbank lässt sich über `ELION_DATABASE_URL` setzen. Standard ist `sqlite:///./elion.db`.

```bash
export ELION_DATABASE_URL=sqlite:///./elion.db
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1
```

`OLLAMA_URL` ist die Basisadresse. `OLLAMA_MODEL` ist der Modellname, Standard ist `llama3.1`. Für deutlich besseres Deutsch eignet sich ein größeres Modell, wenn die Hardware reicht, zum Beispiel `qwen2.5:14b` oder `llama3.1:70b`. Die Prüfanweisung liegt in `prompts/ra_thor_wrap.md` und lässt sich über `ELION_PROMPT_PATH` auf eine andere Datei legen. Der Text zwischen `<<<RA_THOR_WRAP>>>` und `<<<ENDE_RA_THOR_WRAP>>>` geht bei jeder Prüfung mit; die Markierungen selbst nicht.

Beim Start werden fehlende Tabellen und Spalten in einer bestehenden SQLite-Datei ergänzt. Ein freigegebener Bericht lässt sich als Nachtrag ändern. Die bisherige Fassung bleibt im Verlauf, die Ampel gilt als veraltet, und der Bericht muss erneut geprüft und freigegeben werden.

## Tests

```bash
pip install -r requirements.txt
pytest
```

Die Tests nutzen eine temporäre SQLite-Datei und ein nachgestelltes Ollama. Ein laufendes Modell ist dafür nicht nötig.
