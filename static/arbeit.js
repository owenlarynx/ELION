let kindId = null;
let berichtId = null;
let berichtStatus = null;
let berichteCache = [];
let gespeicherterText = "";
let nachtragModus = false;
let verlaufLauf = 0;
let wochenStart = montagDerWoche(new Date());
let heuteLauf = 0;
let wocheLauf = 0;
let ansichtsDatum = heuteLokal();
let herkunft = "heute";
let aktuelleSchicht = "frueh";
let naechsteSchicht = null;
let verbesserteFassung = "";

const STUNDE = { frueh: "07", mittel: "13", spaet: "18", nacht: "22" };

function zeige(name) {
  for (const ansicht of ["heute", "bericht", "woche"]) {
    document.getElementById("ansicht-" + ansicht).hidden = ansicht !== name;
  }
  const markiert = name === "bericht" ? herkunft : name;
  document.querySelectorAll("nav a[data-ansicht]").forEach((link) => {
    link.classList.toggle("aktiv", link.dataset.ansicht === markiert);
  });
  document.title = { heute: "ELION – Heute", bericht: "ELION – Bericht", woche: "ELION – Woche" }[name] || "ELION";
  adresseSetzen(name);
  if (name === "heute") ladeHeute();
  if (name === "woche") ladeWoche();
}

function adresseSetzen(name) {
  const url = new URL(location.href);
  if (name === "bericht" && kindId) {
    url.searchParams.set("kind", String(kindId));
    url.searchParams.set("datum", ansichtsDatum);
    if (aktuelleSchicht) url.searchParams.set("schicht", aktuelleSchicht);
    else url.searchParams.set("schicht", "");
  } else {
    url.searchParams.delete("kind");
    url.searchParams.delete("datum");
    url.searchParams.delete("schicht");
  }
  url.hash = name;
  history.replaceState(null, "", url.pathname + url.search + "#" + name);
}

function tagesklasse(tag) {
  const eintraege = tag.eintraege || [];
  if (!eintraege.length) return "offen";
  if (tag.ampel === "gruen" || tag.ampel === "gelb" || tag.ampel === "rot") return tag.ampel;
  return "keine";
}

function tagesdarstellung(tag, name) {
  const eintraege = tag.eintraege || [];
  const vorhanden = eintraege.length > 0;
  const datum = datumAusIso(tag.datum).toLocaleDateString("de-DE");
  const stand = vorhanden ? ampelText(tag.ampel) : "offen";
  const zusatz = tag.hinweis ? ` · ${tag.hinweis}` : "";
  return {
    klasse: tagesklasse(tag),
    kuerzel: ampelKuerzel(vorhanden ? tag.ampel : null, vorhanden),
    hinweis: tag.hinweis || "",
    titel: `${name}, ${datum}: ${stand}${zusatz}`,
    vorhanden,
  };
}

function bilanzZeichnen(kinder, heute) {
  const zaehler = { gruen: 0, gelb: 0, rot: 0, keine: 0, offen: 0 };
  for (const kind of kinder) {
    const tag = kind.tage.find((eintrag) => eintrag.datum === heute) || { eintraege: [] };
    zaehler[tagesklasse(tag)] += 1;
  }
  const zeilen = [
    ["gruen", "Grün"],
    ["gelb", "Gelb"],
    ["rot", "Rot"],
    ["offen", "offen"],
  ];
  if (zaehler.keine) zeilen.splice(3, 0, ["keine", "ohne Ampel"]);
  document.getElementById("bilanz").innerHTML = zeilen.map(([klasse, label]) => {
    const titel = `${zaehler[klasse]} ${label}`;
    return `<li>${punktHtml(klasse === "offen" || klasse === "keine" ? null : klasse, titel, klasse !== "offen")}<span>${zaehler[klasse]} ${escapeHtml(label)}</span></li>`;
  }).join("");
}

function schichtChipHeute(kind, tag, wert, kurz) {
  const eintrag = (tag.eintraege || []).find((bericht) => (bericht.schicht || "") === wert);
  const vorhanden = Boolean(eintrag);
  const titel = `${kurz}: ${vorhanden ? ampelText(eintrag.ampel) : "offen"}`;
  const kuerzel = ampelKuerzel(vorhanden ? eintrag.ampel : null, vorhanden);
  return `<button type="button" class="chip" data-kind="${kind.id}" data-datum="${escapeHtml(tag.datum)}" data-schicht="${escapeHtml(wert)}" title="${escapeHtml(titel)}">
    <span class="chip-name">${escapeHtml(kurz)}</span>
    <span class="chip-stand">${punktHtml(vorhanden ? eintrag.ampel : null, titel, vorhanden)}<span>${escapeHtml(kuerzel)}</span></span>
  </button>`;
}

function zustandHtml(titel, detail, aktion) {
  const knopf = aktion
    ? `<div class="aktionen"><button type="button" class="sekundaer" data-aktion="${aktion}">Erneut laden</button></div>`
    : "";
  const klein = detail ? `<p class="leis">${escapeHtml(detail)}</p>` : "";
  return `<div class="zustand"><p>${escapeHtml(titel)}</p>${klein}${knopf}</div>`;
}

