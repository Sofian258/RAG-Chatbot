# 📊 Projekt-Analyse: Chatbot-System

## 🎯 Projekt-Übersicht
Ein intelligenter Firmen-Chatbot, der Kundenfragen zu Öffnungszeiten, Versand, Rückgabe und Zahlung beantwortet. Das System kombiniert Cloud-basierte KI (OpenAI) mit lokaler semantischer Suche.

---

## 🛠️ Verwendete Technologien & Frameworks

### **Backend (Python)**
1. **FastAPI** - Modernes Web-Framework für REST-API
   - Asynchrone Request-Verarbeitung
   - Automatische API-Dokumentation
   - Type-safe mit Pydantic

2. **Uvicorn** - ASGI-Server
   - High-performance HTTP-Server
   - Unterstützt asynchrone Operationen

3. **OpenAI API** (gpt-4o-mini)
   - Cloud-basierte Topic-Erkennung
   - Klassifizierung von Kundenfragen

4. **scikit-learn**
   - **TfidfVectorizer** - Text-Vektorisierung (TF-IDF)
   - **cosine_similarity** - Semantische Ähnlichkeitssuche
   - N-gram Analyse (1-2 Wörter)

5. **NumPy** - Numerische Berechnungen für Vektoroperationen

6. **Pydantic** - Datenvalidierung und Serialisierung
   - Request/Response-Modelle
   - Field-Validierung (min/max length)

### **Frontend (JavaScript/HTML/CSS)**
1. **Vanilla JavaScript** - Keine Frameworks, native DOM-API
2. **Fetch API** - Asynchrone HTTP-Requests
3. **Modern CSS** - Flexbox, Grid, Animations, Gradients
4. **SVG Icons** - Skalierbare Vektorgrafiken

### **DevOps & Deployment**
1. **Docker** - Containerisierung
   - Python 3.11-slim Base Image
   - Multi-stage Build möglich

2. **Docker Compose** - Orchestrierung
   - Service-Management
   - Environment-Variablen

---

## 🏗️ Architektur & Design-Patterns

### **Hybrid-Suchstrategie (Cloud-First + Local-Backup)**

```
1. Greeting Detection (lokale Heuristik)
   ↓
2. Cloud Topic Detection (OpenAI GPT-4o-mini)
   ↓ (wenn Topic gefunden)
   Direkte Dokumentenabfrage
   ↓ (wenn kein Topic)
3. Lokale semantische Suche (TF-IDF + Cosine Similarity)
   ↓
4. Fallback (wenn keine relevanten Ergebnisse)
```

### **Komponenten-Struktur**

#### **Backend-Module:**
- `main.py` - FastAPI-App, Routing, Request-Handling
- `cloud_topic.py` - OpenAI-Integration für Topic-Klassifizierung
- `topic_index.py` - Lokale Suchmaschine (TF-IDF Index)
- `doc_loader.py` - Dokumenten-Parser (TXT → strukturierte Sections)

#### **Frontend-Module:**
- `index.html` - Widget-Struktur
- `chat.js` - API-Kommunikation, UI-Logik
- `chat.css` - Modernes Styling

---

## 🔍 Technische Details

### **1. Topic Detection (Cloud)**
- **Modell:** GPT-4o-mini
- **Methode:** Prompt-basierte Klassifizierung
- **Temperature:** 0 (deterministisch)
- **Themen:** ÖFFNUNGSZEITEN, VERSAND, RÜCKGABE, ZAHLUNG

### **2. Semantische Suche (Lokal)**
- **Algorithmus:** TF-IDF + Cosine Similarity
- **Features:**
  - N-gram Range: (1, 2) - Einzelwörter + Bigramme
  - Case-insensitive
  - Min Document Frequency: 1

### **3. Relevanz-Score (RSQ)**
```
RSQ = 0.75 × best_score + 0.25 × margin
```
- Kombiniert absoluten Score mit Margin zum zweitbesten Ergebnis
- Threshold: 0.35 (unter diesem Wert → Fallback)

### **4. CORS-Konfiguration**
- Allow-Origins: `*` (für Entwicklung)
- Production: Sollte spezifische Domains erlauben

---

## 📋 API-Endpunkte

### **GET /health**
- Health-Check Endpoint
- Response: `{"status": "ok"}`

### **POST /chat**
**Request:**
```json
{
  "message": "string (1-4000 chars)",
  "top_k": 3 (optional, 1-5)
}
```

**Response-Varianten:**

1. **Greeting:**
```json
{
  "answer": "Hallo! Wie kann ich dir helfen?",
  "topic": "greeting",
  "mode": "greeting"
}
```

