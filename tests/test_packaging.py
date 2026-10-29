from pathlib import Path

from pfade import bundle_root, ist_gepackt


def test_bundle_root_findet_pruefvorlage():
    assert ist_gepackt() is False
    assert (bundle_root() / "prompts" / "ra_thor_wrap.md").is_file()
    assert (bundle_root() / "static" / "index.html").is_file()


def test_setup_enthaelt_kein_ollama_paket():
    text = Path("packaging/elion.iss").read_text(encoding="utf-8")
    for zeile in text.splitlines():
        if zeile.strip().lower().startswith("source:"):
            assert "ollama" not in zeile.lower()
    liesmich = Path("packaging/liesmich.txt").read_text(encoding="utf-8")
    assert "nicht enthalten" in liesmich
    assert "4,7 GB" in liesmich


def test_start_selbsttest():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "elion_start_test",
        Path("packaging/elion_start.py"),
    )
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    assert modul.selbsttest() == 0
