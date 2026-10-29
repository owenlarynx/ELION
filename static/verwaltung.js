let kinder = [];
let kindEditId = null;
let medEditId = null;
let kontaktEditId = null;

const meldung = document.getElementById("meldung");
function hinweis(text) { meldung.textContent = text || ""; }

function formularDaten(form) {
  const daten = {};
  for (const element of form.elements) {
    if (!element.name) continue;
    const wert = element.value.trim();
    daten[element.name] = wert || null;
  }
  return daten;
}

function formFuellen(form, daten) {
  for (const element of form.elements) {
    if (!element.name) continue;
    element.value = daten[element.name] || "";
  }
}

function formLeeren(form) {
  form.reset();
}

function kindModus(bearbeitung) {
  kindEditId = bearbeitung ? kindEditId : null;
  document.getElementById("kindFormTitel").textContent = bearbeitung ? "Kind bearbeiten" : "Kind anlegen";
  document.getElementById("kindSpeichern").textContent = bearbeitung ? "Änderungen speichern" : "Anlegen";
  document.getElementById("kindAbbrechen").hidden = !bearbeitung;
}

async function ladeKinder() {
  kinder = await api("/kinder/?inkl_inaktiv=true");
  const liste = document.getElementById("kinderListe");
  if (!kinder.length) {
    liste.innerHTML = "<li>Noch keine Kinder.</li>";
  } else {
    liste.innerHTML = kinder.map((kind) => {
      const name = `${kind.vorname} ${kind.nachname || ""}`.trim();
      const aktion = kind.aktiv
        ? `<button type="button" class="leise" data-aktion="aus" data-id="${kind.id}">Deaktivieren</button>`
        : `<button type="button" class="sekundaer" data-aktion="an" data-id="${kind.id}">Aktivieren</button>`;
      const bericht = kind.aktiv
        ? `<a class="button sekundaer" href="/?kind=${kind.id}#bericht">Bericht öffnen</a>`
        : "";
      return `<li class="${kind.aktiv ? "" : "inaktiv"}">
        <div>
          <strong>${escapeHtml(name)}</strong>
          ${kind.aktiv ? "" : " <span class=\"pill keine\">inaktiv</span>"}
          ${kind.paragraph ? `<br><span class="leis">${escapeHtml(kind.paragraph)}</span>` : ""}
          ${kind.besonderheiten ? `<br><span class="leis">${escapeHtml(kind.besonderheiten)}</span>` : ""}
        </div>
        <div class="aktionen">
          ${bericht}
          <button type="button" class="sekundaer" data-aktion="bearbeiten" data-id="${kind.id}">Bearbeiten</button>
          ${aktion}
        </div>
      </li>`;
    }).join("");
  }
  const auswahl = document.getElementById("bezugsKind");
  const bisher = auswahl.value;
  const aktive = kinder.filter((kind) => kind.aktiv);
  auswahl.innerHTML = aktive.length
    ? aktive.map((kind) => `<option value="${kind.id}">${escapeHtml(`${kind.vorname} ${kind.nachname || ""}`.trim())}</option>`).join("")
    : `<option value="">Kein aktives Kind</option>`;
  if (bisher && aktive.some((kind) => String(kind.id) === bisher)) auswahl.value = bisher;
  await ladeBezug();
}

