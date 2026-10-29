# Ollama für ELION

ELION schickt die Prüfung eines Tagesberichts an ein lokales Ollama.
Standardmodell für den ersten Lauf ist `llama3.1:8b` (etwa 4,7 GB, alltagstauglich bei 16 GB Arbeitsspeicher). Läuft Ollama nicht, setzt eine neue Prüfung keine Ampel. Beispielampeln aus den Testdaten sind gekennzeichnet.

ELION ruft `POST {OLLAMA_URL}/api/chat` auf. `OLLAMA_URL` ist die Basisadresse
(Standard `http://localhost:11434`). Endet der Wert schon auf `/api/chat`, wird er so verwendet.

| Variable | Standard | Bedeutung |
| --- | --- | --- |
| `OLLAMA_URL` | `http://localhost:11434` | Adresse von Ollama |
| `OLLAMA_MODEL` | `llama3.1:8b` | Modellname. Die Oberfläche kann ein anderes Modell wählen; diese Variable hat Vorrang. |
| `ELION_PROMPT_PATH` | `prompts/ra_thor_wrap.md` | Prüfvorlage, bei jedem Prüfen neu gelesen |

## Mac

1. Ollama von [https://ollama.com/download](https://ollama.com/download) laden oder mit Homebrew installieren: `brew install ollama`.
2. Das Modell laden:

```bash
ollama pull llama3.1:8b
ollama list
```

3. ELION im Projektordner starten (siehe README, Abschnitt Mac) und einen Bericht prüfen.
   Die Oberfläche spricht `http://localhost:11434` an.

## Windows

1. Den Installer von [https://ollama.com/download](https://ollama.com/download) laden und ausführen.
2. Ollama startet danach im Hintergrund (Symbol in der Taskleiste).
3. PowerShell oder Eingabeaufforderung öffnen und das Modell laden:

```powershell
ollama pull llama3.1:8b
ollama list
```

4. ELION im Projektordner starten (`uvicorn main:app --reload`) und einen Bericht prüfen.
   Die Oberfläche spricht `http://localhost:11434` an.

## Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
ollama list
```

Das Installationsskript richtet einen Dienst ein, der auf `127.0.0.1:11434` lauscht.
ELION danach wie in der README starten. Optional vor dem Start:

```bash
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=llama3.1:8b
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

Der Dienst `ollama-pull` lädt `llama3.1:8b` beim ersten Start von Compose. Das sind etwa 4,7 GB.
In der Oberfläche startet derselbe Download erst nach Zustimmung. Ein 70B-Modell gehört nicht zur Einrichtung.
Die App wartet, bis der Compose-Download fertig ist. Ein weiteres `docker compose up` zieht das
Modell nur neu, wenn es fehlt.

Anderes Modell:

```bash
OLLAMA_MODEL=qwen2.5:7b docker compose up --build
```

Die SQLite-Datei liegt im Volume `elion-data`, die Modelldateien im Volume `ollama`.

Nicht gleichzeitig den Ollama-Dienst des Betriebssystems und Compose auf Port 11434 betreiben.

## Prüfvorlage und Ra-Thor-Wrap

Die Prüfanweisung steht in `prompts/ra_thor_wrap.md`, nicht im Python-Code.
`# System` und `# Auftrag` bleiben die geltende deutsche Prüfanweisung samt JSON-Vertrag
(`ampel`, `umformulierungen`, `hinweise`, `kurzbegruendung`, `verbesserte_fassung`).
Standardmodell für den ersten Lauf ist `llama3.1:8b`. In der Oberfläche lassen sich außerdem `qwen2.5:7b` und `qwen2.5:14b` wählen. Sehr große Modelle wie 70B sind nicht Teil der Einrichtung. Der Name steht in `OLLAMA_MODEL`, wenn er die Oberfläche übersteuern soll.

Persönliches Testen des Ra-Thor-Wraps fällt unter AG-SML. Organisatorische oder kommerzielle Nutzung braucht eine Lizenz; der Hinweis dazu steht bei info@Rathor.ai. ELION verschickt keine E-Mail.

Der Text zwischen `<<<RA_THOR_WRAP>>>` und `<<<ENDE_RA_THOR_WRAP>>>` geht bei jeder Prüfung mit. Die Markierungen selbst nicht.
Nach dem Speichern gilt eine geänderte Datei beim nächsten Klick auf „Prüfung starten“, ohne Neustart.
Liegt die Datei woanders:

```bash
export ELION_PROMPT_PATH=/pfad/zur/ra_thor_wrap.md
```

In Compose ist die Datei zusätzlich nach `/app/prompts/ra_thor_wrap.md` eingehängt.
Eine Änderung auf dem Host gilt damit auch im Container beim nächsten Prüfen.
