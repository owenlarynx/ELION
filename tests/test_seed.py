from datetime import date

from tests.hilfen import bericht_anlegen, kind_anlegen


def test_pilot_seed_legt_kuerzel_ampeln_und_verlauf_an(client):
    erste = client.post("/seed/pilot")
    assert erste.status_code == 200, erste.text
    daten = erste.json()
    assert daten["kuerzel"] == ["AK", "MS", "LS", "BH", "AB", "EST"]
    assert daten["kinder_neu"] == 6
    assert daten["kinder_vorhanden"] == 0
    assert daten["berichte_neu"] == 9

    namen = [kind["vorname"] for kind in client.get("/kinder/").json()]
    assert namen == ["AB", "AK", "BH", "EST", "LS", "MS"]

    woche = client.get("/tagesberichte/woche").json()
    heute = date.today().isoformat()
    ampeln = {}
    for kind in woche["kinder"]:
        tag = next(eintrag for eintrag in kind["tage"] if eintrag["datum"] == heute)
        ampeln[kind["vorname"]] = tag
    assert ampeln["AK"]["ampel"] == "gruen"
    assert "Mittel ungeprüft" in ampeln["AK"]["hinweis"]
    assert ampeln["MS"]["ampel"] == "gelb"
    assert ampeln["LS"]["ampel"] == "rot"
    assert ampeln["AB"]["ampel"] == "gelb"
    assert "Früh ungeprüft" in ampeln["AB"]["hinweis"]
    assert ampeln["EST"]["ampel"] == "gruen"
    assert ampeln["BH"]["eintraege"] == []
    assert ampeln["BH"]["ampel"] is None
    assert next(kind for kind in woche["kinder"] if kind["vorname"] == "AK")["paragraph"] == "§ 34 SGB VIII"

    ms = next(kind for kind in client.get("/kinder/").json() if kind["vorname"] == "MS")
    medikamente = client.get(f"/medikamente/kind/{ms['id']}").json()
    assert [med["name"] for med in medikamente] == ["Platzhalter-Saft"]
    ak = next(kind for kind in client.get("/kinder/").json() if kind["vorname"] == "AK")
    assert client.get(f"/medikamente/kind/{ak['id']}").json() == []
    ls = next(kind for kind in client.get("/kinder/").json() if kind["vorname"] == "LS")
    assert client.get(f"/kontakte/kind/{ls['id']}").json()[0]["name"] == "Jugendamt (Beispiel)"

    ms_bericht = next(
        bericht for bericht in client.get(f"/tagesberichte/kind/{ms['id']}").json() if bericht["ampel"] == "gelb"
    )
    assert "Bitte ergänzen:" in ms_bericht["verbesserte_fassung"]
    assert ms_bericht["umformulierungen"][0]["zitat"] == "total anstrengend"
    assert ms_bericht["kurzbegruendung"]
    assert ms_bericht["pruef_quelle"] == "beispiel"

    est = next(kind for kind in client.get("/kinder/").json() if kind["vorname"] == "EST")
    est_berichte = client.get(f"/tagesberichte/kind/{est['id']}").json()
    assert len(est_berichte) == 1
    assert est_berichte[0]["status"] == "freigegeben"
    verlauf = client.get(f"/tagesberichte/{est_berichte[0]['id']}/versionen").json()
    assert len(verlauf) == 1
    assert "rumgezickt" in verlauf[0]["rohtext"]
    assert verlauf[0]["ampel"] == "gelb"

    zweite = client.post("/seed/pilot")
    assert zweite.status_code == 200, zweite.text
    nochmal = zweite.json()
    assert nochmal["kinder_neu"] == 0
    assert nochmal["kinder_vorhanden"] == 6
    assert nochmal["berichte_neu"] == 0
    assert len(client.get("/kinder/").json()) == 6


def test_seed_ueberschreibt_vorhandene_berichte_nicht(client):
    ms = kind_anlegen(client, vorname="MS", besonderheiten="eigene Notiz")
    bericht_anlegen(client, ms["id"], rohtext="Eigener Text.")
    antwort = client.post("/seed/pilot")
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["kinder_neu"] == 5
    assert daten["kinder_vorhanden"] == 1
    berichte = client.get(f"/tagesberichte/kind/{ms['id']}").json()
    assert [bericht["rohtext"] for bericht in berichte] == ["Eigener Text."]
    assert client.get(f"/kinder/{ms['id']}").json()["besonderheiten"] == "eigene Notiz"
    assert client.get(f"/medikamente/kind/{ms['id']}").json() == []
    assert len(client.get("/kinder/").json()) == 6


def test_demo_ausblenden_und_wieder_laden(client):
    erste = client.post("/seed/pilot")
    assert erste.status_code == 200
    weg = client.post("/seed/pilot/aus")
    assert weg.status_code == 200, weg.text
    assert weg.json()["ausgeblendet"] == 6
    assert client.get("/kinder/").json() == []
    wieder = client.post("/seed/pilot")
    assert wieder.status_code == 200, wieder.text
    assert wieder.json()["berichte_neu"] == 0
    assert len(client.get("/kinder/").json()) == 6
