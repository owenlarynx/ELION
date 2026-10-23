import json

import httpx
import pytest

from tests.hilfen import bericht_anlegen, kind_anlegen, modell_json, pruefen


@pytest.mark.parametrize("ampel", ["gruen", "gelb", "rot"])
def test_pruefung_setzt_ampel_aus_json(client, ollama, ampel):
    kind = kind_anlegen(client, vorname="Minka")
    bericht = bericht_anlegen(client, kind["id"], rohtext="Minka hat geschlafen und gefressen.")
    ollama["inhalt"] = modell_json(ampel, hinweise=["Essen ist genannt."], begruendung="Der Text ist brauchbar.")
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] == ampel
    assert "Hinweise:" in ergebnis["wrap_ergebnis"]
    assert ollama["payloads"][0]["json"]["format"] == "json"
    assert ollama["payloads"][0]["json"]["model"] == "llama3.1"


def test_pruefung_gruen_trotz_rot_im_wort(client, ollama):
    kind = kind_anlegen(client, vorname="Socke")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = modell_json(
        "gruen",
        hinweise=["Brot ist dokumentiert"],
        begruendung="Im Protokoll steht alles Wichtige.",
    )
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] == "gruen"


def test_pruefung_gruen_mit_umlaut(client, ollama):
    kind = kind_anlegen(client, vorname="Nala")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = modell_json("Grün")
    assert pruefen(client, bericht["id"])["ampel"] == "gruen"


def test_pruefung_json_in_markdown(client, ollama):
    kind = kind_anlegen(client, vorname="Leo")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = "```json\n" + modell_json("gelb", begruendung="Es fehlt der Abend.") + "\n```"
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] == "gelb"
    assert "Ampel: Gelb" in ergebnis["wrap_ergebnis"]


def test_pruefung_ungueltiges_json_setzt_keine_ampel(client, ollama):
    kind = kind_anlegen(client, vorname="Minka")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = "Bitte den Bericht rot markieren, das ist kein JSON und steht im Protokoll."
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] is None
    assert "keine Ampel" in ergebnis["wrap_ergebnis"]


def test_pruefung_unbekannte_ampel_setzt_keine_ampel(client, ollama):
    kind = kind_anlegen(client, vorname="Minka")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = json.dumps({
        "ampel": "orange",
        "hinweise": ["Brot erwähnen"],
        "kurzbegruendung": "Im Protokoll bleibt eine Lücke.",
    })
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] is None
    assert "keine gültige Ampel" in ergebnis["wrap_ergebnis"]


def test_pruefung_ollama_nicht_erreichbar(client, ollama):
    kind = kind_anlegen(client, vorname="Socke")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, bericht["id"])["ampel"] == "gruen"

    ollama["fehler"] = httpx.ConnectError("Connection refused")
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] is None
    assert "Ollama ist nicht erreichbar" in ergebnis["wrap_ergebnis"]
    assert "Grün" not in ergebnis["wrap_ergebnis"]


def test_prompt_enthaelt_medikation_und_profil(client, ollama):
    kind = kind_anlegen(
        client,
        vorname="Minka",
        besonderheiten="mag keine lauten Geräusche",
        dokumentationshinweise="Abendmedikation immer notieren",
    )
    aktiv = client.post("/medikamente/", json={
        "kind_id": kind["id"],
        "name": "Platzhalter-Tropfen",
        "dosierung": "1",
        "einnahmezeit": "abends",
    })
    assert aktiv.status_code == 200
    inaktiv = client.post("/medikamente/", json={"kind_id": kind["id"], "name": "Abgesetzt-Pulver"})
    assert client.delete(f"/medikamente/{inaktiv.json()['id']}").status_code == 200

    bericht = bericht_anlegen(client, kind["id"], schicht="spaet", rohtext="Die Tropfen wurden gegeben.")
    ollama["inhalt"] = modell_json("gelb", hinweise=["Uhrzeit fehlt."])
    assert pruefen(client, bericht["id"])["ampel"] == "gelb"

    prompt = ollama["payloads"][0]["json"]["messages"][1]["content"]
    assert "mag keine lauten Geräusche" in prompt
    assert "Abendmedikation immer notieren" in prompt
    assert "Platzhalter-Tropfen" in prompt
    assert "Abgesetzt-Pulver" not in prompt
    assert "Spätdienst" in prompt
    assert "Bewerte nicht das Kind" in prompt
    system = ollama["payloads"][0]["json"]["messages"][0]["content"]
    assert "nicht das Kind" in system