async function ladeHeute() {
  const lauf = ++heuteLauf;
  const ziel = document.getElementById("heuteKarten");
  document.getElementById("heuteDatum").textContent = tagLang(heuteLokal());
  ziel.innerHTML = zustandHtml("Die Übersicht wird geladen.");
  try {
    const montag = isoDatum(montagDerWoche(new Date()));
    const woche = await api("/tagesberichte/woche?von=" + montag);
    if (lauf !== heuteLauf) return;
    const heute = heuteLokal();
    bilanzZeichnen(woche.kinder, heute);
    if (!woche.kinder.length) {
      document.getElementById("bilanz").innerHTML = "";
      ziel.innerHTML = `<div class="zustand">
        <p>Noch keine Kinder für die Tagesarbeit.</p>
        <p class="leis">In der Verwaltung lassen sich Platzhalter anlegen. Für einen ersten Durchgang gibt es sechs Kürzel mit Beispielberichten.</p>
        <div class="aktionen">
          <button type="button" data-aktion="pilot">Pilotdaten laden</button>
          <a class="button sekundaer" href="/verwaltung.html">Zur Verwaltung</a>
        </div>
      </div>`;
      return;
    }
    ziel.innerHTML = woche.kinder.map((kind) => {
      const tag = kind.tage.find((eintrag) => eintrag.datum === heute) || { datum: heute, eintraege: [], ampel: null, hinweis: null };
      const name = `${kind.vorname} ${kind.nachname || ""}`.trim();
      const darstellung = tagesdarstellung(tag, name);
      const zeichen = (kind.nachname || "").trim() ? monogramm(name) : "";
      const rechtsgrund = kind.paragraph ? kind.paragraph : "";
      const hinweis = darstellung.hinweis
        ? `<span class="leis">${escapeHtml(darstellung.hinweis)}</span>`
        : "";
      const chips = SCHICHTEN.map((schicht) => schichtChipHeute(kind, tag, schicht[0], schicht[2])).join("");
      return `<article class="schichtzeile ist-${darstellung.klasse}">
        <button type="button" class="nameknopf" data-kind="${kind.id}" data-datum="${escapeHtml(tag.datum)}">
          ${zeichen ? `<span class="monogramm${zeichen.length > 2 ? " lang" : ""}" aria-hidden="true">${escapeHtml(zeichen)}</span>` : ""}
          <span class="nameblock">
            <strong>${escapeHtml(name)}</strong>
            ${rechtsgrund ? `<span class="leis">${escapeHtml(rechtsgrund)}</span>` : ""}
          </span>
        </button>
        <p class="tagesstand">${ampelPill(darstellung.vorhanden ? tag.ampel : null, darstellung.vorhanden)}${hinweis}</p>
        <div class="chips">${chips}</div>
      </article>`;
    }).join("");
  } catch (fehler) {
    if (lauf !== heuteLauf) return;
    document.getElementById("bilanz").innerHTML = "";
    ziel.innerHTML = zustandHtml("Das hat gerade nicht geklappt.", fehler.message, "neu");
  }
}

function berichteDesTages() {
  return berichteCache.filter((bericht) => String(bericht.datum).slice(0, 10) === ansichtsDatum);
}

function berichtFuer(schicht) {
  const treffer = berichteDesTages().filter((bericht) => (bericht.schicht || "") === schicht);
  treffer.sort((a, b) => b.id - a.id);
  return treffer[0] || null;
}

function schichtKnopf(wert, kurz) {
  const bericht = berichtFuer(wert);
  const vorhanden = Boolean(bericht);
  const titel = `${kurz}: ${vorhanden ? ampelText(bericht.ampel) : "offen"}`;
  const aktiv = aktuelleSchicht === wert ? " aktiv" : "";
  const voll = wert === "" ? " voll" : "";
  const kuerzel = ampelKuerzel(vorhanden ? bericht.ampel : null, vorhanden);
  return `<button type="button" class="schichtwahl${aktiv}${voll}" data-schicht="${escapeHtml(wert)}" aria-pressed="${aktuelleSchicht === wert ? "true" : "false"}">
    <span class="chip-name">${escapeHtml(kurz)}</span>
    <span class="chip-stand">${punktHtml(vorhanden ? bericht.ampel : null, titel, vorhanden)}<span>${escapeHtml(kuerzel)}</span></span>
  </button>`;
}

function schichtLeisteZeichnen() {
  const teile = SCHICHTEN.map((schicht) => schichtKnopf(schicht[0], schicht[2]));
  if (berichtFuer("") || aktuelleSchicht === "") teile.push(schichtKnopf("", "ohne Schicht"));
  document.getElementById("schichtLeiste").innerHTML = teile.join("");
}

function formularSperren() {
  const freigegeben = berichtStatus === "freigegeben";
  const gesperrt = freigegeben && !nachtragModus;
  const speichern = document.getElementById("speichern");
  const pruefen = document.getElementById("pruefen");
  const freigeben = document.getElementById("freigeben");
  document.getElementById("rohtext").readOnly = gesperrt;
  speichern.disabled = gesperrt;
  speichern.textContent = nachtragModus ? "Nachtrag speichern" : "Speichern Entwurf";
  pruefen.disabled = !berichtId || freigegeben;
  pruefen.textContent = "Prüfung starten";
  pruefen.title = !berichtId
    ? "Zuerst den Entwurf speichern."
    : (freigegeben ? "Zuerst einen Nachtrag speichern." : "Prüfung starten");
  freigeben.disabled = !berichtId || freigegeben;
  freigeben.title = !berichtId
    ? "Zuerst den Entwurf speichern."
    : (freigegeben ? "Der Bericht ist freigegeben." : "Bericht freigeben");
  document.getElementById("nachtrag").hidden = !freigegeben || nachtragModus;
  document.getElementById("nameFeld").hidden = !nachtragModus;
}

