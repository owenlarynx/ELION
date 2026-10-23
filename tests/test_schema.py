from sqlalchemy import create_engine, text

from database import ensure_schema


def test_ensure_schema_ergaenzt_alte_sqlite(tmp_path):
    pfad = tmp_path / "alt.db"
    alt = create_engine("sqlite:///" + str(pfad))
    with alt.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE tagesberichte (
                id INTEGER PRIMARY KEY,
                kind_id INTEGER,
                datum DATETIME,
                rohtext TEXT,
                wrap_ergebnis TEXT,
                ampel VARCHAR,
                status VARCHAR,
                erstellt_von VARCHAR,
                freigegeben_von VARCHAR,
                erstellt_am DATETIME,
                freigegeben_am DATETIME
            )
            """
        ))
        conn.execute(text(
            "INSERT INTO tagesberichte (id, kind_id, datum, rohtext, status) "
            "VALUES (1, 1, '2026-10-19 08:00:00', 'Alter Text', 'freigegeben')"
        ))
        conn.execute(text(
            """
            CREATE TABLE bericht_versionen (
                id INTEGER PRIMARY KEY,
                bericht_id INTEGER,
                rohtext TEXT,
                schicht VARCHAR,
                ampel VARCHAR,
                wrap_ergebnis TEXT,
                freigegeben_am DATETIME,
                freigegeben_von VARCHAR,
                geaendert_von VARCHAR,
                archiviert_am DATETIME
            )
            """
        ))
    ensure_schema(alt)
    with alt.begin() as conn:
        spalten = {row[1] for row in conn.execute(text("PRAGMA table_info(tagesberichte)"))}
        tabellen = {
            row[0]
            for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))
        }
        rohtext = conn.execute(text("SELECT rohtext FROM tagesberichte WHERE id = 1")).scalar()
        schicht = conn.execute(text("SELECT schicht FROM tagesberichte WHERE id = 1")).scalar()
        versionsspalten = {row[1] for row in conn.execute(text("PRAGMA table_info(bericht_versionen)"))}
    alt.dispose()
    assert "schicht" in spalten
    assert "verbesserte_fassung" in spalten
    assert "pruef_meta" in spalten
    assert "bericht_versionen" in tabellen
    assert "verbesserte_fassung" in versionsspalten
    assert "pruef_meta" in versionsspalten
    assert rohtext == "Alter Text"
    assert schicht is None
