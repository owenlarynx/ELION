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

    nachricht = ollama["payloads"][0]
    prompt = nachricht["json"]["messages"][1]["content"]
    assert "mag keine lauten Geräusche" in prompt
    assert "Abendmedikation immer notieren" in prompt
    assert "Platzhalter-Tropfen" in prompt
    assert "Abgesetzt-Pulver" not in prompt
    assert "Spätdienst" in prompt
    assert "Bewerte nicht das Kind" in prompt
    assert "Zulässige Werte für ampel" in prompt
    assert "<<<RA_THOR_WRAP>>>" not in prompt
    assert "Hier den Ra-Thor-Wrap-Prompt einfügen" not in prompt
    assert nachricht["url"] == "http://localhost:11434/api/chat"
    system = nachricht["json"]["messages"][0]["content"]
    assert "nicht das Kind" in system


def test_prompt_pfad_und_ollama_env(client, ollama, monkeypatch, tmp_path):
    vorlage = tmp_path / "eigene.md"
    vorlage.write_text(
        "# System\n"
        "System aus Datei.\n"
        "# Auftrag\n"
        "Schicht {schicht}\n"
        "{profil}\n"
        "{medikation}\n"
        "{rohtext}\n"
        "<<<RA_THOR_WRAP>>>\n"
        "<!-- Hier den Ra-Thor-Wrap-Prompt einfügen. Dieser Hinweis wird nicht an das Modell gesendet. -->\n"
        "Auf die dokumentierte Gabe achten.\n"
        "<<<ENDE_RA_THOR_WRAP>>>\n"
        "Ampel nur als JSON.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ELION_PROMPT_PATH", str(vorlage))
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.example:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "testmodell")
    kind = kind_anlegen(client, vorname="Minka", besonderheiten="ruhig")
    bericht = bericht_anlegen(client, kind["id"], schicht="frueh", rohtext="Gabe notiert.")
    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, bericht["id"])["ampel"] == "gruen"
    gesendet = ollama["payloads"][0]
    assert gesendet["url"] == "http://ollama.example:11434/api/chat"
    assert gesendet["json"]["model"] == "testmodell"
    text = gesendet["json"]["messages"][1]["content"]
    assert "Auf die dokumentierte Gabe achten." in text
    assert "Hier den Ra-Thor-Wrap-Prompt einfügen" not in text
    assert "<<<RA_THOR_WRAP>>>" not in text
    assert "Frühdienst" in text
    assert "ruhig" in text
    assert gesendet["json"]["messages"][0]["content"] == "System aus Datei."


def test_ollama_url_mit_api_chat_wird_nicht_verdoppelt(client, ollama, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.example:11434/api/chat/")
    kind = kind_anlegen(client, vorname="Leo")
    bericht = bericht_anlegen(client, kind["id"])
    ollama["inhalt"] = modell_json("gelb")
    assert pruefen(client, bericht["id"])["ampel"] == "gelb"
    assert ollama["payloads"][0]["url"] == "http://ollama.example:11434/api/chat"


def test_pruefvorlage_ohne_auftrag_setzt_keine_ampel(client, ollama, monkeypatch, tmp_path):
    vorlage = tmp_path / "leer.md"
    vorlage.write_text("# System\nNur ein Systemtext.\n", encoding="utf-8")
    monkeypatch.setenv("ELION_PROMPT_PATH", str(vorlage))
    kind = kind_anlegen(client, vorname="Pico")
    bericht = bericht_anlegen(client, kind["id"])
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] is None
    assert "keinen Abschnitt # Auftrag" in ergebnis["wrap_ergebnis"]
    assert ollama["payloads"] == []


def test_fehlende_pruefvorlage_setzt_keine_ampel(client, ollama, monkeypatch, tmp_path):
    monkeypatch.setenv("ELION_PROMPT_PATH", str(tmp_path / "fehlt.md"))
    kind = kind_anlegen(client, vorname="Nala")
    bericht = bericht_anlegen(client, kind["id"])
    ergebnis = pruefen(client, bericht["id"])
    assert ergebnis["ampel"] is None
    assert "Prüfvorlage wurde nicht gefunden" in ergebnis["wrap_ergebnis"]
    assert ollama["payloads"] == []