function platzhalterMarkup(text) {
  const re = /\[Bitte ergänzen:[^\]]+\]/gi;
  let html = "";
  let letzte = 0;
  const quelle = String(text ?? "");
  for (const fund of quelle.matchAll(re)) {
    html += escapeHtml(quelle.slice(letzte, fund.index));
    html += `<mark class="platzhalter">${escapeHtml(fund[0])}</mark>`;
    letzte = fund.index + fund[0].length;
  }
  return html + escapeHtml(quelle.slice(letzte));
}

function spiegelAktualisieren() {
  const feld = document.getElementById("rohtext");
  const spiegel = document.getElementById("rohtextSpiegel");
  spiegel.innerHTML = platzhalterMarkup(feld.value) + "\n";
  spiegel.style.height = feld.offsetHeight + "px";
  spiegel.style.width = feld.offsetWidth + "px";
  spiegel.scrollTop = feld.scrollTop;
}

function tokenisiere(text) {
  return String(text ?? "").match(/\[Bitte ergänzen:[^\]]+\]|\s+|\S+/gi) || [];
}

function tokenHtml(token, art) {
  const platzhalter = /^\[Bitte ergänzen:/i.test(token);
  const innen = platzhalter ? `<mark class="platzhalter">${escapeHtml(token)}</mark>` : escapeHtml(token);
  if (art === "ins") return `<ins>${innen}</ins>`;
  if (art === "del") return `<del>${escapeHtml(token)}</del>`;
  return innen;
}

function diffFassung(alt, neu) {
  const a = tokenisiere(alt);
  const b = tokenisiere(neu);
  if (!a.length && !b.length) return { alt: "", neu: "" };
  if (a.length > 450 || b.length > 450) {
    return { alt: escapeHtml(alt), neu: platzhalterMarkup(neu) };
  }
  const n = a.length;
  const m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  let i = 0;
  let j = 0;
  let altHtml = "";
  let neuHtml = "";
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      altHtml += tokenHtml(a[i]);
      neuHtml += tokenHtml(b[j]);
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      altHtml += tokenHtml(a[i], "del");
      i += 1;
    } else {
      neuHtml += tokenHtml(b[j], "ins");
      j += 1;
    }
  }
  while (i < n) {
    altHtml += tokenHtml(a[i], "del");
    i += 1;
  }
  while (j < m) {
    neuHtml += tokenHtml(b[j], "ins");
    j += 1;
  }
  return { alt: altHtml, neu: neuHtml };
}

function pruefungAnzeigen(bericht) {
  const ziel = document.getElementById("pruefung");
  verbesserteFassung = "";
  if (!bericht || !bericht.wrap_ergebnis) {
    ziel.innerHTML = `<section class="pruefpanel ruhig"><p class="leis">Noch keine Prüfung. Nach dem Speichern kann die Ampel gesetzt werden.</p></section>`;
    return;
  }
  const hinweise = Array.isArray(bericht.hinweise) ? bericht.hinweise : [];
  const paare = Array.isArray(bericht.umformulierungen) ? bericht.umformulierungen : [];
  const fassung = bericht.verbesserte_fassung || "";
  const begruendung = bericht.kurzbegruendung || "";
  const klasse = bericht.ampel || "keine";
  if (!bericht.ampel && !begruendung && !hinweise.length && !fassung && !paare.length) {
    ziel.innerHTML = `<section class="pruefpanel ruhig">
      <p class="ampelzeile">${ampelPill(null, true)}</p>
      <p>Es wurde keine Ampel gesetzt. Die Dokumentation bleibt unverändert.</p>
      <div class="prueftext">${escapeHtml(bericht.wrap_ergebnis)}</div>
    </section>`;
    return;
  }
  verbesserteFassung = fassung;
  const paarliste = paare.length
    ? `<h3>Wertend → pädagogisch</h3><ul class="paarliste">${paare.map((paar) => `<li><span class="zitat">„${escapeHtml(paar.zitat)}“</span> <span class="pfeil">→</span> <span class="vorschlag">${escapeHtml(paar.vorschlag)}</span></li>`).join("")}</ul>`
    : "";
  const liste = hinweise.length
    ? `<h3>Hinweise</h3><ul class="hinweisliste">${hinweise.map((hinweis) => `<li>${escapeHtml(hinweis)}</li>`).join("")}</ul>`
    : "";
  let vergleich = "";
  if (fassung) {
    const gleich = fassung.trim() === String(bericht.rohtext || "").trim();
    const koerper = gleich
      ? `<div class="vergleichtext">${platzhalterMarkup(fassung)}</div>`
      : (() => {
          const diff = diffFassung(bericht.rohtext || "", fassung);
          return `<div class="vergleich">
            <div><p class="label">Bisher</p><div class="vergleichtext">${diff.alt}</div></div>
            <div><p class="label">Vorschlag</p><div class="vergleichtext">${diff.neu}</div></div>
          </div>`;
        })();
    vergleich = `<h3>Überarbeitete Fassung</h3>
      ${koerper}
      <div class="aktionen">
        <button type="button" data-aktion="uebernehmen">Übernehmen</button>
        <button type="button" class="sekundaer" data-aktion="anpassen">Anpassen</button>
        <button type="button" class="textlink" data-aktion="uebernehmen-pruefen">Übernehmen und neu prüfen</button>
      </div>
      <div class="anpassen" id="anpassenKasten" hidden>
        <label for="anpassenText">Fassung anpassen
          <textarea id="anpassenText"></textarea>
        </label>
        <div class="aktionen">
          <button type="button" data-aktion="anpassen-uebernehmen">Angepasste Fassung übernehmen</button>
          <button type="button" class="sekundaer" data-aktion="anpassen-schliessen">Schließen</button>
        </div>
      </div>`;
  }
  ziel.innerHTML = `<section class="pruefpanel ${klasse}">
    <p class="ampelzeile">${ampelPill(bericht.ampel, true)}</p>
    ${begruendung ? `<h3>Fazit</h3><p>${escapeHtml(begruendung)}</p>` : ""}
    ${paarliste}
    ${liste}
    ${vergleich}
  </section>`;
}