async function ladeBezug() {
  const kindId = document.getElementById("bezugsKind").value;
  const medListe = document.getElementById("medListe");
  const kontaktListe = document.getElementById("kontaktListe");
  const medForm = document.getElementById("medForm");
  const kontaktForm = document.getElementById("kontaktForm");
  const hatKind = Boolean(kindId);
  for (const element of medForm.elements) element.disabled = !hatKind;
  for (const element of kontaktForm.elements) element.disabled = !hatKind;
  if (!hatKind) {
    medListe.innerHTML = "<li>Zuerst ein Kind anlegen.</li>";
    kontaktListe.innerHTML = "";
    medListe.dataset.roh = "[]";
    kontaktListe.dataset.roh = "[]";
    return;
  }
  const [medikamente, kontakte] = await Promise.all([
    api("/medikamente/kind/" + kindId + "?inkl_inaktiv=true"),
    api("/kontakte/kind/" + kindId + "?inkl_inaktiv=true"),
  ]);
  medListe.innerHTML = medikamente.length ? medikamente.map((med) => `<li class="${med.aktiv ? "" : "inaktiv"}">
    <div class="stammkarte"><strong>${escapeHtml(med.name)}</strong>${med.aktiv ? "" : " <span class=\"pill keine\">inaktiv</span>"}
      <span class="feldzeile"><span class="label">Dosierung</span> ${escapeHtml(med.dosierung || "—")}</span>
      <span class="feldzeile"><span class="label">Einnahmezeit</span> ${escapeHtml(med.einnahmezeit || "—")}</span>
      ${med.hinweis ? `<span class="feldzeile"><span class="label">Hinweis</span> ${escapeHtml(med.hinweis)}</span>` : ""}
    </div>
    <div class="aktionen">
      <button type="button" class="sekundaer" data-aktion="bearbeiten" data-id="${med.id}">Bearbeiten</button>
      ${med.aktiv
        ? `<button type="button" class="leise" data-aktion="aus" data-id="${med.id}">Deaktivieren</button>`
        : `<button type="button" class="sekundaer" data-aktion="an" data-id="${med.id}">Aktivieren</button>`}
    </div>
  </li>`).join("") : "<li>Keine Medikation hinterlegt. Die Prüfung spricht Medikamente dann nicht an.</li>";
  const typLabel = { eltern: "Eltern", asd: "Jugendamt (ASD)", vormund: "Vormund", sonstige: "Sonstige" };
  kontaktListe.innerHTML = kontakte.length ? kontakte.map((kontakt) => `<li class="${kontakt.aktiv ? "" : "inaktiv"}">
    <div class="stammkarte"><strong>${escapeHtml(kontakt.name)}</strong>${kontakt.aktiv ? "" : " <span class=\"pill keine\">inaktiv</span>"}
      <span class="feldzeile"><span class="label">Art</span> ${escapeHtml(typLabel[kontakt.typ] || kontakt.typ)}</span>
      <span class="feldzeile"><span class="label">Telefon</span> ${escapeHtml(kontakt.telefon || "—")}</span>
      <span class="feldzeile"><span class="label">E-Mail</span> ${escapeHtml(kontakt.email || "—")}</span>
      ${kontakt.hinweis ? `<span class="feldzeile"><span class="label">Hinweis</span> ${escapeHtml(kontakt.hinweis)}</span>` : ""}
    </div>
    <div class="aktionen">
      <button type="button" class="sekundaer" data-aktion="bearbeiten" data-id="${kontakt.id}">Bearbeiten</button>
      ${kontakt.aktiv
        ? `<button type="button" class="leise" data-aktion="aus" data-id="${kontakt.id}">Deaktivieren</button>`
        : `<button type="button" class="sekundaer" data-aktion="an" data-id="${kontakt.id}">Aktivieren</button>`}
    </div>
  </li>`).join("") : "<li>Keine Kontakte.</li>";
  medListe.dataset.roh = JSON.stringify(medikamente);
  kontaktListe.dataset.roh = JSON.stringify(kontakte);
}

document.getElementById("kindForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const daten = formularDaten(event.target);
  if (!daten.vorname) return hinweis("Vorname fehlt.");
  try {
    if (kindEditId) {
      await api("/kinder/" + kindEditId, { method: "PUT", body: JSON.stringify(daten) });
      hinweis("Kind gespeichert.");
    } else {
      await api("/kinder/", { method: "POST", body: JSON.stringify(daten) });
      hinweis("Kind angelegt.");
    }
    kindModus(false);
    kindEditId = null;
    formLeeren(event.target);
    await ladeKinder();
  } catch (fehler) {
    hinweis(fehler.message);
  }
});

document.getElementById("kindAbbrechen").addEventListener("click", () => {
  kindEditId = null;
  formLeeren(document.getElementById("kindForm"));
  kindModus(false);
});

document.getElementById("kinderListe").addEventListener("click", async (event) => {
  const knopf = event.target.closest("button");
  if (!knopf) return;
  const id = Number(knopf.dataset.id);
  const kind = kinder.find((eintrag) => eintrag.id === id);
  try {
    if (knopf.dataset.aktion === "bearbeiten" && kind) {
      kindEditId = id;
      formFuellen(document.getElementById("kindForm"), kind);
      kindModus(true);
      document.getElementById("kindForm").scrollIntoView({ block: "start", behavior: sanft() });
      return;
    }
    if (knopf.dataset.aktion === "aus") {
      await api("/kinder/" + id, { method: "DELETE" });
      hinweis("Kind deaktiviert. Es erscheint nicht mehr in der Tagesarbeit.");
    }
    if (knopf.dataset.aktion === "an") {
      await api("/kinder/" + id, { method: "PUT", body: JSON.stringify({ aktiv: true }) });
      hinweis("Kind aktiviert.");
    }
    await ladeKinder();
  } catch (fehler) {
    hinweis(fehler.message);
  }
});

document.getElementById("bezugsKind").addEventListener("change", () => {
  medEditId = null;
  kontaktEditId = null;
  formLeeren(document.getElementById("medForm"));
  formLeeren(document.getElementById("kontaktForm"));
  document.getElementById("medSpeichern").textContent = "Hinzufügen";
  document.getElementById("kontaktSpeichern").textContent = "Hinzufügen";
  document.getElementById("medAbbrechen").hidden = true;
  document.getElementById("kontaktAbbrechen").hidden = true;
  ladeBezug().catch((fehler) => hinweis(fehler.message));
});

document.getElementById("medForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const kindId = document.getElementById("bezugsKind").value;
  if (!kindId) return hinweis("Bitte ein Kind auswählen.");
  const daten = formularDaten(event.target);
  try {
    if (medEditId) {
      await api("/medikamente/" + medEditId, { method: "PUT", body: JSON.stringify(daten) });
      hinweis("Medikation gespeichert.");
    } else {
      await api("/medikamente/", { method: "POST", body: JSON.stringify({ ...daten, kind_id: Number(kindId) }) });
      hinweis("Medikation hinzugefügt. Die Prüfung beachtet sie in passenden Schichten.");
    }
    medEditId = null;
    document.getElementById("medSpeichern").textContent = "Hinzufügen";
    document.getElementById("medAbbrechen").hidden = true;
    formLeeren(event.target);
    await ladeBezug();
  } catch (fehler) {
    hinweis(fehler.message);
  }
});

