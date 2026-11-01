function textAnCursor(bisher, start, ende, stueck) {
  const wort = String(stueck ?? "").replace(/\s+/g, " ").trim();
  const quelle = String(bisher ?? "");
  const von = Number.isFinite(start) ? Math.max(0, Math.min(start, quelle.length)) : quelle.length;
  const bis = Number.isFinite(ende) ? Math.max(von, Math.min(ende, quelle.length)) : von;
  if (!wort) return { text: quelle, cursor: von };
  const davor = quelle.slice(0, von);
  const danach = quelle.slice(bis);
  const leerDavor = davor.length > 0 && !/[\s([\u201e"«]$/.test(davor);
  const leerDanach = danach.length > 0 && !/^[\s,.;:!?)\]]/.test(danach);
  const einfuegung = (leerDavor ? " " : "") + wort + (leerDanach ? " " : "");
  return { text: davor + einfuegung + danach, cursor: davor.length + einfuegung.length };
}

function ergebnisTexte(results, resultIndex) {
  let fertig = "";
  let laufend = "";
  const liste = results || [];
  const start = Number.isFinite(resultIndex) ? resultIndex : 0;
  for (let i = Math.max(0, start); i < liste.length; i += 1) {
    const ergebnis = liste[i];
    const satz = ergebnis && ergebnis[0] ? String(ergebnis[0].transcript || "") : "";
    if (ergebnis && ergebnis.isFinal) fertig += satz;
    else laufend += satz;
  }
  return { fertig, laufend };
}

function diktatMeldung(code) {
  switch (code) {
    case "nicht-unterstuetzt":
    case "language-not-supported":
    case "service-not-allowed":
      return "Diktieren wird von diesem Gerät oder Browser nicht unterstützt.";
    case "not-allowed":
      return "Mikrofonzugriff fehlt. Bitte das Mikrofon für diese Seite erlauben.";
    case "audio-capture":
      return "Es ist kein Mikrofon verfügbar. Bitte ein Mikrofon anschließen.";
    case "network":
      return "Diktieren ist gerade nicht erreichbar. Bitte es später erneut versuchen.";
    case "no-speech":
      return "Nichts verstanden. Bitte erneut diktieren.";
    case "gesperrt":
      return "Zum Diktieren zuerst „Bearbeiten / Nachtrag“ wählen.";
    case "aborted":
      return "";
    default:
      return "Diktieren ist gerade nicht möglich. Bitte es erneut versuchen.";
  }
}

function haengeErkennung(instanz, hooks) {
  let zwischen = "";
  let gewollt = true;
  let versuche = 0;
  let hatteText = false;
  let gestartetUm = 0;
  let aufgeloest = false;
  let resolveFertig = function () {};
  const warten = new Promise((resolve) => {
    resolveFertig = resolve;
  });

  function fertig() {
    if (aufgeloest) return;
    aufgeloest = true;
    gewollt = false;
    resolveFertig();
    if (hooks.fertig) hooks.fertig();
  }

  function einfuegenRest() {
    const rest = zwischen;
    zwischen = "";
    if (rest && hooks.einfuegen) hooks.einfuegen(rest);
  }

  function zeigeHoeren(ausschnitt) {
    if (!gewollt) return;
    if (hooks.zustand) hooks.zustand(true, "Diktat läuft …");
    if (hooks.zwischen) hooks.zwischen(String(ausschnitt || "").replace(/\s+/g, " ").trim());
  }

  function start() {
    gestartetUm = Date.now();
    try {
      instanz.start();
      zeigeHoeren("");
    } catch (_fehler) {
      hooks.zustand(false, diktatMeldung("nicht-unterstuetzt"));
      fertig();
    }
  }

  function stopp() {
    if (aufgeloest) return;
    gewollt = false;
    if (hooks.zustand) hooks.zustand(false, "");
    try {
      instanz.stop();
    } catch (_fehler) {
      einfuegenRest();
      fertig();
      return;
    }
    const timer = setTimeout(() => {
      if (aufgeloest) return;
      einfuegenRest();
      instanz.onend = null;
      try { instanz.abort(); } catch (_fehler) {}
      fertig();
    }, 800);
    if (timer && typeof timer.unref === "function") timer.unref();
  }

  function abbrechen() {
    if (aufgeloest) return;
    zwischen = "";
    gewollt = false;
    instanz.onstart = null;
    instanz.onresult = null;
    instanz.onerror = null;
    instanz.onend = null;
    try { instanz.abort(); } catch (_fehler) {}
    if (hooks.zustand) hooks.zustand(false, "");
    fertig();
  }

  instanz.onstart = function () {
    gestartetUm = Date.now();
    zeigeHoeren("");
  };

  instanz.onresult = function (event) {
    if (aufgeloest || !event) return;
    const texte = ergebnisTexte(event.results, event.resultIndex);
    hatteText = hatteText || Boolean(texte.fertig || texte.laufend);
    versuche = 0;
    if (texte.fertig && hooks.einfuegen) {
      zwischen = "";
      hooks.einfuegen(texte.fertig);
    }
    zwischen = texte.laufend;
    zeigeHoeren(zwischen);
  };

  instanz.onerror = function (event) {
    if (aufgeloest) return;
    const code = event && event.error ? String(event.error) : "";
    if (code === "no-speech" || code === "aborted") return;
    gewollt = false;
    const rest = zwischen;
    zwischen = "";
    instanz.onend = null;
    if (rest && hooks.einfuegen) hooks.einfuegen(rest);
    if (hooks.zustand) hooks.zustand(false, diktatMeldung(code));
    try { instanz.abort(); } catch (_fehler) {}
    fertig();
  };

  instanz.onend = function () {
    if (aufgeloest) return;
    if (gewollt) {
      const kurz = !hatteText && Date.now() - gestartetUm < 500;
      hatteText = false;
      if (kurz) versuche += 1;
      else versuche = 0;
      if (versuche <= 6) {
        einfuegenRest();
        // Manche Browser beenden das Zuhören nach einer Pause. Dann neu starten.
        const neu = hooks.neuStarten || function (fn) { setTimeout(fn, 250); };
        neu(function () {
          if (aufgeloest || !gewollt) return;
          start();
        });
        return;
      }
      einfuegenRest();
      if (hooks.zustand) hooks.zustand(false, diktatMeldung("nicht-unterstuetzt"));
      if (hooks.zwischen) hooks.zwischen("");
      fertig();
      return;
    }
    einfuegenRest();
    if (hooks.zustand) hooks.zustand(false, "");
    fertig();
  };

  return { start, stopp, abbrechen, warten };
}

let diktatSteuerung = null;
let diktatAuswahl = null;

function diktatFeld() {
  return document.getElementById("rohtext");
}

function diktatAuswahlMerken() {
  const feld = diktatFeld();
  if (!feld || typeof feld.selectionStart !== "number") return;
  diktatAuswahl = { start: feld.selectionStart, ende: feld.selectionEnd };
}

function diktatPosition(feld) {
  const laenge = feld.value.length;
  if (document.activeElement === feld && typeof feld.selectionStart === "number") {
    return { start: feld.selectionStart, ende: feld.selectionEnd };
  }
  if (diktatAuswahl) {
    return {
      start: Math.max(0, Math.min(diktatAuswahl.start, laenge)),
      ende: Math.max(0, Math.min(diktatAuswahl.ende, laenge)),
    };
  }
  return { start: laenge, ende: laenge };
}

function inFeldSchreiben(feld, stueck) {
  if (!feld || feld.readOnly) return false;
  const position = diktatPosition(feld);
  const ergebnis = textAnCursor(feld.value, position.start, position.ende, stueck);
  if (ergebnis.text === feld.value) return false;
  feld.value = ergebnis.text;
  diktatAuswahl = { start: ergebnis.cursor, ende: ergebnis.cursor };
  try {
    feld.selectionStart = ergebnis.cursor;
    feld.selectionEnd = ergebnis.cursor;
  } catch (_fehler) {}
  feld.dispatchEvent(new Event("input", { bubbles: true }));
  return true;
}

function diktatUi(hoert, meldung, ausschnitt) {
  const knopf = document.getElementById("diktieren");
  const zeile = document.getElementById("diktatZeile");
  const status = document.getElementById("diktatStatus");
  const zwischen = document.getElementById("diktatZwischen");
  const label = document.getElementById("diktatLabel");
  if (!knopf) return;
  knopf.classList.toggle("hoert", Boolean(hoert));
  knopf.setAttribute("aria-pressed", hoert ? "true" : "false");
  knopf.setAttribute("aria-label", hoert ? "Diktieren beenden" : "Diktieren starten");
  if (label) label.textContent = hoert ? "Stopp" : "Diktieren";
  const text = meldung || "";
  const vorschau = String(ausschnitt || "").replace(/\s+/g, " ").trim();
  if (status && status.textContent !== text) status.textContent = text;
  if (zwischen) zwischen.textContent = vorschau ? " " + vorschau : "";
  if (zeile) {
    zeile.hidden = !text && !vorschau;
    zeile.classList.toggle("hoert", Boolean(hoert));
    zeile.classList.toggle("fehler", Boolean(text) && !hoert);
  }
}

function erkenner() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function diktatLos() {
  const feld = diktatFeld();
  if (!feld) return;
  if (feld.readOnly) {
    diktatUi(false, diktatMeldung("gesperrt"), "");
    return;
  }
  const Ctor = erkenner();
  const unsicher = typeof window.isSecureContext === "boolean" && !window.isSecureContext;
  if (!Ctor || unsicher) {
    diktatUi(false, diktatMeldung("nicht-unterstuetzt"), "");
    return;
  }
  let instanz;
  try {
    instanz = new Ctor();
  } catch (_fehler) {
    diktatUi(false, diktatMeldung("nicht-unterstuetzt"), "");
    return;
  }
  instanz.lang = "de-DE";
  instanz.continuous = true;
  instanz.interimResults = true;
  const platz = haengeErkennung(instanz, {
    einfuegen(text) { inFeldSchreiben(diktatFeld(), text); },
    zustand(hoert, meldung) { diktatUi(hoert, meldung, ""); },
    zwischen(text) { diktatVorschau(text); },
    neuStarten(fn) { setTimeout(fn, 250); },
    fertig() {
      if (diktatSteuerung === platz) diktatSteuerung = null;
    },
  });
  diktatSteuerung = platz;
  platz.start();
}

function diktatVorschau(text) {
  const vorschau = String(text || "").replace(/\s+/g, " ").trim();
  const zwischenEl = document.getElementById("diktatZwischen");
  const zeile = document.getElementById("diktatZeile");
  if (zwischenEl) zwischenEl.textContent = vorschau ? " " + vorschau : "";
  if (zeile && vorschau) zeile.hidden = false;
}

function diktatStopp() {
  if (!diktatSteuerung) return null;
  const aktuelle = diktatSteuerung;
  aktuelle.stopp();
  return aktuelle.warten;
}

function diktatAbbrechen() {
  diktatAuswahl = null;
  if (!diktatSteuerung) {
    diktatUi(false, "", "");
    return;
  }
  const aktuelle = diktatSteuerung;
  diktatSteuerung = null;
  aktuelle.abbrechen();
}

function diktatSperren(gesperrt) {
  const knopf = document.getElementById("diktieren");
  if (!knopf) return;
  if (gesperrt) diktatAbbrechen();
  knopf.disabled = Boolean(gesperrt);
  knopf.title = gesperrt
    ? "Zum Diktieren zuerst „Bearbeiten / Nachtrag“ wählen."
    : "Berichtstext auf Deutsch diktieren";
}

function diktatEinrichten() {
  const knopf = document.getElementById("diktieren");
  const feld = diktatFeld();
  if (!knopf || knopf.dataset.bereit === "1") return;
  knopf.dataset.bereit = "1";
  knopf.addEventListener("mousedown", (event) => {
    event.preventDefault();
  });
  knopf.addEventListener("click", () => {
    if (diktatSteuerung) diktatStopp();
    else diktatLos();
  });
  if (!feld) return;
  ["keyup", "mouseup", "select", "focus", "blur"].forEach((name) => {
    feld.addEventListener(name, diktatAuswahlMerken);
  });
}

if (typeof document !== "undefined") diktatEinrichten();

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    textAnCursor,
    ergebnisTexte,
    diktatMeldung,
    haengeErkennung,
  };
}