function textInBericht(text, meldung) {
  if (!text) return;
  if (berichtStatus === "freigegeben" && !nachtragModus) {
    nachtragModus = true;
    formularSperren();
  }
  const feld = document.getElementById("rohtext");
  feld.value = text;
  spiegelAktualisieren();
  feld.focus();
  feld.scrollIntoView({ block: "center", behavior: sanft() });
  setzeHinweis(meldung);
}

function fassungEinsetzen() {
  textInBericht(
    verbesserteFassung,
    "Vorschlag steht im Bericht. Bitte lesen und als Entwurf speichern.",
  );
}

function statusSetzen(bericht, hatVerlauf) {
  const status = document.getElementById("berichtStatus");
  let text = "neu";
  let klasse = "status";
  if (bericht && bericht.status === "freigegeben") {
    text = "freigegeben";
    klasse = "status freigegeben";
  } else if (bericht && hatVerlauf) {
    text = "Entwurf nach Nachtrag";
    klasse = "status nachtrag";
  } else if (bericht) {
    text = "Entwurf";
  }
  status.textContent = text;
  status.className = klasse;
}

async function ladeVerlauf(id) {
  const lauf = ++verlaufLauf;
  const ziel = document.getElementById("verlauf");
  if (!id) {
    ziel.innerHTML = "<p class=\"leis\">Noch kein Verlauf. Eine freigegebene Fassung bleibt nach einer Änderung hier stehen.</p>";
    statusSetzen(berichtId ? { status: berichtStatus } : null, false);
    return;
  }
  try {
    const versionen = await api("/tagesberichte/" + id + "/versionen");
    if (lauf !== verlaufLauf) return;
    statusSetzen(berichtFuer(aktuelleSchicht), versionen.length > 0);
    if (!versionen.length) {
      ziel.innerHTML = "<p class=\"leis\">Noch kein Nachtrag. Eine freigegebene Fassung bleibt nach einer Änderung hier stehen.</p>";
      return;
    }
    ziel.innerHTML = `<ul class="verlauf">${versionen.map((version) => {
      const wann = version.archiviert_am ? new Date(version.archiviert_am).toLocaleString("de-DE") : "";
      const wer = version.geaendert_von || version.freigegeben_von || "Name nicht erfasst";
      const pruefung = version.wrap_ergebnis
        ? `<details><summary>Damalige Prüfung</summary><div class="prueftext">${escapeHtml(version.wrap_ergebnis)}</div></details>`
        : "";
      return `<li>
        <span class="leis">${escapeHtml(wann)} · ${escapeHtml(wer)} · ${escapeHtml(schichtName(version.schicht || ""))}</span>
        <div>${ampelPill(version.ampel, true)}</div>
        <div class="alttext">${escapeHtml(version.rohtext)}</div>
        ${pruefung}
      </li>`;
    }).join("")}</ul>`;
  } catch (fehler) {
    if (lauf !== verlaufLauf) return;
    ziel.innerHTML = zustandHtml("Der Verlauf ist gerade nicht erreichbar.", fehler.message);
  }
}

function slotInFormular(schicht) {
  aktuelleSchicht = schicht;
  nachtragModus = false;
  document.getElementById("nachtragVon").value = "";
  const bericht = berichtFuer(schicht);
  berichtId = bericht ? bericht.id : null;
  berichtStatus = bericht ? bericht.status : null;
  const text = bericht ? bericht.rohtext : "";
  document.getElementById("rohtext").value = text;
  gespeicherterText = text;
  spiegelAktualisieren();
  statusSetzen(bericht, false);
  pruefungAnzeigen(bericht);
  formularSperren();
  schichtLeisteZeichnen();
  const schichtLabel = schichtName(schicht);
  document.getElementById("berichtDatum").textContent = `${schichtLabel} · ${tagLang(ansichtsDatum)}`;
  ladeVerlauf(berichtId);
  if (!document.getElementById("ansicht-bericht").hidden) adresseSetzen("bericht");
}

