# 🏗️ Architektur: Multi-Tenant RAG-Chatbot System

## Übersicht

Das System ist eine **Multi-Tenant RAG (Retrieval-Augmented Generation) Chatbot-Architektur**, die firmenspezifische Dokumente verarbeitet und KI-gestützte Antworten generiert.

---

## Architektur-Ebenen

### 1. Präsentationsschicht (Presentation Layer)

```
┌─────────────────────────────────────┐
│         Frontend Widget              │
│  (Vanilla JavaScript + CSS)          │
│  - chat.js                           │
│  - chat.css                          │
│  - index.html                        │
└──────────────┬──────────────────────┘
               │ HTTP/REST
               ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  - main.py (API-Endpunkte)          │
│  - CORS Middleware                   │
│  - Request/Response Validation       │
└─────────────────────────────────────┘
```

**Komponenten:**
- **Widget**: Einbettbares Chat-Interface
- **FastAPI**: REST-API mit automatischer Swagger-Dokumentation
- **CORS**: Cross-Origin Resource Sharing für Web-Integration

---

### 2. Anwendungsschicht (Application Layer)

```
┌─────────────────────────────────────┐
│      Chat Handler                    │
│  - process_chat_query()             │
│  - Greeting-Erkennung                │
│  - Request-Routing                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Document Manager                │
│  - Multi-Tenant-Verwaltung           │
│  - company_id → Index Mapping        │
│  - Dokumenten-Upload                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      RAG Engine                      │
│  - Retrieval-Augmented Generation    │
│  - Kontext-Erstellung                │
│  - LLM-Prompt-Generierung            │
│  - Antwort-Bereinigung               │
└─────────────────────────────────────┘
```

**Komponenten:**
- **Chat Handler**: Zentrale Chat-Verarbeitungslogik
- **Document Manager**: Multi-Tenant Dokumenten-Verwaltung
- **RAG Engine**: Kern der KI-Logik (Retrieval + Generation)

---

### 3. Datenzugriffsschicht (Data Access Layer)

```
┌─────────────────────────────────────┐
│      Vector Index                    │
│  - ChromaDB Integration              │
│  - Semantische Suche                 │
│  - Top-K Chunk Retrieval            │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│  Local      │  │  ChromaDB   │
│  Embeddings │  │  (Persistent)│
└─────────────┘  └─────────────┘
```

**Komponenten:**
- **Vector Index**: Vektordatenbank-Integration (ChromaDB)
- **Local Embeddings**: Embedding-Generierung (sentence-transformers)
- **ChromaDB**: Persistente Vektordatenbank pro Firma

---

### 4. KI-Schicht (AI/ML Layer)

```
┌─────────────────────────────────────┐
│      LLM Router                      │
│  - Intelligente Modell-Auswahl       │
│  - Komplexitäts-Analyse              │
│  - Load Balancing                    │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│  Local LLM  │  │  Ollama     │
│  (qwen2.5)  │  │  Service    │
└─────────────┘  └─────────────┘
```

**Komponenten:**
- **LLM Router**: Intelligente Modell-Auswahl basierend auf Komplexität
- **Local LLM**: Integration mit Ollama
- **Ollama**: Lokaler LLM-Service (qwen2.5:7b, qwen2.5:3b, llama3.2:1b)

---

### 5. Infrastruktur-Schicht (Infrastructure Layer)

```
┌─────────────────────────────────────┐
│      Docker Compose                  │
│  - Service Orchestrierung            │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│  Chatbot    │  │  Ollama     │
│  Container  │  │  Container  │
│  (Port 8000)│  │  (Port 11434)│
└─────────────┘  └─────────────┘
```

**Komponenten:**
- **Docker Compose**: Service-Orchestrierung
- **Chatbot Container**: FastAPI-Anwendung
- **Ollama Container**: LLM-Service

---

## Multi-Tenant-Architektur

### Datenisolation

```
┌─────────────────────────────────────┐
│      FastAPI Application             │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Company A│ │Company B│ │Company C│
│planovo  │ │acme-corp│ │tech-gmbh│
└────┬────┘ └────┬────┘ └────┬────┘
     │           │           │
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│Index A  │ │Index B  │ │Index C  │
│ChromaDB │ │ChromaDB │ │ChromaDB │
└─────────┘ └─────────┘ └─────────┘
```

**Isolation-Mechanismen:**
- **company_id**: Eindeutige Identifikation pro Firma
- **Separate Collections**: Jede Firma hat eigene ChromaDB-Collection
- **Separate Indizes**: Jede Firma hat eigenen VectorIndex
- **Separate RAG Engines**: Jede Firma hat eigene RAG-Engine-Instanz
- **Separate Dokumente**: Dokumente werden pro Firma gespeichert

