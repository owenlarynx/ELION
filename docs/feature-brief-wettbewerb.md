# ELION – Feature-Brief (Wettbewerb & Ausbau)

Stand: 2026-10-29 (Europe/Berlin)  
Quelle: Fertiger Auftrag von Мұз (normaler Grok-Chat → Alpha)

## 1. Ziel

ELION als lokales (on-prem) Dokumentations- und Prüfungssystem für stationäre Kinder- und Jugendhilfe weiter ausbauen: innovativ, testbereit, klar abgegrenzt von Cloud-SaaS (Kuuna u. a.).

## 2. Priorisierung – nächster Entwicklungsschritt (Must-haves)

1. **Wochenübersicht (Früh-/Spätschicht)** – Ampel-Lage über die Woche, Fokus Früh- und Spätschicht (bestehende Mittel-/Nachtdienste nicht zerstören, aber diese Priorität).
2. **Kindprofil** – strukturierte **Medikamente** und **Kontakte** (Bearbeitung in Verwaltung / Profil).
3. **Ampel-Logik im Tagesbericht** – Ra-Thor-Wrap fest verdrahtet: Prüfung → Grün/Gelb/Rot + Vorschlag; stabil mit Ollama; klare Meldung wenn Ollama fehlt.

## 3. Nice-to-have (spätere Version)

- **Monatsansicht** – planen, aber nicht im nächsten Sprint blockierend umsetzen.

## 4. Abgrenzung (verbindlich)

| | ELION | Kuuna / Cloud-Produkte (z. B. klassische Cloud-SaaS) |
|---|---|---|
| Betrieb | lokal / on-prem (EXE + Ollama) | Cloud-SaaS |
| Kern | Prüfung, Ampel, pädagogische Umformulierung des selbst geschriebenen Texts (Ra-Thor-Wrap) | KI-Zusammenfassungen, Vorlagen, Mobile Cloud |
| Daten | bleiben in der Einrichtung | gehostet beim Anbieter |

- Keine Übernahme von Kuuna-Texten, Claims, Screenshots, Logos oder Design-Elementen.
- Interne Bezeichnung ELION ok; kommerzielle Marke separat klären (bekanntes Risiko).
- Pilotkinder nur Initialen: AK, MS, LS, BH, AB, EST.

## 5. Interner Pitch (nicht für öffentliche Claims — Repo ist public)

**ELION** ist die lokale Ampel-Prüfung für Tagesdokus: schreiben wie bisher, prüfen mit Ollama + Ra-Thor-Wrap, Freigabe mit Verlauf — ohne Cloud-Zwang. Gegenüber **Kuuna** und anderen Cloud-SaaS: Daten bleiben vor Ort, Fokus auf Vollständigkeit und pädagogische Qualität statt generischer KI-Zusammenfassung. Gegenüber klassischen Systemen (z. B. **Vivendi** u. a.): schlanke Schicht- und Ampel-Arbeitsoberfläche für den Alltag in der Wohngruppe, statt schwerer Träger-Suite. Windows-EXE + Ollama für den Start auf dem Dienstrechner.

## 6. Lizenzhinweis Ra-Thor-Wrap

- Persönliches Testen: AG-SML ok.  
- Organisatorische / kommerzielle Nutzung: Commercial Licence über info@Rathor.ai.

## 7. AUFTRAG FÜR LEAD MATE / ALPHA (umsetzen)

1. Speichere diesen Feature-Brief unter `docs/feature-brief-wettbewerb.md`.
2. Priorisiere die Must-haves für den nächsten Entwicklungsschritt:
   - Wochenübersicht (Früh-/Spätschicht)
   - Kindprofil mit strukturierten Medikamenten und Kontakten
   - Ampel-Logik im Tagesbericht (Ra-Thor-Wrap)
3. Plane die Monatsansicht als Nice-to-have für eine spätere Version.
4. Halte die Abgrenzung zu Kuuna und anderen Cloud-Produkten klar (on-prem + Prüfung).
5. Bereite einen kurzen internen Pitch vor, der die Stärken (lokal, Ampel, Ra-Thor-Wrap) gegenüber Kuuna und klassischen Systemen (Vivendi etc.) hervorhebt.
6. Gib den Brief und die Priorisierung an den PATSAGi-Council und die Cloud-Agents weiter.