function startSchicht() {
  if (naechsteSchicht != null) {
    const gewaehlt = naechsteSchicht;
    naechsteSchicht = null;
    if (SCHICHTEN.some((schicht) => schicht[0] === gewaehlt) || gewaehlt === "") return gewaehlt;
  }
  const rang = { gruen: 1, gelb: 2, rot: 3 };
  let gewaehlt = null;
  let bester = 0;
  for (const schicht of SCHICHTEN) {
    const bericht = berichtFuer(schicht[0]);
    if (!bericht || !bericht.ampel || !rang[bericht.ampel]) continue;
    if (rang[bericht.ampel] > bester) {
      bester = rang[bericht.ampel];
      gewaehlt = schicht[0];
    }
  }
  if (gewaehlt) return gewaehlt;
  const erste = SCHICHTEN.find((schicht) => berichtFuer(schicht[0]));
  if (erste) return erste[0];
  if (berichtFuer("")) return "";
  return "frueh";
}

async function ladeBericht() {
  const [kind, medikamente, kontakte, berichte] = await Promise.all([
    api("/kinder/" + kindId),
    api("/medikamente/kind/" + kindId),
    api("/kontakte/kind/" + kindId),
    api("/tagesberichte/kind/" + kindId),
  ]);
  berichteCache = berichte;
  const name = `${kind.vorname} ${kind.nachname || ""}`.trim();
  document.getElementById("kindName").textContent = name;
  document.getElementById("berichtTag").value = ansichtsDatum;
  const profilFeld = (titel, text) => `<div class="profilfeld"><span class="label">${escapeHtml(titel)}</span><div>${escapeHtml(text || "keine Angaben")}</div></div>`;
  const profil = [
    kind.paragraph ? profilFeld("Rechtsgrundlage", kind.paragraph) : "",
    profilFeld("Besonderheiten", kind.besonderheiten),
    profilFeld("Dokumentationshinweise", kind.dokumentationshinweise),
  ].filter(Boolean).join("");
  const medListe = medikamente.length
    ? `<ul class="stammliste">${medikamente.map((med) => `<li class="stammkarte">
        <strong>${escapeHtml(med.name)}</strong>
        <span class="feldzeile"><span class="label">Dosierung</span> ${escapeHtml(med.dosierung || "—")}</span>
        <span class="feldzeile"><span class="label">Einnahmezeit</span> ${escapeHtml(med.einnahmezeit || "—")}</span>
        ${med.hinweis ? `<span class="feldzeile"><span class="label">Hinweis</span> ${escapeHtml(med.hinweis)}</span>` : ""}
      </li>`).join("")}</ul>`
    : "<p class=\"leis\">Keine Medikation hinterlegt. Die Prüfung spricht Medikamente dann nicht an.</p>";
  const typLabel = { eltern: "Eltern", asd: "Jugendamt", vormund: "Vormund", sonstige: "Sonstige" };
  const kontaktListe = kontakte.length
    ? `<ul class="stammliste">${kontakte.map((kontakt) => `<li class="stammkarte">
        <strong>${escapeHtml(kontakt.name)}</strong>
        <span class="feldzeile"><span class="label">Art</span> ${escapeHtml(typLabel[kontakt.typ] || kontakt.typ)}</span>
        <span class="feldzeile"><span class="label">Telefon</span> ${escapeHtml(kontakt.telefon || "—")}</span>
        <span class="feldzeile"><span class="label">E-Mail</span> ${escapeHtml(kontakt.email || "—")}</span>
        ${kontakt.hinweis ? `<span class="feldzeile"><span class="label">Hinweis</span> ${escapeHtml(kontakt.hinweis)}</span>` : ""}
      </li>`).join("")}</ul>`
    : "<p class=\"leis\">Keine Kontakte hinterlegt.</p>";
  document.getElementById("profilKarte").innerHTML = `<h2>Kindprofil</h2><div class="profilfelder">${profil}</div><h3>Medikamente</h3>${medListe}<h3>Kontakte</h3>${kontaktListe}<p class="leis">Liegt nur auf diesem Rechner.</p><p><a class="textlink" href="/verwaltung.html">In der Verwaltung bearbeiten</a></p>`;
  slotInFormular(startSchicht());
}

async function oeffneKind(id, datum, von, schicht) {
  if (!id) return;
  kindId = id;
  ansichtsDatum = datum || heuteLokal();
  herkunft = von === "woche" ? "woche" : "heute";
  naechsteSchicht = schicht == null ? null : schicht;
  document.getElementById("zurueck").textContent = herkunft === "woche" ? "Zur Woche" : "Zur Übersicht";
  document.getElementById("formHinweis").textContent = "";
  try {
    await ladeBericht();
    zeige("bericht");
  } catch (fehler) {
    const ziel = herkunft === "woche" ? "wocheStatus" : "heuteStatus";
    document.getElementById(ziel).textContent = fehler.message;
  }
}

function setzeHinweis(text) {
  document.getElementById("formHinweis").textContent = text;
}

async function ungespeichertVerwerfen(text) {
  const berichtSichtbar = !document.getElementById("ansicht-bericht").hidden;
  if (!berichtSichtbar) return true;
  if (document.getElementById("rohtext").value === gespeicherterText) return true;
  return frage(text, "Verwerfen");
}

