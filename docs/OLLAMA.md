# Ollama für ELION

ELION schickt die Prüfung eines Tagesberichts an ein lokales Ollama.
Standardmodell ist `llama3.1`. Läuft Ollama nicht, bleibt die Ampel leer.

ELION ruft `POST {OLLAMA_URL}/api/chat` auf. `OLLAMA_URL` ist die Basisadresse
(Standard `http://localhost:11434`). Endet der Wert schon auf `/api/chat`, wird er so verwendet.

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `OLLAMA_URL` | `http://localhost:11434` | Adresse von Ollama |
| `OLLAMA_MODEL` | `llama3.1` | Modellname |
| `ELION_PROMPT_PATH` | `prompts/ra_thor_wrap.md` | Prüfvorlage, bei jedem Prüfen neu gelesen |

## Windows

1. Den Installer von [https://ollama.com/download](https://ollama.com/download) laden und ausführen.
2. Ollama startet danach im Hintergrund (Symbol in der Taskleiste).
3. PowerShell oder Eingabeaufforderung öffnen und das Modell laden:

```powershell
ollama pull llama3.1
ollama list
```

4. ELION im Projektordner starten (`uvicorn main:app --reload`) und einen Bericht prüfen.
   Die Oberfläche spricht `http://localhost:11434` an.

## Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1
ollama list
```

Das Installationsskript richtet einen Dienst ein, der auf `127.0.0.1:11434` lauscht.
ELION danach wie in der README starten. Optional vor dem Start:

```bash
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=llama3.1
```

## Docker Compose (Windows und Linux)

Wer Ollama nicht auf dem Rechner installieren will, startet App und Ollama zusammen.
Dafür braucht es Docker Desktop (Windows) oder die Docker Engine (Linux).

```bash
docker compose up --build
```

- ELION: http://localhost:8000
- Ollama auf dem Host: http://localhost:11434
- Im Netz von Compose spricht die App `http://ollama:11434` an.

Der Dienst `ollama-pull` lädt `llama3.1` beim ersten Start. Das sind mehrere Gigabyte;
die App wartet, bis der Download fertig ist. Ein weiteres `docker compose up` zieht das
Modell nur neu, wenn es fehlt.

Anderes Modell:

```bash
OLLAMA_MODEL=llama3.1 docker compose up --build
```

Die SQLite-Datei liegt im Volume `elion-data`, die Modelldateien im Volume `ollama`.

Nicht gleichzeitig den Ollama-Dienst des Betriebssystems und Compose auf Port 11434 betreiben.

## Prüfvorlage und Ra-Thor-Wrap

Die Prüfanweisung steht in `prompts/ra_thor_wrap.md`, nicht im Python-Code.
`# System` und `# Auftrag` bleiben die geltende deutsche Prüfanweisung samt JSON-Vertrag
(`ampel`, `umformulierungen`, `hinweise`, `kurzbegruendung`, `verbesserte_fassung`).
Standardmodell ist `llama3.1`. Ein größeres Modell wie `qwen2.5:14b` oder `llama3.1:70b` formuliert auf Deutsch sicherer, wenn die Hardware das trägt. Der Name steht in `OLLAMA_MODEL`.

Den späteren Ra-Thor-Wrap-Text zwischen diese beiden Zeilen setzen:

```text
<<<RA_THOR_WRAP>>>
<<<ENDE_RA_THOR_WRAP>>>
```

Solange dort nur der HTML-Kommentar steht, geht er nicht an das Modell.
Nach dem Speichern gilt der neue Text beim nächsten Klick auf „Prüfen“, ohne Neustart.
Liegt die Datei woanders:

```bash
export ELION_PROMPT_PATH=/pfad/zur/ra_thor_wrap.md
```

In Compose ist die Datei zusätzlich nach `/app/prompts/ra_thor_wrap.md` eingehängt.
Eine Änderung auf dem Host gilt damit auch im Container beim nächsten Prüfen.
