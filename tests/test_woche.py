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
    assert minka_zeile["tage"][0]["ampel"] == "rot"
    assert minka_zeile["tage"][0]["hinweis"] == "Mittel und Nacht fehlen · Früh ungeprüft"
    assert minka_zeile["tage"][1]["eintraege"] == []
    assert minka_zeile["tage"][1]["ampel"] is None
    assert minka_zeile["tage"][1]["hinweis"] is None

    socke_mittwoch = daten["kinder"][1]["tage"][2]
    assert socke_mittwoch["datum"] == "2026-10-21"
    assert len(socke_mittwoch["eintraege"]) == 1
    assert socke_mittwoch["eintraege"][0]["schicht"] is None
    assert socke_mittwoch["eintraege"][0]["ampel"] is None
    assert socke_mittwoch["ampel"] is None
    assert socke_mittwoch["hinweis"] == "ungeprüft"


def test_tagesampel_ist_die_schlechteste(client, ollama):
    minka = kind_anlegen(client, vorname="Minka")
    schichten = {
        "frueh": ("gruen", "2026-10-19T07:00:00"),
        "mittel": ("gelb", "2026-10-19T12:00:00"),
        "spaet": ("gruen", "2026-10-19T16:00:00"),
        "nacht": ("rot", "2026-10-19T22:00:00"),
    }
    for schicht, (ampel, datum) in schichten.items():
        bericht = bericht_anlegen(
            client,
            minka["id"],
            datum=datum,
            schicht=schicht,
            rohtext=f"{schicht} dokumentiert.",
        )
        ollama["inhalt"] = modell_json(ampel)
        assert pruefen(client, bericht["id"])["ampel"] == ampel

    montag = client.get("/tagesberichte/woche", params={"von": "2026-10-19"}).json()
    tag = montag["kinder"][0]["tage"][0]
    assert tag["ampel"] == "rot"
    assert tag["hinweis"] is None
    assert {eintrag["schicht"] for eintrag in tag["eintraege"]} == set(schichten)

    pico = kind_anlegen(client, vorname="Pico")
    for schicht, datum in (("frueh", "2026-10-20T07:00:00"), ("spaet", "2026-10-20T16:00:00")):
        bericht = bericht_anlegen(client, pico["id"], datum=datum, schicht=schicht, rohtext="Ruhig.")
        ollama["inhalt"] = modell_json("gruen")
        assert pruefen(client, bericht["id"])["ampel"] == "gruen"
    nacht = bericht_anlegen(client, pico["id"], datum="2026-10-20T22:00:00", schicht="nacht", rohtext="Unruhig.")
    ollama["inhalt"] = modell_json("rot")
    assert pruefen(client, nacht["id"])["ampel"] == "rot"

    dienstag = client.get("/tagesberichte/woche", params={"von": "2026-10-19"}).json()
    pico_tag = next(kind for kind in dienstag["kinder"] if kind["vorname"] == "Pico")["tage"][1]
    assert pico_tag["datum"] == "2026-10-20"
    assert pico_tag["ampel"] == "rot"
    assert pico_tag["hinweis"] == "Mittel fehlt"

    socke = kind_anlegen(client, vorname="Socke")
    ohne_schicht = bericht_anlegen(client, socke["id"], datum="2026-10-21T12:00:00", rohtext="Ohne Schicht, geprüft.")
    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, ohne_schicht["id"])["ampel"] == "gruen"
    mitte = client.get("/tagesberichte/woche", params={"von": "2026-10-19"}).json()
    socke_tag = next(kind for kind in mitte["kinder"] if kind["vorname"] == "Socke")["tage"][2]
    assert socke_tag["ampel"] == "gruen"
    assert socke_tag["hinweis"] is None
