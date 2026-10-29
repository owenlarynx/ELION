"""Startet ELION lokal und öffnet die Oberfläche.

Ollama und das Sprachmodell sind nicht Bestandteil dieser Datei.
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
if not getattr(sys, "frozen", False) and str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))

from pfade import bundle_root, daten_verzeichnis, ist_gepackt  # noqa: E402


def umgebung() -> None:
    os.environ.setdefault("ELION_PROMPT_PATH", str(bundle_root() / "prompts" / "ra_thor_wrap.md"))
    if ist_gepackt():
        datenbank = daten_verzeichnis() / "elion.db"
        os.environ.setdefault("ELION_DATABASE_URL", "sqlite:///" + datenbank.as_posix())


def selbsttest() -> int:
    umgebung()
    import main  # noqa: F401
    print("ELION bereit")
    return 0


def _wartet(url: str, thread: threading.Thread) -> bool:
    import urllib.request
    for _ in range(80):
        if not thread.is_alive():
            return False
        try:
            with urllib.request.urlopen(url, timeout=0.4) as antwort:
                if antwort.status < 500:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def haupt(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selbsttest" in argv:
        return selbsttest()
    umgebung()
    import uvicorn
    from main import app

    host = "127.0.0.1"
    port = 8000
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="info"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://{host}:{port}/"
    if not _wartet(url, thread):
        print("ELION konnte nicht starten.")
        return 1
    print("ELION läuft auf", url)
    print("Ollama ist ein separates Programm und nicht in dieser Einrichtung enthalten.")
    print("Dieses Fenster schließen beendet ELION.")
    webbrowser.open(url)
    try:
        while thread.is_alive():
            time.sleep(0.4)
    except KeyboardInterrupt:
        server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(haupt())
