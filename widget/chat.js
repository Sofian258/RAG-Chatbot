// Konfiguration
const COMPANY_ID = document.currentScript?.getAttribute("data-company-id") || "firma1"; // Deine company_id
const API_URL = document.currentScript?.getAttribute("data-api-url") || `http://localhost:8000/api/companies/${COMPANY_ID}/chat`; // Firmen-spezifischer Chat

const openBtn = document.getElementById("chat-open");
const closeBtn = document.getElementById("chat-close");
const box = document.getElementById("chatbox");
const sendBtn = document.getElementById("send");
const input = document.getElementById("msg");
const messages = document.getElementById("chat-messages");

openBtn.onclick = () => box.classList.remove("hidden");
closeBtn.onclick = () => box.classList.add("hidden");

function addMsg(text, cls, sources = null) {
  const div = document.createElement("div");
  div.className = `msg ${cls}`;
  
  // Text-Inhalt
  const textDiv = document.createElement("div");
  textDiv.className = "msg-text";
  textDiv.textContent = text;
  div.appendChild(textDiv);
  
  // Quellen anzeigen, wenn vorhanden
  if (sources && sources.length > 0 && cls === "bot") {
    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "msg-sources";
    sourcesDiv.innerHTML = `<strong>Quellen:</strong> ${sources.map(s => s.title || s.source_id || "Unbekannt").join(", ")}`;
    div.appendChild(sourcesDiv);
  }
  
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

async function send() {
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMsg(text, "me");

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        message: text,
        use_rag: true,  // RAG aktiviert für Analyse und präzise Antworten
        top_k: 3
      })
    });

    if (!res.ok) {
      // API-Fehler (404, 500, etc.)
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      addMsg(`Fehler: ${error.detail || res.statusText}`, "bot");
      console.error("API Error:", error, "Status:", res.status);
      return;
    }

    const data = await res.json();
    
    // Prüfe ob Antwort vorhanden ist
    if (data.answer) {
      // Quellen aus API-Response extrahieren
      const sources = data.sources || [];
      addMsg(data.answer, "bot", sources);
      
      // Debug-Info in Console
      if (sources.length > 0) {
        console.log("Quellen:", sources);
        console.log("RSQ:", data.rsq, "Mode:", data.mode);
      }
    } else {
      addMsg("Keine Antwort erhalten.", "bot");
      console.warn("Keine Antwort im Response:", data);
    }
  } catch (error) {
    // Netzwerk-Fehler oder andere Exceptions
    addMsg("Fehler: Verbindung zum Server fehlgeschlagen. Bitte prüfe, ob der Server läuft.", "bot");
    console.error("Network Error:", error);
  }
}

sendBtn.onclick = send;
input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
