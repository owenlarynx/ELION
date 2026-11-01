from pathlib import Path

from tests.hilfen import bericht_anlegen, kind_anlegen, modell_json, pruefen

PROMPT = Path(__file__).resolve().parents[1] / "prompts" / "ra_thor_wrap.md"
WRAP_FEST = (
    "You are sitting under the Ra-Thor employ loop (workspace 14.15.6).\n"
    "\n"
    "You are the optional model, not the lattice. The lattice is the Mercy-Checks. You are the sampler.\n"
    "\n"
    "Standing test: TOLC 8 — Truth, Order, Love, Compassion (zero-harm), Service, Abundance, Joy, Cosmic Harmony.\n"
    "\n"
    "PATSAGi Councils are architecture for deliberation in the monorepo — not a warranty that every answer is automatically correct.\n"
    "\n"
    "Layer 0 is an admission shell, not sampler weights.\n"
    "\n"
    "Outputs are drafts. A human reviews them before filing, sale, or public claims.\n"
    "\n"
    "inspect ≠ METR. Combined AGSi stays SURMISE. Independent of xAI. An optional Grok session is not an xAI product.\n"
    "\n"
    "Do not invent METR numbers, certifications, or a finished MMO. Powrush-MMO is a separate repo.\n"
    "\n"
    "Contact: info@Rathor.ai\n"
    "License: AG-SML v1.2 (non-revenue personal / research). Organizations license."
)


def _wrap_innen(text: str) -> str:
    zeilen = text.splitlines()
    start = zeilen.index("<<<RA_THOR_WRAP>>>")
    ende = zeilen.index("<<<ENDE_RA_THOR_WRAP>>>")
    return "\n".join(zeilen[start + 1:ende])


def test_ra_thor_wrap_bleibt_woertlich():
    assert _wrap_innen(PROMPT.read_text(encoding="utf-8")) == WRAP_FEST


def test_system_fordert_ampel_korrektur_und_hinweise(client, ollama):
    kind = kind_anlegen(client, vorname="Minka")
    bericht = bericht_anlegen(client, kind["id"], rohtext="Minka hat Brot gegessen und war ruhig.")
    ollama["inhalt"] = modell_json("gruen")
    assert pruefen(client, bericht["id"])["ampel"] == "gruen"
    nachricht = ollama["payloads"][0]["json"]["messages"]
    system = nachricht[0]["content"]
    auftrag = nachricht[1]["content"]
    assert "llama3.1" in system
    assert "ampel ist genau gruen, gelb oder rot" in system
    assert "Rechtschreibung, Grammatik und Formulierung" in system
    assert "Nichts streichen, was im Tagesbericht steht" in system
    assert "kein neues Ereignis" in system
    assert "Nicht nacherzählen, was schon klar im Text steht" in system
    assert "Ra-Thor employ loop" in auftrag
    assert "<<<RA_THOR_WRAP>>>" not in auftrag
    assert "Kontrollschritt vor der Antwort" in auftrag
    assert "Keine neue Handlung" in auftrag
    assert "Keinen Satz streichen" in auftrag
    assert "Nicht das Offensichtliche nacherzählen" in auftrag
    assert "ohne etwas wegzulassen" in auftrag