document.getElementById("medAbbrechen").addEventListener("click", () => {
  medEditId = null;
  formLeeren(document.getElementById("medForm"));
  document.getElementById("medSpeichern").textContent = "Hinzufügen";
  document.getElementById("medAbbrechen").hidden = true;
});

document.getElementById("medListe").addEventListener("click", async (event) => {
  const knopf = event.target.closest("button");
  if (!knopf) return;
  const id = Number(knopf.dataset.id);
  const medikamente = JSON.parse(document.getElementById("medListe").dataset.roh || "[]");
  const med = medikamente.find((eintrag) => eintrag.id === id);
  try {
    if (knopf.dataset.aktion === "bearbeiten" && med) {
      medEditId = id;
      formFuellen(document.getElementById("medForm"), med);
      document.getElementById("medSpeichern").textContent = "Änderungen speichern";
      document.getElementById("medAbbrechen").hidden = false;
      document.getElementById("medForm").scrollIntoView({ block: "start", behavior: sanft() });
      return;
    }
    if (knopf.dataset.aktion === "aus") await api("/medikamente/" + id, { method: "DELETE" });
    if (knopf.dataset.aktion === "an") await api("/medikamente/" + id, { method: "PUT", body: JSON.stringify({ aktiv: true }) });
    hinweis("Medikation aktualisiert.");
    await ladeBezug();
  } catch (fehler) {
    hinweis(fehler.message);
  }
});

document.getElementById("kontaktForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const kindId = document.getElementById("bezugsKind").value;
  if (!kindId) return hinweis("Bitte ein Kind auswählen.");
  const daten = formularDaten(event.target);
  daten.typ = event.target.elements.typ.value;
  try {
    if (kontaktEditId) {
      await api("/kontakte/" + kontaktEditId, { method: "PUT", body: JSON.stringify(daten) });
      hinweis("Kontakt gespeichert.");
    } else {
      await api("/kontakte/", { method: "POST", body: JSON.stringify({ ...daten, kind_id: Number(kindId) }) });
      hinweis("Kontakt hinzugefügt.");
    }
    kontaktEditId = null;
    document.getElementById("kontaktSpeichern").textContent = "Hinzufügen";
    document.getElementById("kontaktAbbrechen").hidden = true;
    formLeeren(event.target);
    await ladeBezug();
  } catch (fehler) {
    hinweis(fehler.message);
  }
});

document.getElementById("kontaktAbbrechen").addEventListener("click", () => {
  kontaktEditId = null;
  formLeeren(document.getElementById("kontaktForm"));
  document.getElementById("kontaktSpeichern").textContent = "Hinzufügen";
  document.getElementById("kontaktAbbrechen").hidden = true;
});

document.getElementById("kontaktListe").addEventListener("click", async (event) => {
  const knopf = event.target.closest("button");
  if (!knopf) return;
  const id = Number(knopf.dataset.id);
  const kontakte = JSON.parse(document.getElementById("kontaktListe").dataset.roh || "[]");
  const kontakt = kontakte.find((eintrag) => eintrag.id === id);
  try {
    if (knopf.dataset.aktion === "bearbeiten" && kontakt) {
      kontaktEditId = id;
      formFuellen(document.getElementById("kontaktForm"), kontakt);
      document.getElementById("kontaktSpeichern").textContent = "Änderungen speichern";
      document.getElementById("kontaktAbbrechen").hidden = false;
      document.getElementById("kontaktForm").scrollIntoView({ block: "start", behavior: sanft() });
      return;
    }
    if (knopf.dataset.aktion === "aus") await api("/kontakte/" + id, { method: "DELETE" });
    if (knopf.dataset.aktion === "an") await api("/kontakte/" + id, { method: "PUT", body: JSON.stringify({ aktiv: true }) });
    hinweis("Kontakt aktualisiert.");
    await ladeBezug();
  } catch (fehler) {
    hinweis(fehler.message);
  }
});

document.getElementById("pilotLaden").addEventListener("click", async () => {
  const ok = await frage(
    "Pilotkürzel und Beispielberichte anlegen? Vorhandene Kürzel und ihre Berichte bleiben unverändert.",
    "Anlegen",
  );
  if (!ok) return;
  const knopf = document.getElementById("pilotLaden");
  knopf.disabled = true;
  hinweis("Pilotdaten werden angelegt …");
  try {
    const ergebnis = await api("/seed/pilot", { method: "POST" });
    hinweis(seedSatz(ergebnis));
    await ladeKinder();
  } catch (fehler) {
    hinweis(fehler.message);
  } finally {
    knopf.disabled = false;
  }
});

ladeKinder().catch((fehler) => hinweis(fehler.message));