async function speichern() {
  const rohtext = document.getElementById("rohtext").value.trim();
  if (!rohtext) {
    setzeHinweis("Bitte einen Text eingeben.");
    return false;
  }
  if (berichtStatus === "freigegeben" && !nachtragModus) {
    setzeHinweis("Für eine Änderung zuerst „Bearbeiten / Nachtrag“ wählen.");
    return false;
  }
  const schicht = aktuelleSchicht;
  const von = document.getElementById("nachtragVon").value.trim();
  const warNachtrag = nachtragModus;
  const knopf = document.getElementById("speichern");
  knopf.disabled = true;
  try {
    let gespeichert = null;
    if (berichtId) {
      const koerper = { rohtext };
      if (von) koerper.von = von;
      gespeichert = await api("/tagesberichte/" + berichtId, {
        method: "PUT",
        body: JSON.stringify(koerper),
      });
    } else {
      await api("/tagesberichte/", {
        method: "POST",
        body: JSON.stringify({
          kind_id: kindId,
          datum: `${ansichtsDatum}T${STUNDE[schicht] || "12"}:00:00`,
          rohtext,
          schicht: schicht || null,
        }),
      });
    }
    if (warNachtrag && gespeichert && gespeichert.status === "freigegeben") {
      setzeHinweis("Keine Änderung. Die Freigabe bleibt bestehen.");
    } else if (warNachtrag) {
      setzeHinweis("Nachtrag gespeichert. Die alte Ampel ist veraltet. Bitte erneut prüfen und freigeben.");
    } else {
      setzeHinweis("Entwurf gespeichert.");
    }
    await ladeBericht();
    slotInFormular(schicht || "");
    return true;
  } catch (fehler) {
    setzeHinweis(fehler.message);
    formularSperren();
    return false;
  }
}

async function pruefen() {
  if (!berichtId) {
    setzeHinweis("Bitte den Bericht zuerst speichern.");
    return;
  }
  const knopf = document.getElementById("pruefen");
  knopf.disabled = true;
  knopf.textContent = "Prüfung läuft …";
  setzeHinweis("Prüfung läuft. Das kann einen Moment dauern.");
  try {
    await api("/tagesberichte/" + berichtId + "/pruefen", { method: "POST" });
    const schicht = aktuelleSchicht;
    await ladeBericht();
    slotInFormular(schicht);
    setzeHinweis("Prüfung abgeschlossen.");
  } catch (fehler) {
    setzeHinweis(fehler.message);
    formularSperren();
  }
}

async function freigeben() {
  if (!berichtId) {
    setzeHinweis("Bitte den Bericht zuerst speichern.");
    return;
  }
  const text = document.getElementById("rohtext").value;
  const mitPlatzhalter = /\[Bitte ergänzen:[^\]]+\]/i.test(text);
  const ohneAmpel = !(berichtFuer(aktuelleSchicht) || {}).ampel;
  let wortlaut = "Bericht freigeben? Ein späterer Nachtrag bleibt im Verlauf sichtbar.";
  if (mitPlatzhalter) wortlaut = "Im Bericht stehen noch Platzhalter [Bitte ergänzen: …]. " + wortlaut;
  if (ohneAmpel) wortlaut = "Die Ampel ist noch leer. " + wortlaut;
  if (!(await frage(wortlaut, "Freigeben"))) return;
  try {
    await api("/tagesberichte/" + berichtId + "/freigeben", { method: "POST" });
    const schicht = aktuelleSchicht;
    await ladeBericht();
    slotInFormular(schicht);
    setzeHinweis("Freigegeben.");
  } catch (fehler) {
    setzeHinweis(fehler.message);
  }
}

async function uebernehmenUndPruefen() {
  if (!verbesserteFassung) return;
  fassungEinsetzen();
  const ok = await speichern();
  if (ok) await pruefen();
}

function wechsleSchicht(neu) {
  if (neu === aktuelleSchicht) return;
  const weiter = () => {
    slotInFormular(neu);
    setzeHinweis("");
  };
  if (document.getElementById("rohtext").value === gespeicherterText) {
    weiter();
    return;
  }
  frage("Ungespeicherte Änderungen verwerfen und die andere Schicht öffnen?", "Verwerfen").then((ja) => {
    if (ja) weiter();
  });
}

async function wechsleDatum(neu) {
  if (!neu || neu === ansichtsDatum) {
    document.getElementById("berichtTag").value = ansichtsDatum;
    return;
  }
  if (!(await ungespeichertVerwerfen("Ungespeicherte Änderungen verwerfen und den anderen Tag öffnen?"))) {
    document.getElementById("berichtTag").value = ansichtsDatum;
    return;
  }
  const bisher = ansichtsDatum;
  ansichtsDatum = neu;
  naechsteSchicht = aktuelleSchicht;
  try {
    await ladeBericht();
    setzeHinweis("");
  } catch (fehler) {
    ansichtsDatum = bisher;
    document.getElementById("berichtTag").value = bisher;
    setzeHinweis(fehler.message);
  }
}

