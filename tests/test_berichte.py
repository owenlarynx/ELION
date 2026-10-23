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
        "schicht": "nacht",
    }).status_code == 422

    bericht = bericht_anlegen(client, kind["id"], schicht="frueh", rohtext="Frühdienst ruhig.")
    assert bericht["schicht"] == "frueh"
    assert bericht["ampel"] is None
    assert bericht["status"] == "entwurf"

    liste = client.get(f"/tagesberichte/kind/{kind['id']}")
    assert liste.status_code == 200
    assert liste.json()[0]["id"] == bericht["id"]

    frei = client.post(f"/tagesberichte/{bericht['id']}/freigeben")
    assert frei.status_code == 200
    assert frei.json()["status"] == "freigegeben"
    assert frei.json()["freigegeben_am"]

    gesperrt = client.put(f"/tagesberichte/{bericht['id']}", json={"rohtext": "Änderung"})
    assert gesperrt.status_code == 409
    assert client.post(f"/tagesberichte/{bericht['id']}/pruefen").status_code == 409


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
