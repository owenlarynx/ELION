# ELION unter Windows einrichten

Testfassung. Die Setup-Datei installiert nur ELION. Ollama und das Sprachmodell sind nicht darin enthalten.

## Voraussetzung

- Windows 10 oder 11, 64 Bit
- Für das Modell `llama3.1:8b`: etwa 16 GB Arbeitsspeicher sind ein ruhiger Alltagswert
- Freier Speicher: die Setup-Datei selbst (einige zehn Megabyte), dazu Ollama (separater Installer, üblicherweise einige hundert Megabyte) und danach das Modell (etwa 4,7 GB)

## Installation

1. `ELION-Setup-0.9.1-test.exe` starten und den Schritten folgen.
2. Eine Verknüpfung liegt im Startmenü. Auf Wunsch auch auf dem Desktop.
3. Ollama getrennt einrichten. Im Setup kann die Downloadseite <https://ollama.com/download> geöffnet werden. Der Ollama-Installer kommt von dort, nicht aus der ELION-Datei.
4. ELION über die Verknüpfung starten. Es öffnet sich der Browser, ohne schwarzes Konsolenfenster. Ein zweiter Doppelklick öffnet die Oberfläche erneut. Beenden geht über das Startmenü „ELION beenden“.
5. Läuft Ollama noch nicht, zeigt ELION das und bietet **Ollama starten** an, wenn das Programm installiert ist. **Erneut prüfen** fragt den Dienst noch einmal. ELION spricht `127.0.0.1:11434` an, damit Windows nicht auf IPv6 ausweicht.

## Erster Start und Modell

Oben in der Oberfläche steht, ob Ollama erreichbar ist.

- Fehlt Ollama, setzt eine neue Prüfung keine Ampel. **Modell laden** bleibt dann aus und nennt den Grund.
- Ist Ollama installiert, der Dienst aber aus, **Ollama starten** und danach **Erneut prüfen**.
- Ist Ollama da und das Modell fehlt, bleibt der Download stehen, bis **Modell laden** bestätigt wird. Standard ist `llama3.1:8b`.
- In der Auswahlliste gibt es außerdem `qwen2.5:7b` und `qwen2.5:14b`. Andere Namen lassen sich eintragen. Sehr große Modelle wie 70B sind nicht Teil dieser Einrichtung und werden nur geladen, wenn der Name bewusst gewählt wird.
- `OLLAMA_MODEL` in der Umgebung hat Vorrang vor der Auswahl in der Oberfläche.

## Testen

1. Verwaltung öffnen und **Pilotdaten laden**. Die Kürzel AK, MS, LS, BH, AB und EST sind Testdaten. Ampeln darin sind Beispielampeln ohne KI-Prüfung.
2. In Woche oder Monat Früh oder Spät öffnen, Text ändern, **Speichern Entwurf**, dann **Prüfung starten**.
3. Mit laufendem Ollama und geladenem Modell erscheinen Ampel, Fazit und ein Vorschlag. **Übernehmen** oder **Anpassen**, danach **Freigeben**.
4. **Demo ausblenden** nimmt die Kürzel aus der Tagesansicht. Die Berichte bleiben gespeichert.

## Deinstallation

ELION unter Windows bei „Apps“ entfernen. Verknüpfungen gehen mit.

Die Datenbank bleibt unter `%LOCALAPPDATA%\ELION`. Diesen Ordner nur löschen, wenn die lokalen Berichte auch weg sollen. Ollama wird von dieser Deinstallation nicht entfernt.

## Lizenzhinweis

Persönliches Testen des Ra-Thor-Wraps fällt unter AG-SML. Organisatorische oder kommerzielle Nutzung braucht eine Lizenz. Der Hinweis dazu steht bei info@Rathor.ai. ELION verschickt keine E-Mail.