**Speicherorte:**
- Dokumente: `documents/{company_id}_{filename}`
- ChromaDB: `chroma_db/{company_id}/`
- Metadaten: `documents/metadata.json` (mit company_id-Mapping)

---

## Datenfluss-Architektur

### Chat-Anfrage-Fluss

```
1. Benutzer-Anfrage
   │
   ▼
2. FastAPI Endpoint (/api/companies/{company_id}/chat)
   │
   ▼
3. Chat Handler (process_chat_query)
   │
   ├─→ Greeting? → Ja → Return Greeting
   │
   └─→ Nein
       │
       ▼
4. Document Manager
   │
   ├─→ company_id vorhanden? → Nein → HTTP 404
   │
   └─→ Ja
       │
       ▼
5. Vector Index (ChromaDB)
   │
   ├─→ Embedding-Generierung (Local Embeddings)
   │
   ├─→ Semantische Suche (Top-K Chunks)
   │
   └─→ Relevanz-Score (RSQ)
       │
       ▼
6. RAG Engine
   │
   ├─→ Kontext-Erstellung aus Chunks
   │
   ├─→ Prompt-Generierung (firmenspezifisch)
   │
   └─→ LLM Router
       │
       ├─→ Komplexitäts-Analyse
       │
       ├─→ Modell-Auswahl (qwen2.5:7b / qwen2.5:3b / llama3.2:1b)
       │
       └─→ Ollama API-Aufruf
           │
           ▼
7. Antwort-Generierung
   │
   ├─→ Antwort-Bereinigung (clean_answer)
   │
   ├─→ Quellen-Entfernung (für Planovo)
   │
   └─→ JSON-Response
       │
       ▼
8. Frontend Widget
   │
   └─→ Anzeige der Antwort
```

---

### Dokument-Upload-Fluss

```
1. Dokument-Upload (POST /api/companies/{company_id}/documents)
   │
   ▼
2. Document Manager (upload_document)
   │
   ├─→ Dateityp-Erkennung (TXT / PDF / Bild)
   │
   └─→ Doc Loader
       │
       ├─→ TXT → load_sections_from_txt()
       │   └─→ Überschriften-Erkennung
       │   └─→ Abschnitts-Segmentierung
       │
       ├─→ PDF → load_sections_from_pdf()
       │   └─→ Text-Extraktion
       │   └─→ Segmentierung
       │
       └─→ Bild → load_sections_from_image()
           └─→ OCR (Tesseract)
           └─→ Text-Extraktion
           └─→ Segmentierung
       │
       ▼
3. Vector Index (VectorIndex)
   │
   ├─→ ChromaDB Collection erstellen/laden
   │   └─→ Collection-Name: "documents_{company_id}"
   │
   ├─→ Alte Collection löschen (bei Update)
   │
   ├─→ Embedding-Generierung für jeden Chunk
   │   └─→ Local Embeddings (sentence-transformers)
   │
   └─→ In ChromaDB speichern
       │
       ▼
4. Index-Speicherung
   │
   ├─→ VectorIndex in DocumentManager speichern
   │
   ├─→ Metadaten speichern (metadata.json)
   │
   └─→ RAG Engine erstellen (bei Bedarf)
```

---

## Komponenten-Interaktionen

### Abhängigkeits-Graph

```
main.py (API-Layer)
│
├──→ chat_handler.py
│   │
│   ├──→ document_manager.py
│   │   │
│   │   ├──→ doc_loader.py
│   │   │   ├──→ PyPDF2 (PDF)
│   │   │   └──→ Tesseract OCR (Bilder)
│   │   │
│   │   └──→ vector_index.py
│   │       │
│   │       ├──→ local_embeddings.py
│   │       │   └──→ sentence-transformers
│   │       │
│   │       └──→ chromadb
│   │
│   └──→ rag_engine.py
│       │
│       ├──→ vector_index.py (für Suche)
│       │
│       └──→ llm_router.py
│           │
│           └──→ local_llm.py
│               │
│               └──→ Ollama API
│
└──→ project_manager.py (optional)
```

---

## Architektur-Patterns

### 1. Multi-Tenant Pattern
- **Isolation**: Jede Firma hat isolierte Daten
- **Skalierung**: Neue Firmen können einfach hinzugefügt werden
- **Sicherheit**: Keine Datenvermischung zwischen Firmen

### 2. Repository Pattern
- **DocumentManager**: Zentralisiert Dokumenten-Zugriff
- **VectorIndex**: Abstrahiert Vektordatenbank-Zugriff
- **ProjectManager**: Verwaltet Projekt-Daten

### 3. Strategy Pattern
- **LLM Router**: Wählt Strategie (Modell) basierend auf Komplexität
- **Doc Loader**: Verschiedene Strategien für verschiedene Dateitypen

