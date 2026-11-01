const assert = require("assert");
const { textAnCursor, ergebnisTexte, diktatMeldung, haengeErkennung } = require("../static/diktat.js");

function gleich(ist, soll, name) {
  assert.deepStrictEqual(ist, soll, name);
}

function testTextAnCursor() {
  gleich(
    textAnCursor("Schon getippt.", 14, 14, " Und ruhig"),
    { text: "Schon getippt. Und ruhig", cursor: 24 },
    "hängt an und lässt den bisherigen Text stehen",
  );
  gleich(
    textAnCursor("AK hat geschlafen.", 3, 3, "heute"),
    { text: "AK heute hat geschlafen.", cursor: 9 },
    "fügt an der Schreibmarke ein",
  );
  gleich(
    textAnCursor("AK XX hier", 3, 5, "war"),
    { text: "AK war hier", cursor: 6 },
    "ersetzt nur die Auswahl",
  );
  const leer = textAnCursor("Bleibt.", 7, 7, "   ");
  gleich(leer, { text: "Bleibt.", cursor: 7 }, "leere Erkennung ändert nichts");
  gleich(
    textAnCursor("(Hinweis)", 1, 1, "AK"),
    { text: "(AK Hinweis)", cursor: 4 },
    "kein Leerzeichen nach der öffnenden Klammer",
  );
  gleich(
    textAnCursor("", 0, 0, "  AK hat gegessen.  "),
    { text: "AK hat gegessen.", cursor: 16 },
    "leeres Feld übernimmt den Satz",
  );
}

function testErgebnisTexte() {
  const ergebnisse = [
    { isFinal: true, 0: { transcript: "Alt" } },
    { isFinal: true, 0: { transcript: " Neu" } },
    { isFinal: false, 0: { transcript: " noch" } },
  ];
  gleich(ergebnisTexte(ergebnisse, 1), { fertig: " Neu", laufend: " noch" }, "frühere Ergebnisse bleiben außen vor");
  gleich(ergebnisTexte(null, 0), { fertig: "", laufend: "" }, "ohne Ergebnis keine Texte");
}

function testMeldungen() {
  const faelle = [
    ["not-allowed", "Mikrofonzugriff fehlt"],
    ["nicht-unterstuetzt", "nicht unterstützt"],
    ["language-not-supported", "nicht unterstützt"],
    ["service-not-allowed", "nicht unterstützt"],
    ["audio-capture", "kein Mikrofon"],
    ["network", "nicht erreichbar"],
    ["no-speech", "Nichts verstanden"],
    ["gesperrt", "Bearbeiten / Nachtrag"],
    ["sonst", "nicht möglich"],
  ];
  for (const [code, teil] of faelle) {
    const text = diktatMeldung(code);
    assert.ok(text.includes(teil), code + " -> " + text);
    assert.ok(!/speech|webkit|api|permission|denied|error/i.test(text), text);
  }
  gleich(diktatMeldung("aborted"), "", "Abbruch bleibt still");
}

function instanz() {
  return {
    start() {
      if (this.onstart) this.onstart();
    },
    stop() {
      if (this.onend) this.onend();
    },
    abort() {},
  };
}

function testFinaleEinfuegen() {
  const feld = { text: "Schon getippt.", cursor: 14 };
  const erkannt = instanz();
  const zustaende = [];
  const steuerung = haengeErkennung(erkannt, {
    einfuegen(stueck) {
      const ergebnis = textAnCursor(feld.text, feld.cursor, feld.cursor, stueck);
      feld.text = ergebnis.text;
      feld.cursor = ergebnis.cursor;
    },
    zustand(hoert, meldung) { zustaende.push([hoert, meldung]); },
    zwischen() {},
    neuStarten(fn) { setTimeout(fn, 0); },
  });
  steuerung.start();
  erkannt.onresult({
    resultIndex: 0,
    results: [{ isFinal: true, 0: { transcript: " Und ruhig" } }],
  });
  steuerung.stopp();
  gleich(feld.text, "Schon getippt. Und ruhig", "finaler Text wird angehängt");
  return new Promise((resolve) => {
    setTimeout(() => {
      gleich(feld.text, "Schon getippt. Und ruhig", "Stopp fügt denselben Satz nicht noch einmal ein");
      assert.ok(zustaende.some((eintrag) => eintrag[0] && eintrag[1] === "Diktat läuft …"), "Zuhör-Zustand");
      resolve();
    }, 850);
  });
}

