// Konfiguration
const API_URL = document.currentScript?.getAttribute("data-api-url") || "http://localhost:8000/api/projects";

const openBtn = document.getElementById("project-open");
const closeBtn = document.getElementById("project-close");
const box = document.getElementById("projectbox");
const form = document.getElementById("project-form");
const formContainer = document.getElementById("project-form-container");
const successMessage = document.getElementById("success-message");
const statusDiv = document.getElementById("form-status");
const submitBtn = document.getElementById("submit-btn");
const btnText = submitBtn.querySelector(".btn-text");
const btnLoading = submitBtn.querySelector(".btn-loading");
const newProjectBtn = document.getElementById("new-project-btn");

// Event Listeners
openBtn.onclick = () => {
  box.classList.remove("hidden");
  resetForm();
};

closeBtn.onclick = () => {
  box.classList.add("hidden");
  resetForm();
};

newProjectBtn.onclick = () => {
  showForm();
  resetForm();
};

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  await createProject();
});

// Formular zurücksetzen
function resetForm() {
  form.reset();
  statusDiv.textContent = "";
  statusDiv.className = "";
  showForm();
}

// Formular anzeigen
function showForm() {
  formContainer.style.display = "block";
  successMessage.classList.add("hidden");
  form.classList.remove("hidden");
}

// Erfolgs-Nachricht anzeigen
function showSuccess(projectId) {
  form.classList.add("hidden");
  successMessage.classList.remove("hidden");
  document.getElementById("project-id-display").textContent = `Projekt-ID: ${projectId}`;
  
  // Auto-close nach 5 Sekunden
  setTimeout(() => {
    box.classList.add("hidden");
    resetForm();
  }, 5000);
}

// Projekt erstellen
async function createProject() {
  // Formular-Daten sammeln
  const formData = new FormData(form);
  const data = {
    name: formData.get("name"),
  };

  // Optionale Felder nur hinzufügen, wenn ausgefüllt
  const description = formData.get("description")?.trim();
  if (description) data.description = description;

  const ort = formData.get("ort")?.trim();
  if (ort) data.ort = ort;

  const startdatum = formData.get("startdatum");
  if (startdatum) data.startdatum = startdatum;

  const enddatum = formData.get("enddatum");
  if (enddatum) data.enddatum = enddatum;

  const projekttyp = formData.get("projekttyp");
  if (projekttyp) data.projekttyp = projekttyp;

  const ansprechpartner = formData.get("ansprechpartner")?.trim();
  if (ansprechpartner) data.ansprechpartner = ansprechpartner;

  const team_type = formData.get("team_type");
  if (team_type) data.team_type = team_type;

  const company_id = formData.get("company_id")?.trim();
  if (company_id) data.company_id = company_id;

  // UI-Status aktualisieren
  submitBtn.disabled = true;
  btnText.classList.add("hidden");
  btnLoading.classList.remove("hidden");
  statusDiv.textContent = "";
  statusDiv.className = "";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || result.message || "Fehler beim Erstellen des Projekts");
    }

    // Erfolg!
    statusDiv.textContent = "Projekt wird erstellt...";
    statusDiv.className = "success";
    
    // Kurze Verzögerung für bessere UX
    setTimeout(() => {
      showSuccess(result.project?.project_id || "unbekannt");
    }, 500);

  } catch (error) {
    console.error("Fehler:", error);
    statusDiv.textContent = error.message || "Fehler beim Erstellen des Projekts. Bitte versuche es erneut.";
    statusDiv.className = "error";
  } finally {
    submitBtn.disabled = false;
    btnText.classList.remove("hidden");
    btnLoading.classList.add("hidden");
  }
}

// Enter-Taste für Formular-Submit
form.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
    e.preventDefault();
    if (!submitBtn.disabled) {
      form.dispatchEvent(new Event("submit"));
    }
  }
});