### 4. Factory Pattern
- **RAG Engine**: Erstellt LLM-Instanzen basierend auf Konfiguration
- **Vector Index**: Erstellt Embedding-Modelle basierend auf Konfiguration

### 5. Chain of Responsibility
- **Chat Handler**: Verarbeitet Anfrage durch verschiedene Schritte
  - Greeting → RAG → Fallback

---

## Skalierungs-Architektur

### Horizontale Skalierung

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Load       │     │  Load       │     │  Load       │
│  Balancer   │────▶│  Balancer   │────▶│  Balancer   │
└─────────────┘     └─────────────┘     └─────────────┘
     │                   │                   │
     ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Chatbot    │     │  Chatbot    │     │  Chatbot    │
│  Instance 1 │     │  Instance 2 │     │  Instance 3 │
└─────────────┘     └─────────────┘     └─────────────┘
     │                   │                   │
     └───────────────────┼───────────────────┘
                         │
                         ▼
                 ┌─────────────┐
                 │  Shared     │
                 │  ChromaDB   │
                 │  (oder      │
                 │  Replicated)│
                 └─────────────┘
```

**Skalierungs-Optionen:**
- **Stateless Backend**: FastAPI-Instanzen können horizontal skaliert werden
- **Shared ChromaDB**: Zentrale Vektordatenbank für alle Instanzen
- **Ollama Cluster**: Mehrere Ollama-Instanzen für Load Balancing

---

## Sicherheits-Architektur

### Sicherheitsebenen

```
┌─────────────────────────────────────┐
│  1. CORS Middleware                  │
│     - Erlaubte Origins                │
│     - Credentials-Handling            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  2. Input Validation                 │
│     - Pydantic Models                 │
│     - Field-Validierung               │
│     - Längen-Limits                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  3. Multi-Tenant Isolation           │
│     - company_id-Validierung         │
│     - Datenisolation                 │
│     - Keine Cross-Tenant-Zugriffe    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  4. Error Handling                  │
│     - HTTP-Status-Codes              │
│     - Fehler-Logging                 │
│     - Keine sensible Daten in Logs   │
└─────────────────────────────────────┘
```

---

## Persistenz-Architektur

### Datenpersistenz

```
┌─────────────────────────────────────┐
│  Dokumente                          │
│  - documents/{company_id}_{file}     │
│  - Dateisystem                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Vektordatenbank                    │
│  - chroma_db/{company_id}/          │
│  - ChromaDB (Persistent)            │
│  - Embeddings + Metadaten           │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Metadaten                          │
│  - documents/metadata.json          │
│  - JSON-Format                       │
│  - company_id → Metadaten-Mapping   │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Projekte                           │
│  - In-Memory (project_manager.py)   │
│  - Optional: Datenbank-Integration  │
└─────────────────────────────────────┘
```

---

## Deployment-Architektur

### Docker-basierte Architektur

```
┌─────────────────────────────────────┐
│  Docker Compose                     │
│  - Service-Orchestrierung            │
│  - Network-Management                │
│  - Volume-Management                 │
└──────────────┬──────────────────────┘
               │
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
┌─────────────┐      ┌─────────────┐
│  Chatbot    │      │  Ollama     │
│  Container  │      │  Container  │
│             │      │             │
│  - FastAPI  │      │  - LLM      │
│  - Python   │      │  - Models   │
│  - Port 8000│      │  - Port     │
│             │      │    11434    │
└─────────────┘      └─────────────┘
    │                       │
    └───────────┬───────────┘
               │
               ▼
    ┌─────────────────────┐
    │  Shared Volumes      │
    │  - documents/        │
    │  - chroma_db/        │
    │  - ollama_data/      │
    └─────────────────────┘
```

---

## Zusammenfassung

### Architektur-Merkmale

1. **Multi-Tenant**: Vollständige Datenisolation pro Firma
2. **RAG-basiert**: Retrieval-Augmented Generation für präzise Antworten
3. **Lokale LLMs**: Keine Cloud-Abhängigkeit, vollständig lokal
4. **Skalierbar**: Horizontale Skalierung möglich
5. **Modular**: Klare Trennung der Verantwortlichkeiten
6. **Containerisiert**: Docker-basiertes Deployment
7. **RESTful**: Standard REST-API
8. **Intelligent**: Multi-Modell-Routing basierend auf Komplexität

### Technologie-Stack

- **Backend**: FastAPI, Python 3.11
- **Vektordatenbank**: ChromaDB
- **Embeddings**: sentence-transformers (lokal)
- **LLMs**: Ollama (qwen2.5, llama3.2)
- **Dokumentenverarbeitung**: PyPDF2, Tesseract OCR
- **Container**: Docker, Docker Compose
- **Frontend**: Vanilla JavaScript

Diese Architektur ermöglicht ein skalierbares, sicheres und wartbares Multi-Tenant RAG-Chatbot-System.
