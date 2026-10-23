from tests.hilfen import kind_anlegen


def test_datenbankpfad_ist_konfiguriert():
    from database import engine
    assert "elion-test-" in str(engine.url)


def test_kind_anlegen_listen_aendern_deaktivieren(client):
    angelegt = kind_anlegen(
        client,
        vorname="Minka",
        nachname=None,
        besonderheiten="mag keine lauten Geräusche",
        dokumentationshinweise="Abendmedikation notieren",
    )
    assert angelegt["vorname"] == "Minka"
    assert angelegt["aktiv"] is True

    liste = client.get("/kinder/")
    assert liste.status_code == 200
    assert [kind["vorname"] for kind in liste.json()] == ["Minka"]

    einzeln = client.get(f"/kinder/{angelegt['id']}")
    assert einzeln.status_code == 200
    assert einzeln.json()["dokumentationshinweise"] == "Abendmedikation notieren"

    geaendert = client.put(
        f"/kinder/{angelegt['id']}",
        json={"besonderheiten": "schläft gerne am Fenster"},
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["besonderheiten"] == "schläft gerne am Fenster"

    weg = client.delete(f"/kinder/{angelegt['id']}")
    assert weg.status_code == 200
    assert weg.json()["aktiv"] is False
    assert client.get("/kinder/").json() == []

    alle = client.get("/kinder/", params={"inkl_inaktiv": True})
    assert len(alle.json()) == 1

    wieder = client.put(f"/kinder/{angelegt['id']}", json={"aktiv": True})
    assert wieder.json()["aktiv"] is True
    assert len(client.get("/kinder/").json()) == 1


def test_kind_nicht_gefunden(client):
    assert client.get("/kinder/999").status_code == 404
    assert client.put("/kinder/999", json={"vorname": "Socke"}).status_code == 404


def test_medikament_und_kontakt_crud(client):
    kind = kind_anlegen(client, vorname="Socke")
    assert client.post("/medikamente/", json={"kind_id": 999, "name": "Tropfen"}).status_code == 404

    med = client.post("/medikamente/", json={
        "kind_id": kind["id"],
        "name": "Platzhalter-Tropfen",
        "dosierung": "1",
        "einnahmezeit": "abends",
        "hinweis": "nur Platzhalter",
    })
    assert med.status_code == 200, med.text
    med_id = med.json()["id"]

    geaendert = client.put(f"/medikamente/{med_id}", json={"dosierung": "2"})
    assert geaendert.json()["dosierung"] == "2"
    assert client.get(f"/medikamente/kind/{kind['id']}").json()[0]["name"] == "Platzhalter-Tropfen"

    assert client.delete(f"/medikamente/{med_id}").json()["aktiv"] is False
    assert client.get(f"/medikamente/kind/{kind['id']}").json() == []
    assert len(client.get(f"/medikamente/kind/{kind['id']}", params={"inkl_inaktiv": True}).json()) == 1
    assert client.put(f"/medikamente/{med_id}", json={"aktiv": True}).json()["aktiv"] is True

    assert client.post("/kontakte/", json={"kind_id": 999, "typ": "sonstige", "name": "Tierarztpraxis"}).status_code == 404
    kontakt = client.post("/kontakte/", json={
        "kind_id": kind["id"],
        "typ": "sonstige",
        "name": "Praxis Samtpfote",
        "telefon": "0123",
    })
    assert kontakt.status_code == 200, kontakt.text
    kontakt_id = kontakt.json()["id"]
    assert client.put(f"/kontakte/{kontakt_id}", json={"telefon": "456"}).json()["telefon"] == "456"
    assert client.get(f"/kontakte/kind/{kind['id']}").json()[0]["name"] == "Praxis Samtpfote"
    assert client.delete(f"/kontakte/{kontakt_id}").json()["aktiv"] is False
    assert client.get(f"/kontakte/kind/{kind['id']}").json() == []