async function pilotLaden() {
  const ok = await frage(
    "Pilotkürzel und Beispielberichte anlegen? Vorhandene Kürzel und ihre Berichte bleiben unverändert.",
    "Anlegen",
  );
  if (!ok) return;
  const status = document.getElementById("heuteStatus");
  status.textContent = "Pilotdaten werden angelegt …";
  try {
    const ergebnis = await api("/seed/pilot", { method: "POST" });
    await ladeHeute();
    status.textContent = seedSatz(ergebnis);
  } catch (fehler) {
    status.textContent = fehler.message;
  }
}

document.getElementById("schichtLeiste").addEventListener("click", (event) => {
  const knopf = event.target.closest("[data-schicht]");
  if (knopf) wechsleSchicht(knopf.dataset.schicht);
});

document.getElementById("heuteKarten").addEventListener("click", (event) => {
  const aktion = event.target.closest("[data-aktion]");
  if (aktion && aktion.dataset.aktion === "pilot") {
    pilotLaden();
    return;
  }
  if (aktion && aktion.dataset.aktion === "neu") {
    ladeHeute();
    return;
  }
  const knopf = event.target.closest("[data-kind]");
  if (!knopf) return;
  const schicht = Object.prototype.hasOwnProperty.call(knopf.dataset, "schicht") ? knopf.dataset.schicht : null;
  oeffneKind(Number(knopf.dataset.kind), knopf.dataset.datum, "heute", schicht);
});

document.querySelector("nav").addEventListener("click", async (event) => {
  const link = event.target.closest("a[data-ansicht]");
  if (!link) return;
  event.preventDefault();
  if (!(await ungespeichertVerwerfen("Ungespeicherte Änderungen verwerfen?"))) return;
  zeige(link.dataset.ansicht);
});

document.getElementById("zurueck").addEventListener("click", async () => {
  if (!(await ungespeichertVerwerfen("Ungespeicherte Änderungen verwerfen und zurückgehen?"))) return;
  zeige(herkunft);
});

document.getElementById("rohtext").addEventListener("input", spiegelAktualisieren);
document.getElementById("rohtext").addEventListener("scroll", spiegelAktualisieren);
if (window.ResizeObserver) {
  new ResizeObserver(spiegelAktualisieren).observe(document.getElementById("rohtext"));
}

document.getElementById("pruefung").addEventListener("click", (event) => {
  const knopf = event.target.closest("[data-aktion]");
  if (!knopf) return;
  if (knopf.dataset.aktion === "uebernehmen") fassungEinsetzen();
  if (knopf.dataset.aktion === "uebernehmen-pruefen") uebernehmenUndPruefen();
  if (knopf.dataset.aktion === "anpassen") {
    const kasten = document.getElementById("anpassenKasten");
    const feld = document.getElementById("anpassenText");
    if (!kasten || !feld) return;
    if (!feld.value) feld.value = verbesserteFassung;
    kasten.hidden = false;
    feld.focus();
  }
  if (knopf.dataset.aktion === "anpassen-schliessen") {
    const kasten = document.getElementById("anpassenKasten");
    if (kasten) kasten.hidden = true;
  }
  if (knopf.dataset.aktion === "anpassen-uebernehmen") {
    const feld = document.getElementById("anpassenText");
    const text = feld ? feld.value.trim() : "";
    if (!text) {
      setzeHinweis("Die angepasste Fassung ist leer.");
      return;
    }
    textInBericht(text, "Angepasste Fassung steht im Bericht. Bitte als Entwurf speichern.");
  }
});

document.getElementById("speichern").addEventListener("click", speichern);
document.getElementById("pruefen").addEventListener("click", pruefen);
document.getElementById("freigeben").addEventListener("click", freigeben);
document.getElementById("nachtrag").addEventListener("click", () => {
  nachtragModus = true;
  formularSperren();
  document.getElementById("rohtext").focus();
  setzeHinweis("Die bisherige Fassung bleibt im Verlauf. Nach dem Speichern sind Ampel und Freigabe veraltet und müssen neu gesetzt werden.");
});
document.getElementById("berichtTag").addEventListener("change", () => {
  wechsleDatum(document.getElementById("berichtTag").value);
});

document.getElementById("wocheZurueck").addEventListener("click", () => {
  wochenStart = addTage(wochenStart, -7);
  ladeWoche();
});
document.getElementById("wocheVor").addEventListener("click", () => {
  wochenStart = addTage(wochenStart, 7);
  ladeWoche();
});
document.getElementById("wocheDiese").addEventListener("click", () => {
  wochenStart = montagDerWoche(new Date());
  ladeWoche();
});

function eintragDerSchicht(tag, wert) {
  return (tag.eintraege || []).find((bericht) => (bericht.schicht || "") === wert) || null;
}

function schichtFokus(kind, tag, wert, kurz, neben) {
  const eintrag = eintragDerSchicht(tag, wert);
  const vorhanden = Boolean(eintrag);
  const titel = `${kurz}: ${vorhanden ? ampelText(eintrag.ampel) : "offen"}`;
  const klasse = neben ? "nebenknopf" : "fokusknopf";
  return `<button type="button" class="${klasse}" data-kind="${kind.id}" data-datum="${escapeHtml(tag.datum)}" data-schicht="${escapeHtml(wert)}" title="${escapeHtml(titel)}">
    <span>${escapeHtml(kurz)}</span>
    ${punktHtml(vorhanden ? eintrag.ampel : null, titel, vorhanden)}
    <span class="kuerzel">${escapeHtml(ampelKuerzel(vorhanden ? eintrag.ampel : null, vorhanden))}</span>
  </button>`;
}