function testZwischenBeimStopp() {
  const eingefuegt = [];
  const erkannt = instanz();
  const steuerung = haengeErkennung(erkannt, {
    einfuegen(text) { eingefuegt.push(text); },
    zustand() {},
    zwischen() {},
    neuStarten(fn) { setTimeout(fn, 0); },
  });
  steuerung.start();
  erkannt.onresult({
    resultIndex: 0,
    results: [{ isFinal: false, 0: { transcript: "müde" } }],
  });
  assert.deepStrictEqual(eingefuegt, [], "Zwischentext steht noch nicht im Feld");
  steuerung.stopp();
  assert.deepStrictEqual(eingefuegt, ["müde"], "Stopp übernimmt den gehörten Text");
}

function testAbbrechenVerwirftZwischen() {
  const eingefuegt = [];
  const erkannt = instanz();
  const steuerung = haengeErkennung(erkannt, {
    einfuegen(text) { eingefuegt.push(text); },
    zustand() {},
    zwischen() {},
    neuStarten(fn) { setTimeout(fn, 0); },
  });
  steuerung.start();
  erkannt.onresult({
    resultIndex: 0,
    results: [{ isFinal: false, 0: { transcript: "weg" } }],
  });
  steuerung.abbrechen();
  assert.deepStrictEqual(eingefuegt, [], "Wechsel der Schicht verwirft nur den offenen Zwischentext");
}

function testMikrofonVerweigert() {
  const erkannt = {
    start() {
      if (this.onstart) this.onstart();
      if (this.onerror) this.onerror({ error: "not-allowed" });
    },
    stop() {},
    abort() { throw new Error("abbruch"); },
  };
  let meldung = "";
  assert.doesNotThrow(() => {
    const steuerung = haengeErkennung(erkannt, {
      einfuegen() { throw new Error("nichts einfügen"); },
      zustand(_hoert, text) { meldung = text; },
      zwischen() {},
      neuStarten(fn) { setTimeout(fn, 0); },
    });
    steuerung.start();
  });
  assert.ok(meldung.includes("Mikrofonzugriff fehlt"), meldung);
}

function testNichtUnterstuetzt() {
  const erkannt = {
    start() { throw new Error("fehlt"); },
    stop() {},
    abort() {},
  };
  let meldung = "";
  const steuerung = haengeErkennung(erkannt, {
    einfuegen() {},
    zustand(_hoert, text) { meldung = text; },
    zwischen() {},
    neuStarten(fn) { setTimeout(fn, 0); },
  });
  assert.doesNotThrow(() => steuerung.start());
  assert.ok(meldung.includes("nicht unterstützt"), meldung);
}

function testKurzerAbbruchEndet() {
  let starts = 0;
  const erkannt = {
    start() {
      starts += 1;
      if (this.onstart) this.onstart();
      if (this.onend) this.onend();
    },
    stop() {},
    abort() {},
  };
  return new Promise((resolve, reject) => {
    const frist = setTimeout(() => reject(new Error("Zuhören endet nicht")), 3000);
    haengeErkennung(erkannt, {
      einfuegen() {},
      zustand(hoert, meldung) {
        if (!hoert && meldung.includes("nicht unterstützt")) {
          clearTimeout(frist);
          assert.ok(starts >= 2 && starts < 12, "Startversuche: " + starts);
          resolve();
        }
      },
      zwischen() {},
      neuStarten(fn) { setTimeout(fn, 0); },
    }).start();
  });
}

Promise.all([
  testTextAnCursor(),
  testErgebnisTexte(),
  testMeldungen(),
  testFinaleEinfuegen(),
  testZwischenBeimStopp(),
  testAbbrechenVerwirftZwischen(),
  testMikrofonVerweigert(),
  testNichtUnterstuetzt(),
  testKurzerAbbruchEndet(),
]).then(() => {
  console.log("diktat ok");
}).catch((fehler) => {
  console.error(fehler);
  process.exit(1);
});
