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
