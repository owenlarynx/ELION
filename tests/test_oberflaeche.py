from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"
KERNAKTIONEN = (
    "Prüfung starten",
    "Speichern Entwurf",
    "Freigeben",
    "Übernehmen",
    "Anpassen",
    "Bearbeiten / Nachtrag",
    "Pilotdaten laden",
    "Zur Tagesarbeit",
    "Medikation",
    "Nachtrag speichern",
)
FREMDE_MARKEN = ("Kuuna", "KUUNA", "Klient", "Klienten")


def _oberflaeche() -> str:
    return "\n".join(
        (STATIC / name).read_text(encoding="utf-8")
        for name in ("index.html", "arbeit.js", "verwaltung.html", "verwaltung.js", "style.css")
    )


def test_oberflaeche_nennt_kernaktionen():
    texte = _oberflaeche()
    for schnipsel in KERNAKTIONEN:
        assert schnipsel in texte


def test_oberflaeche_ohne_fremde_marke():
    texte = _oberflaeche()
    for fremd in FREMDE_MARKEN:
        assert fremd not in texte


def test_startseite_und_verwaltung_werden_ausgeliefert(client):
    start = client.get("/")
    assert start.status_code == 200
    assert "Prüfung starten" in start.text
    assert "Tagesdoku vor Ort" in start.text
    verwaltung = client.get("/verwaltung.html")
    assert verwaltung.status_code == 200
    assert "Pilotdaten laden" in verwaltung.text
    assert "Zur Tagesarbeit" in verwaltung.text
    assert client.get("/arbeit.js").status_code == 200
    assert client.get("/style.css").status_code == 200
