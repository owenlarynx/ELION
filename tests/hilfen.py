import json


def kind_anlegen(client, vorname="Minka", **extra):
    daten = {"vorname": vorname}
    daten.update(extra)
    antwort = client.post("/kinder/", json=daten)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def bericht_anlegen(client, kind_id, rohtext="Der Tag verlief ruhig.", datum="2026-10-19T08:00:00", schicht=None):
    daten = {"kind_id": kind_id, "datum": datum, "rohtext": rohtext}
    if schicht is not None:
        daten["schicht"] = schicht
    antwort = client.post("/tagesberichte/", json=daten)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def pruefen(client, bericht_id):
    antwort = client.post(f"/tagesberichte/{bericht_id}/pruefen")
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def modell_json(ampel, hinweise=None, begruendung="Die Dokumentation ist nachvollziehbar.", fassung=None):
    daten = {"ampel": ampel, "hinweise": hinweise or [], "kurzbegruendung": begruendung}
    if fassung is not None:
        daten["verbesserte_fassung"] = fassung
    return json.dumps(daten, ensure_ascii=False)
