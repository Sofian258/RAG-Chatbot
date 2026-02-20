# Multi-Tenant RAG Chatbot

Ein wiederverwendbarer RAG (Retrieval-Augmented Generation) Chatbot mit Multi-Tenant-Support, der firmenspezifische Dokumente verarbeitet und KI-gestützte Antworten generiert.

## Features

- **Multi-Tenant Architektur**: Isolierte Daten und Indizes pro Firma (`company_id`)
- **RAG-System**: Kombiniert Dokumenten-Retrieval mit LLM-Generierung
- **Lokale LLMs**: Nutzt Ollama für lokale Sprachmodelle (qwen2.5, llama3.2)
- **Vektor-Suche**: ChromaDB für semantische Dokumentensuche
- **Dokumenten-Formate**: Unterstützt TXT, PDF und Bilder (mit OCR)
- **Einbettbares Widget**: JavaScript-Widget für einfache Integration
- **REST API**: FastAPI mit automatischer Swagger-Dokumentation
- **Docker Support**: Vollständig containerisiert mit Docker Compose

## Tech Stack

- **Backend**: FastAPI, Python 3.x
- **LLM**: Ollama (qwen2.5:7b, qwen2.5:3b, llama3.2:1b)
- **Vektor-DB**: ChromaDB
- **Embeddings**: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Dokumenten-Parsing**: PyPDF2, Tesseract OCR
- **Frontend**: Vanilla JavaScript + CSS

## Quick Start

## Voraussetzungen

- Docker & Docker Compose

## Docker Container starten:

docker-compose up -d

- **Die Container laden automatisch die benötigten LLM-Modelle (kann einige Minuten dauern).






**Wichtig Wichtig Wichtig Wichtig: Erst Docker starten, dann funktionieren die Links.**



  
## API testen:

- **Swagger UI öffnen
http://localhost:8000/docs


## Verwendung

1. **Dokument hochladen**
   
   **curl -X POST "http://localhost:8000/api/companies/planovo/documents" \
       -F "file=@dein-dokument.txt"
   
Unterstützte Formate: .txt, .pdf, .jpg, .png, .gif, .bmp, .tiff 


2. **Chat-Anfrage stellen**

curl -X POST "http://localhost:8000/api/companies/planovo/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Was ist Planovo?",
    "top_k": 3,
    "use_rag": true
  }'

  3. **Widget einbinden**

     <!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="widget/chat.css">
</head>
<body>
  <!-- Chat Widget -->
  <script src="widget/chat.js" 
          data-company-id="planovo" 
          data-api-url="http://localhost:8000">
  </script>
</body>
</html>


## API Endpunkte
     

**Dokumenten-Management**

- **POST /api/companies/{company_id}/documents - Dokument hochladen
- **PUT /api/companies/{company_id}/documents - Dokument aktualisieren
- **DELETE /api/companies/{company_id}/documents - Dokument löschen
- **GET /api/companies - Alle Firmen auflisten


## Chat

- **POST /api/companies/{company_id}/chat - Chat-Anfrage (empfohlen)
- **POST /chat - Legacy-Endpunkt (benötigt company_id im Body)

## Projekte

- **POST /api/projects - Projekt erstellen
- **GET /api/projects - Projekte auflisten
- **PUT /api/projects/{project_id} - Projekt aktualisieren
- **DELETE /api/projects/{project_id} - Projekt löschen

-**Vollständige API-Dokumentation: http://localhost:8000/docs 






## Konfiguration

**Umgebungsvariablen**

- **Erstelle eine .env Datei:

  USE_LOCAL_MODELS=true
OLLAMA_URL=http://ollama:11434
LLM_MODEL=qwen2.5:7b
LLM_FAST_MODEL=qwen2.5:3b
LLM_FALLBACK_MODEL=llama3.2:1b
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2


## LLM Router Konfiguration

- **Bearbeite llm_config.json für Multi-Modell-Routing:

{
  "models": [
    {
      "name": "qwen2.5:7b",
      "complexity_threshold": 0.7,
      "temperature": 0.3
    }
  ]
}


Projektstruktur


Chatbotproject/
├── app/                    # Backend-Anwendung
│   ├── main.py            # FastAPI App & Endpunkte
│   ├── chat_handler.py    # Chat-Verarbeitungslogik
│   ├── rag_engine.py      # RAG-Engine
│   ├── document_manager.py # Dokumenten-Management
│   ├── vector_index.py    # ChromaDB Integration
│   ├── topic_index.py     # TF-IDF Fallback
│   ├── llm_router.py      # Multi-Modell Router
│   └── ...
├── widget/                # Frontend Widget
│   ├── chat.js           # Chat-Widget
│   ├── chat.css          # Styles
│   └── index.html        # Beispiel
├── docker-compose.yml     # Docker Compose Konfiguration
├── Dockerfile            # Container Build
├── requirements.txt      # Python Dependencies
└── ARCHITEKTUR.md        # Detaillierte Architektur-Dokumentation 


  
 ## Docker

# Container starten
docker-compose up -d

# Container stoppen
docker-compose down
