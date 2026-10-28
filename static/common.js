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
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((eintrag) => eintrag.msg || "Eingabe prüfen").join(" ");
  }
  return "Anfrage fehlgeschlagen";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const antwort = await fetch(path, { ...options, headers });
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
