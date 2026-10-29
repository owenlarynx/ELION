from datetime import date

from tests.hilfen import bericht_anlegen, kind_anlegen, modell_json, pruefen


def test_monat_rahmt_kalender_und_markiert_aussen(client, ollama):
    kind = kind_anlegen(client, vorname="Minka")
    frueh = bericht_anlegen(client, kind["id"], datum="2026-10-19T07:00:00", schicht="frueh", rohtext="Früh notiert.")
    spaet = bericht_anlegen(client, kind["id"], datum="2026-10-19T18:00:00", schicht="spaet", rohtext="Spät notiert.")
    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, frueh["id"])["ampel"] == "gruen"
    ollama["inhalt"] = modell_json("rot")
    assert pruefen(client, spaet["id"])["ampel"] == "rot"

    antwort = client.get("/tagesberichte/monat", params={"jahr": 2026, "monat": 10})
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["jahr"] == 2026
    assert daten["monat"] == 10
    assert daten["von"] == "2026-09-28"
    assert daten["bis"] == "2026-11-01"
    assert len(daten["kinder"]) == 1
    tage = {tag["datum"]: tag for tag in daten["kinder"][0]["tage"]}
    assert tage["2026-09-28"]["im_monat"] is False
    assert tage["2026-10-01"]["im_monat"] is True
    assert tage["2026-11-01"]["im_monat"] is False
    montag = tage["2026-10-19"]
    schichten = {eintrag["schicht"]: eintrag for eintrag in montag["eintraege"]}
    assert schichten["frueh"]["ampel"] == "gruen"
    assert schichten["spaet"]["ampel"] == "rot"
    assert montag["ampel"] == "rot"
    assert (date.fromisoformat(daten["bis"]) - date.fromisoformat(daten["von"])).days % 7 == 6


def test_monat_ungueltig(client):
    assert client.get("/tagesberichte/monat", params={"jahr": 2026, "monat": 13}).status_code == 422
