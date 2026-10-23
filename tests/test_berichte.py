from tests.hilfen import bericht_anlegen, kind_anlegen, modell_json, pruefen


def test_bericht_mit_schicht_und_freigabe(client):
    kind = kind_anlegen(client, vorname="Nala")
    assert client.post("/tagesberichte/", json={
        "kind_id": 999,
        "datum": "2026-10-19T08:00:00",
        "rohtext": "Text",
    }).status_code == 404
    assert client.post("/tagesberichte/", json={
        "kind_id": kind["id"],
        "datum": "2026-10-19T08:00:00",
        "rohtext": "   ",
    }).status_code == 400
    assert client.post("/tagesberichte/", json={
        "kind_id": kind["id"],
        "datum": "2026-10-19T08:00:00",
        "rohtext": "Text",
        "schicht": "wochenende",
    }).status_code == 422
    assert bericht_anlegen(client, kind["id"], schicht="mittel")["schicht"] == "mittel"
    assert bericht_anlegen(client, kind["id"], schicht="nacht", datum="2026-10-19T22:00:00")["schicht"] == "nacht"

    bericht = bericht_anlegen(client, kind["id"], schicht="frueh", rohtext="Frühdienst ruhig.")
    assert bericht["schicht"] == "frueh"
    assert bericht["ampel"] is None
    assert bericht["status"] == "entwurf"

    liste = client.get(f"/tagesberichte/kind/{kind['id']}")
    assert liste.status_code == 200
    assert {eintrag["schicht"] for eintrag in liste.json()} == {"mittel", "nacht", "frueh"}
    assert any(eintrag["id"] == bericht["id"] for eintrag in liste.json())

    frei = client.post(f"/tagesberichte/{bericht['id']}/freigeben")
    assert frei.status_code == 200
    assert frei.json()["status"] == "freigegeben"
    assert frei.json()["freigegeben_am"]

    assert client.post(f"/tagesberichte/{bericht['id']}/pruefen").status_code == 409
    unveraendert = client.put(
        f"/tagesberichte/{bericht['id']}",
        json={"rohtext": "Frühdienst ruhig.", "von": "Wird nicht archiviert"},
    )
    assert unveraendert.status_code == 200
    assert unveraendert.json()["status"] == "freigegeben"
    assert client.get(f"/tagesberichte/{bericht['id']}/versionen").json() == []


def test_bericht_aendern_setzt_pruefung_zurueck(client, ollama):
    kind = kind_anlegen(client, vorname="Leo")
    bericht = bericht_anlegen(client, kind["id"], rohtext="Leo hat gefressen.")
    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, bericht["id"])["ampel"] == "gruen"

    geaendert = client.put(
        f"/tagesberichte/{bericht['id']}",
        json={"rohtext": "Leo hat am Nachmittag geschlafen."},
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["ampel"] is None
    assert geaendert.json()["wrap_ergebnis"] is None
    assert geaendert.json()["rohtext"] == "Leo hat am Nachmittag geschlafen."
    assert client.get(f"/tagesberichte/{bericht['id']}/versionen").json() == []


def test_nachtrag_archiviert_freigabe_und_fordert_neue_pruefung(client, ollama):
    kind = kind_anlegen(client, vorname="Socke")
    bericht = bericht_anlegen(client, kind["id"], schicht="frueh", rohtext="Erste Fassung.")
    ollama["inhalt"] = modell_json("gelb", begruendung="Essen fehlt.")
    assert pruefen(client, bericht["id"])["ampel"] == "gelb"
    assert client.post(f"/tagesberichte/{bericht['id']}/freigeben").status_code == 200

    erster = client.put(
        f"/tagesberichte/{bericht['id']}",
        json={"rohtext": "Zweite Fassung mit Essen.", "von": " " + ("A" * 90)},
    )
    assert erster.status_code == 200, erster.text
    assert erster.json()["status"] == "entwurf"
    assert erster.json()["ampel"] is None
    assert erster.json()["wrap_ergebnis"] is None
    assert erster.json()["freigegeben_am"] is None
    assert erster.json()["freigegeben_von"] is None
    assert erster.json()["rohtext"] == "Zweite Fassung mit Essen."
    assert erster.json()["schicht"] == "frueh"

    versionen = client.get(f"/tagesberichte/{bericht['id']}/versionen")
    assert versionen.status_code == 200
    assert len(versionen.json()) == 1
    alt = versionen.json()[0]
    assert alt["rohtext"] == "Erste Fassung."
    assert alt["schicht"] == "frueh"
    assert alt["ampel"] == "gelb"
    assert "Essen fehlt." in alt["wrap_ergebnis"]
    assert alt["geaendert_von"] == "A" * 80
    assert alt["archiviert_am"]
    assert client.get("/tagesberichte/999/versionen").status_code == 404

    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, bericht["id"])["ampel"] == "gruen"
    assert client.post(f"/tagesberichte/{bericht['id']}/freigeben").status_code == 200

    zweiter = client.put(
        f"/tagesberichte/{bericht['id']}",
        json={"schicht": "nacht", "von": "Nachtdienst"},
    )
    assert zweiter.status_code == 200, zweiter.text
    assert zweiter.json()["status"] == "entwurf"
    assert zweiter.json()["schicht"] == "nacht"
    assert zweiter.json()["ampel"] is None
    assert zweiter.json()["rohtext"] == "Zweite Fassung mit Essen."

    verlauf = client.get(f"/tagesberichte/{bericht['id']}/versionen").json()
    assert [eintrag["rohtext"] for eintrag in verlauf] == [
        "Zweite Fassung mit Essen.",
        "Erste Fassung.",
    ]
    assert verlauf[0]["schicht"] == "frueh"
    assert verlauf[0]["ampel"] == "gruen"
    assert verlauf[0]["geaendert_von"] == "Nachtdienst"
    assert verlauf[1]["ampel"] == "gelb"