function schichtOhne(kind, tag) {
  const eintrag = eintragDerSchicht(tag, "");
  if (!eintrag) return "";
  return schichtFokus(kind, tag, "", "Tag", true);
}

function fokusNotiz(tag) {
  const teile = [];
  for (const [wert, kurz] of [["frueh", "Früh"], ["spaet", "Spät"]]) {
    const eintrag = eintragDerSchicht(tag, wert);
    if (eintrag && !eintrag.ampel) teile.push(`${kurz} ungeprüft`);
  }
  return teile.join(" · ");
}

async function ladeWoche() {
  const lauf = ++wocheLauf;
  const label = document.getElementById("wochenLabel");
  const sonntag = addTage(wochenStart, 6);
  const format = (datum) => datum.toLocaleDateString("de-DE", { day: "numeric", month: "long" });
  label.textContent = `${format(wochenStart)} – ${format(sonntag)} ${sonntag.getFullYear()}`;
  const diese = isoDatum(montagDerWoche(new Date()));
  document.getElementById("wocheDiese").disabled = isoDatum(wochenStart) === diese;
  const koerper = document.getElementById("wochenKörper");
  koerper.innerHTML = `<tr><td colspan="8">Die Woche wird geladen …</td></tr>`;
  try {
    const woche = await api("/tagesberichte/woche?von=" + isoDatum(wochenStart));
    if (lauf !== wocheLauf) return;
    const heute = heuteLokal();
    const kopf = woche.kinder[0] ? woche.kinder[0].tage : [];
    const tage = kopf.length ? kopf : Array.from({ length: 7 }, (_, index) => ({ datum: isoDatum(addTage(wochenStart, index)) }));
    document.getElementById("wochenKopf").innerHTML = `<tr><th scope="col">Kind</th>${tage.map((tag) => {
      const text = datumAusIso(tag.datum).toLocaleDateString("de-DE", { weekday: "short", day: "numeric", month: "numeric" });
      return `<th scope="col" class="${tag.datum === heute ? "heute" : ""}">${escapeHtml(text)}</th>`;
    }).join("")}</tr>`;
    if (!woche.kinder.length) {
      koerper.innerHTML = `<tr><td colspan="8"><div class="zustand"><p>Noch keine Kinder in dieser Woche.</p><p><a href="/verwaltung.html">Zur Verwaltung</a></p></div></td></tr>`;
      return;
    }
    const nameDatum = (() => {
      if (heute >= isoDatum(wochenStart) && heute <= isoDatum(sonntag)) return heute;
      return isoDatum(wochenStart);
    })();
    koerper.innerHTML = woche.kinder.map((kind) => {
      const name = `${kind.vorname} ${kind.nachname || ""}`.trim();
        const zellen = kind.tage.map((tag) => {
            const darstellung = tagesdarstellung(tag, name);
            const notiz = fokusNotiz(tag);
            return `<td class="${tag.datum === heute ? "heute" : ""}"><div class="wochenzelle" title="${escapeHtml(darstellung.titel)}">
              <div class="wochenfokus">
                ${schichtFokus(kind, tag, "frueh", "Früh")}
                ${schichtFokus(kind, tag, "spaet", "Spät")}
              </div>
              <div class="wocheneben">
                ${schichtFokus(kind, tag, "mittel", "Mittel", true)}
                ${schichtFokus(kind, tag, "nacht", "Nacht", true)}
                ${schichtOhne(kind, tag)}
              </div>
              ${notiz ? `<span class="tageshinweis">${escapeHtml(notiz)}</span>` : ""}
            </div></td>`;
          }).join("");
      return `<tr><th scope="row"><button type="button" class="link" data-kind="${kind.id}" data-datum="${escapeHtml(nameDatum)}">${escapeHtml(name)}</button></th>${zellen}</tr>`;
    }).join("");
  } catch (fehler) {
    if (lauf !== wocheLauf) return;
    koerper.innerHTML = `<tr><td colspan="8">${zustandHtml("Die Woche ist gerade nicht erreichbar.", fehler.message, "neu")}</td></tr>`;
  }
}

document.getElementById("wochenKörper").addEventListener("click", (event) => {
  const aktion = event.target.closest("[data-aktion]");
  if (aktion && aktion.dataset.aktion === "neu") {
    ladeWoche();
    return;
  }
  const knopf = event.target.closest("[data-kind]");
  if (!knopf) return;
  const schicht = Object.prototype.hasOwnProperty.call(knopf.dataset, "schicht") ? knopf.dataset.schicht : null;
  oeffneKind(Number(knopf.dataset.kind), knopf.dataset.datum, "woche", schicht);
});

const parameter = new URLSearchParams(location.search);
const kindParameter = parameter.get("kind");
if (kindParameter) {
  const schicht = parameter.has("schicht") ? parameter.get("schicht") : null;
  oeffneKind(Number(kindParameter), parameter.get("datum") || undefined, "heute", schicht);
} else if (location.hash === "#woche") {
  zeige("woche");
} else {
  zeige("heute");
}
