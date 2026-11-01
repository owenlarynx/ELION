function escapeHtml(wert) {
  return String(wert ?? "").replace(/[&<>"']/g, (zeichen) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[zeichen]));
}

function isoDatum(datum) {
  const jahr = datum.getFullYear();
  const monat = String(datum.getMonth() + 1).padStart(2, "0");
  const tag = String(datum.getDate()).padStart(2, "0");
  return `${jahr}-${monat}-${tag}`;
}

function heuteLokal() {
  return isoDatum(new Date());
}

function montagDerWoche(datum) {
  const tag = new Date(datum.getFullYear(), datum.getMonth(), datum.getDate());
  tag.setDate(tag.getDate() - ((tag.getDay() + 6) % 7));
  return tag;
}

function addTage(datum, tage) {
  const kopie = new Date(datum.getFullYear(), datum.getMonth(), datum.getDate());
  kopie.setDate(kopie.getDate() + tage);
  return kopie;
}

function datumAusIso(iso) {
  const [jahr, monat, tag] = iso.split("-").map(Number);
  return new Date(jahr, monat - 1, tag);
}

function fehlerAusDetail(detail) {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((eintrag) => {
      const msg = String((eintrag && eintrag.msg) || "");
      const ort = Array.isArray(eintrag && eintrag.loc)
        ? eintrag.loc.filter((teil) => teil !== "body" && teil !== "query" && teil !== "path").join(" · ")
        : "";
      if (/field required/i.test(msg)) return ort ? `Pflichtfeld fehlt: ${ort}.` : "Ein Pflichtfeld fehlt.";
      if (/valid integer|int_type|int_parsing/i.test(msg)) return ort ? `${ort} muss eine ganze Zahl sein.` : "Hier wird eine ganze Zahl erwartet.";
      if (/valid date|datetime|date_from/i.test(msg)) return "Das Datum ist ungültig.";
      if (/valid email/i.test(msg)) return "Die E-Mail-Adresse ist ungültig.";
      if (/value is not a valid|enum|literal/i.test(msg)) return ort ? `${ort} ist ungültig.` : "Ein Wert ist ungültig.";
      return ort ? `${ort}: bitte die Eingabe prüfen.` : "Bitte die Eingabe prüfen.";
    }).join(" ");
  }
  return "Die Anfrage ist fehlgeschlagen. Bitte es noch einmal versuchen.";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  let antwort;
  try {
    antwort = await fetch(path, { ...options, headers });
  } catch (_netz) {
    throw new Error("ELION ist gerade nicht erreichbar. Bitte die Seite neu laden.");
  }
  if (antwort.status === 204) return null;
  const text = await antwort.text();
  let daten = null;
  if (text) {
    try {
      daten = JSON.parse(text);
    } catch (_fehler) {
      daten = text;
    }
  }
  if (!antwort.ok) {
    throw new Error(fehlerAusDetail(daten && daten.detail));
  }
  return daten;
}

function ampelText(ampel) {
  return { gruen: "Grün", gelb: "Gelb", rot: "Rot" }[ampel] || "keine Ampel";
}

function ampelKuerzel(ampel, vorhanden) {
  if (!vorhanden) return "–";
  return { gruen: "G", gelb: "Ge", rot: "R" }[ampel] || "?";
}

function punktHtml(ampel, titel, vorhanden) {
  const klasse = !vorhanden ? "offen" : (ampel === "gruen" || ampel === "gelb" || ampel === "rot" ? ampel : "keine");
  const sicher = escapeHtml(titel);
  return `<span class="punkt ${klasse}" title="${sicher}" aria-label="${sicher}"></span>`;
}

const SCHICHTEN = [
  ["frueh", "Frühdienst", "Früh"],
  ["mittel", "Mitteldienst", "Mittel"],
  ["spaet", "Spätdienst", "Spät"],
  ["nacht", "Nachtdienst", "Nacht"],
];

function schichtName(wert) {
  const fund = SCHICHTEN.find((eintrag) => eintrag[0] === wert);
  return fund ? fund[1] : "ohne Schicht";
}

function schichtKurz(wert) {
  const fund = SCHICHTEN.find((eintrag) => eintrag[0] === wert);
  return fund ? fund[2] : "Tag";
}

function statusText(status) {
  return status === "freigegeben" ? "freigegeben" : "Entwurf";
}

function tagLang(iso) {
  return datumAusIso(iso).toLocaleDateString("de-DE", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

function monogramm(name) {
  const teile = String(name || "").trim().split(/\s+/).filter(Boolean);
  if (!teile.length) return "?";
  if (teile.length >= 2) return (teile[0][0] + teile[1][0]).toUpperCase();
  return teile[0].slice(0, 3).toUpperCase();
}

function ampelPill(ampel, vorhanden) {
  const klasse = !vorhanden ? "offen" : (ampel === "gruen" || ampel === "gelb" || ampel === "rot" ? ampel : "keine");
  const label = !vorhanden ? "Offen" : (ampel ? ampelText(ampel) : "Keine Ampel");
  return `<span class="pill ${klasse}">${punktHtml(vorhanden ? ampel : null, label, vorhanden)}<span>${escapeHtml(label)}</span></span>`;
}

function seedSatz(ergebnis) {
  if (!ergebnis || (!ergebnis.kinder_neu && !ergebnis.berichte_neu)) {
    return "Die Pilotkürzel waren schon da. Es wurde nichts Neues angelegt.";
  }
  const teile = [];
  if (ergebnis.kinder_neu) teile.push(`${ergebnis.kinder_neu} Kürzel neu`);
  if (ergebnis.kinder_vorhanden) teile.push(`${ergebnis.kinder_vorhanden} schon vorhanden`);
  if (ergebnis.berichte_neu) teile.push(`${ergebnis.berichte_neu} Beispielberichte`);
  return `${teile.join(" · ")}.`;
}

function sanft() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

const THEMEN = ["aktuell", "luna", "modern", "linux"];
const THEMA_SCHLUESSEL = "elion-thema";

function themaLesen() {
  try {
    const wert = localStorage.getItem(THEMA_SCHLUESSEL);
    if (THEMEN.includes(wert)) return wert;
  } catch (_fehler) {
    return "aktuell";
  }
  return "aktuell";
}

function themaAnwenden(name, speichern) {
  const thema = THEMEN.includes(name) ? name : "aktuell";
  if (thema === "aktuell") document.documentElement.removeAttribute("data-thema");
  else document.documentElement.setAttribute("data-thema", thema);
  if (speichern !== false) {
    try {
      localStorage.setItem(THEMA_SCHLUESSEL, thema);
    } catch (_fehler) {
      /* Darstellung gilt für diese Ansicht, auch wenn der Browser nichts speichert. */
    }
  }
  const wahl = document.getElementById("themaWahl");
  if (wahl && wahl.value !== thema) wahl.value = thema;
  return thema;
}

function themaLeiste() {
  const wahl = document.getElementById("themaWahl");
  const thema = themaLesen();
  themaAnwenden(thema, false);
  if (!wahl) return;
  wahl.addEventListener("change", () => {
    themaAnwenden(wahl.value, true);
  });
}

themaLeiste();

function frage(text, okText) {
  const dialog = document.getElementById("dialog");
  if (!dialog || typeof dialog.showModal !== "function") {
    return Promise.resolve(window.confirm(text));
  }
  document.getElementById("dialogText").textContent = text;
  const ok = document.getElementById("dialogOk");
  ok.textContent = okText || "Weiter";
  if (dialog.open) dialog.close();
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
  });
}