2. **Cloud-Topic:**
```json
{
  "answer": "Dokumententext...",
  "topic": "VERSAND",
  "mode": "cloud-topic"
}
```

3. **Local Search:**
```json
{
  "answer": "Dokumententext...",
  "topic": "VERSAND",
  "rsq": 0.85,
  "mode": "local",
  "candidates": [
    {"topic": "VERSAND", "score": 0.85, "source_id": "versand"},
    ...
  ]
}
```

4. **Fallback:**
```json
{
  "answer": "Ich habe dazu keine Informationen...",
  "topic": null,
  "rsq": 0.25,
  "mode": "fallback"
}
```

---

## 🎨 Frontend-Features

### **UI/UX:**
- ✅ Floating Action Button (FAB)
- ✅ Slide-up Animation
- ✅ Message Bubbles (User vs. Bot)
- ✅ Gradient Design (Purple/Blue)
- ✅ Responsive Design (Mobile-ready)
- ✅ Smooth Scrolling
- ✅ Enter-Key Support
- ✅ Accessibility (ARIA-Labels)

### **Interaktionen:**
- Click-to-open/close Chat
- Real-time Message Display
- Auto-scroll to latest message
- Input Validation (trim empty)

---

## 🔐 Sicherheit & Best Practices

### **✅ Gut implementiert:**
- Input-Validierung (Pydantic)
- Error-Handling (try-catch in cloud_topic.py)
- CORS-Middleware
- Environment-Variablen für API-Keys

### **⚠️ Verbesserungspotenzial:**
- CORS: `allow_origins=["*"]` → spezifische Domains in Production
- API-Key: Sollte in `.env` sein (nicht hardcoded)
- Rate Limiting fehlt
- Input Sanitization für XSS (Frontend)
- HTTPS in Production

---

## 📊 Datenfluss

```
User Input (Frontend)
    ↓
POST /chat (FastAPI)
    ↓
1. Greeting Check → Ja? → Return Greeting
    ↓ Nein
2. OpenAI Topic Detection → Topic gefunden? → Return Document
    ↓ Nein
3. TF-IDF Search → RSQ > 0.35? → Return Best Match
    ↓ Nein
4. Fallback Response
    ↓
JSON Response → Frontend → Display Message
```

---

## 🚀 Deployment

### **Docker-Setup:**
- Base: `python:3.11-slim`
- Port: 8000
- Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### **Environment:**
- `OPENAI_API_KEY` - Muss gesetzt sein für Cloud-Topic-Detection

---

## 📈 Skalierbarkeit & Performance

### **Stärken:**
- Lokale Suche ist schnell (TF-IDF in Memory)
- Cloud-API nur bei Bedarf
- Stateless Backend (horizontal skalierbar)

### **Limitationen:**
- TF-IDF Index im Memory (bei großen Dokumenten → mehr RAM)
- Keine Persistenz (Index wird bei Restart neu aufgebaut)
- Keine Caching-Mechanismen

---

## 🎓 Zusammenfassung

**Technologie-Stack:**
- **Backend:** FastAPI + OpenAI + scikit-learn
- **Frontend:** Vanilla JS + Modern CSS
- **Deployment:** Docker + Docker Compose
- **AI/ML:** GPT-4o-mini + TF-IDF Vectorization

**Architektur-Pattern:**
- Hybrid Search (Cloud-First, Local-Backup)
- Layered Response (Greeting → Cloud → Local → Fallback)
- RESTful API Design

**Besonderheiten:**
- Intelligente Topic-Erkennung mit OpenAI
- Lokale semantische Suche als Fallback
- RSQ-Scoring für Relevanz-Bewertung
- Modernes, responsives Widget-Design

---

## ❓ Häufige Fragen zum Projekt

**Q: Warum zwei Suchmethoden?**
A: Cloud (OpenAI) ist präziser für Topic-Erkennung, aber teurer und langsamer. Lokale Suche ist kostenlos und schnell, aber weniger intelligent. Die Kombination bietet Best-of-Both-Worlds.

**Q: Wie funktioniert die Relevanz-Bewertung?**
A: RSQ kombiniert den besten Score (75%) mit dem Margin zum zweitbesten Ergebnis (25%). Ein hoher Margin bedeutet, dass das beste Ergebnis deutlich besser ist.

**Q: Kann das System erweitert werden?**
A: Ja! Neue Themen können in `cloud_topic.py` und `company_doc.txt` hinzugefügt werden. Die lokale Suche skaliert automatisch mit neuen Dokumenten.

**Q: Ist das System production-ready?**
A: Fast! Noch zu tun: CORS einschränken, Rate Limiting, HTTPS, Error-Logging, Monitoring.
