from datetime import date

from tests.hilfen import bericht_anlegen, kind_anlegen, modell_json, pruefen


def test_woche_ohne_von_beginnt_montag(client):
    daten = client.get("/tagesberichte/woche")
    assert daten.status_code == 200, daten.text
    von = date.fromisoformat(daten.json()["von"])
    bis = date.fromisoformat(daten.json()["bis"])
    assert von.weekday() == 0
    assert (bis - von).days == 6
    assert daten.json()["kinder"] == []


def test_wochenuebersicht_mit_schichten(client, ollama):
    minka = kind_anlegen(client, vorname="Minka")
    socke = kind_anlegen(client, vorname="Socke")
    nala = kind_anlegen(client, vorname="Nala")

    erster = bericht_anlegen(client, minka["id"], datum="2026-10-19T08:00:00", schicht="frueh", rohtext="Erster Frühtext.")
    zweiter = bericht_anlegen(client, minka["id"], datum="2026-10-19T09:00:00", schicht="frueh", rohtext="Zweiter Frühtext.")
    spaet = bericht_anlegen(client, minka["id"], datum="2026-10-19T18:00:00", schicht="spaet", rohtext="Spät wach.")
    bericht_anlegen(client, minka["id"], datum="2026-10-18T12:00:00", rohtext="Vorwoche.")
    bericht_anlegen(client, minka["id"], datum="2026-10-26T12:00:00", rohtext="Folgewoche.")
    bericht_anlegen(client, socke["id"], datum="2026-10-21T12:00:00", rohtext="Ohne Schicht.")
    bericht_anlegen(client, nala["id"], datum="2026-10-20T12:00:00", rohtext="Wird deaktiviert.")
    assert client.delete(f"/kinder/{nala['id']}").status_code == 200

    ollama["inhalt"] = modell_json("rot", hinweise=["Mitteilung fehlt."])
    assert pruefen(client, spaet["id"])["ampel"] == "rot"

    antwort = client.get("/tagesberichte/woche", params={"von": "2026-10-19"})
    assert antwort.status_code == 200, antwort.text
    daten = antwort.json()
    assert daten["von"] == "2026-10-19"
    assert daten["bis"] == "2026-10-25"
    namen = [kind["vorname"] for kind in daten["kinder"]]
    assert namen == ["Minka", "Socke"]

    minka_zeile = daten["kinder"][0]
    assert len(minka_zeile["tage"]) == 7
    assert minka_zeile["tage"][0]["datum"] == "2026-10-19"
    eintraege = {eintrag["schicht"]: eintrag for eintrag in minka_zeile["tage"][0]["eintraege"]}
    assert set(eintraege) == {"frueh", "spaet"}
    assert eintraege["frueh"]["bericht_id"] == zweiter["id"]
    assert eintraege["frueh"]["bericht_id"] != erster["id"]
    assert eintraege["spaet"]["ampel"] == "rot"
    assert minka_zeile["tage"][1]["eintraege"] == []

    socke_mittwoch = daten["kinder"][1]["tage"][2]
    assert socke_mittwoch["datum"] == "2026-10-21"
    assert len(socke_mittwoch["eintraege"]) == 1
    assert socke_mittwoch["eintraege"][0]["schicht"] is None
    assert socke_mittwoch["eintraege"][0]["ampel"] is None
