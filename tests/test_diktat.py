import subprocess
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"
JS = STATIC / "diktat.js"
HTML = STATIC / "index.html"


def test_diktat_steuerung_ist_neben_dem_berichtstext():
    seite = HTML.read_text(encoding="utf-8")
    kopf = seite.split('id="diktieren"', 1)[0]
    assert kopf.rstrip().endswith("<button type=\"button\"")
    assert 'class="feldkopf"' in seite
    assert 'for="rohtext">Berichtstext' in seite
    assert 'aria-controls="rohtext"' in seite
    assert 'id="diktatLabel">Diktieren' in seite
    assert 'aria-pressed="false"' in seite
    assert 'id="diktatStatus"' in seite
    assert 'aria-live="polite"' in seite
    assert seite.index('id="diktieren"') < seite.index('id="rohtext"')
    assert '<script src="/diktat.js"></script>' in seite
    assert seite.index("/diktat.js") < seite.index("/arbeit.js")


def test_diktat_sprache_und_fehlermeldungen_sind_deutsch():
    quelle = JS.read_text(encoding="utf-8")
    assert 'instanz.lang = "de-DE"' in quelle
    assert "window.SpeechRecognition || window.webkitSpeechRecognition" in quelle
    for satz in (
        "Diktieren wird von diesem Gerät oder Browser nicht unterstützt.",
        "Mikrofonzugriff fehlt. Bitte das Mikrofon für diese Seite erlauben.",
        "Es ist kein Mikrofon verfügbar. Bitte ein Mikrofon anschließen.",
        "Diktat läuft …",
        "Zum Diktieren zuerst „Bearbeiten / Nachtrag“ wählen.",
    ):
        assert satz in quelle
    assert "SpeechRecognition" not in quelle.split("function diktatMeldung", 1)[1].split("function haengeErkennung", 1)[0]


def test_diktat_stoppt_vor_dem_speichern():
    quelle = (STATIC / "arbeit.js").read_text(encoding="utf-8")
    speichern = quelle.split("async function speichernJetzt()", 1)[1].split("async function pruefen()", 1)[0]
    assert "diktatStopp()" in speichern
    assert speichern.index("diktatStopp()") < speichern.index('getElementById("rohtext")')
    assert "diktatAbbrechen()" in quelle
    assert "diktatSperren(gesperrt)" in quelle


def test_diktat_logik():
    skript = Path(__file__).resolve().parent / "diktat_logik.test.js"
    fertig = subprocess.run(
        ["node", str(skript)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fertig.returncode == 0, fertig.stdout + "\n" + fertig.stderr


def test_diktat_datei_wird_ausgeliefert(client):
    seite = client.get("/")
    assert seite.status_code == 200
    assert 'id="diktieren"' in seite.text
    skript = client.get("/diktat.js")
    assert skript.status_code == 200
    assert "de-DE" in skript.text
    stil = client.get("/style.css")
    assert "diktat-knopf" in stil.text
    assert ".hoert" in stil.text
