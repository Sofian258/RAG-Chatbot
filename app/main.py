from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import re
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional, Literal

from app.doc_loader import load_sections_from_txt
from app.topic_index import TopicIndex
from app.document_manager import DocumentManager
from app.rag_engine import RAGEngine
from app.project_manager import ProjectManager
from app.chat_handler import process_chat_query

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('chatbot.log', maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Chatbot API",
    description="Wiederverwendbarer RAG-Chatbot mit dynamischem Dokumenten-Management",
    version="1.0.0"
)

# CORS: Spezifische Domains erlauben (sicherer für Production)
# Für Development: Erlaube auch file:// und andere localhost-Ports
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Development: Erlaube alle localhost-Varianten und file://
    allowed_origins = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "null"  # Für file:// Protokoll
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Statt ['*'] für bessere Sicherheit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Document Manager für Multi-Tenant-Support
doc_manager = DocumentManager()
rag_engines: Dict[str, RAGEngine] = {}  # company_id -> RAGEngine

# Project Manager für Projekt-Verwaltung
project_manager = ProjectManager()

# Multi-Modell LLM Router (optional, wird aktiviert wenn USE_LLM_ROUTER=true)
use_llm_router = os.getenv("USE_LLM_ROUTER", "true").lower() == "true"
llm_router = None
if use_llm_router:
    try:
        from app.llm_router import LLMRouter
        llm_router = LLMRouter()
        print("✓ Multi-Modell LLM Router aktiviert")
    except Exception as e:
        print(f"⚠ LLM Router konnte nicht initialisiert werden: {e}, nutze Legacy-Modus")
        llm_router = None

# Standard-Dokument wird nicht mehr für Chat verwendet
# company_id ist jetzt Pflichtfeld für alle Chat-Anfragen
    default_index = None
    default_rag = None


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(3, ge=1, le=5)
    use_rag: bool = Field(True, description="Nutze RAG für Antwort-Generierung")


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Projektname (Pflichtfeld)")
    description: Optional[str] = Field(None, max_length=2000, description="Projektbeschreibung")
    team_type: Optional[Literal["Techniker", "Entwickler"]] = Field(
        None, 
        description="Team-Typ: Techniker oder Entwickler. Kann später ergänzt werden."
    )
    company_id: Optional[str] = Field(None, description="Verknüpfung zu einer Firma (optional)")
    status: str = Field("active", description="Projektstatus")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    team_type: Optional[Literal["Techniker", "Entwickler", None]] = None
    company_id: Optional[str] = None
    status: Optional[str] = None


def is_greeting(text: str) -> bool:
    return text.strip().lower() in {
        "hallo", "hi", "hey",
        "guten tag", "guten morgen",
        "guten abend", "servus", "moin"
    }


def format_chunk_fallback(chunk_text: str) -> str:
    """
    Formatiert Chunk-Text intelligent als Fallback, statt rohen Text zurückzugeben.
    Extrahiert erste 2-3 relevante Sätze.
    """
    sentences = re.split(r'[.!?]+', chunk_text)
    relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
    if relevant_sentences:
        return '. '.join(relevant_sentences) + '.'
    else:
        # Nur wenn wirklich nichts gefunden: Erste 200 Zeichen
        return chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text




@app.get("/")
def root():
    """Root-Endpunkt mit API-Übersicht"""
    return {
        "message": "RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "api_docs": "/docs",
            "chat": "/chat",
            "upload_document": "/api/companies/{company_id}/documents",
            "company_chat": "/api/companies/{company_id}/chat",
            "list_companies": "/api/companies",
            "company_info": "/api/companies/{company_id}",
            "create_project": "/api/projects",
            "list_projects": "/api/projects",
            "get_project": "/api/projects/{project_id}",
            "update_project": "/api/projects/{project_id}",
            "delete_project": "/api/projects/{project_id}"
        },
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "ok", "companies": len(doc_manager.indices)}


# ==================== Dokumenten-Management API ====================

@app.post("/api/companies/{company_id}/documents")
async def upload_document(
    company_id: str,
    file: UploadFile = File(...)
):
    """
    Lädt Dokument für eine Firma hoch
    
    Unterstützte Formate:
    - **TXT**: Text-Dateien (.txt)
    - **PDF**: PDF-Dateien (.pdf)
    - **Bilder**: Fotos mit Text (.jpg, .png, .gif, etc.) - wird mit OCR verarbeitet
    
    - **company_id**: Eindeutige ID der Firma (z.B. "firma1", "acme-corp")
    - **file**: Datei mit Firmeninformationen (TXT, PDF oder Bild)
    """
    if not file.filename:
        raise HTTPException(400, "Kein Dateiname angegeben")
    
    content = await file.read()
    file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    
    # Bestimme ob Binary (PDF/Bilder) oder Text
    if file_ext == 'pdf' or file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
        # Binary-Dateien (PDF, Bilder) direkt weitergeben
        result = doc_manager.upload_document(company_id, content, file.filename)
    else:
        # Text-Dateien dekodieren
        try:
            content_str = content.decode("utf-8")
            result = doc_manager.upload_document(company_id, content_str, file.filename)
        except UnicodeDecodeError:
            raise HTTPException(400, "Text-Datei muss UTF-8 kodiert sein")
    
    # Erstelle RAG Engine für diese Firma
    api_key = os.getenv("OPENAI_API_KEY")
    use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
    index = doc_manager.get_index(company_id)
    if index:
        rag_engines[company_id] = RAGEngine(index, use_local=use_local, api_key=api_key, llm_router=llm_router)
    
    return result


@app.put("/api/companies/{company_id}/documents")
async def update_document(
    company_id: str,
    file: UploadFile = File(...)
):
    """
    Aktualisiert Dokument einer Firma (ersetzt altes)
    
    Unterstützte Formate: TXT, PDF, Bilder (mit OCR)
    """
    if not file.filename:
        raise HTTPException(400, "Kein Dateiname angegeben")
    
    content = await file.read()
    file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    
    # Bestimme ob Binary (PDF/Bilder) oder Text
    if file_ext == 'pdf' or file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
        # Binary-Dateien (PDF, Bilder) direkt weitergeben
        result = doc_manager.update_document(company_id, content, file.filename)
    else:
        # Text-Dateien dekodieren
        try:
            content_str = content.decode("utf-8")
            result = doc_manager.update_document(company_id, content_str, file.filename)
        except UnicodeDecodeError:
            raise HTTPException(400, "Text-Datei muss UTF-8 kodiert sein")
    
    # Aktualisiere RAG Engine
    api_key = os.getenv("OPENAI_API_KEY")
    use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
    index = doc_manager.get_index(company_id)
    if index:
        rag_engines[company_id] = RAGEngine(index, use_local=use_local, api_key=api_key, llm_router=llm_router)
    
    return result


@app.delete("/api/companies/{company_id}/documents")
def delete_document(company_id: str):
    """Löscht Dokument einer Firma"""
    if doc_manager.delete_document(company_id):
        # Entferne RAG Engine
        rag_engines.pop(company_id, None)
        return {"status": "deleted", "company_id": company_id}
    raise HTTPException(404, f"Firma {company_id} nicht gefunden")


@app.get("/api/companies")
def list_companies():
    """Listet alle Firmen mit Dokumenten"""
    return {"companies": doc_manager.list_companies()}


@app.get("/api/companies/{company_id}")
def get_company_info(company_id: str):
    """Holt Informationen zu einer Firma"""
    if not doc_manager.company_exists(company_id):
        raise HTTPException(404, f"Firma {company_id} nicht gefunden")
    
    metadata = doc_manager.metadata.get(company_id, {})
    index = doc_manager.get_index(company_id)
    
    return {
        "company_id": company_id,
        "metadata": metadata,
        "has_index": index is not None,
        "has_rag": company_id in rag_engines
    }


# ==================== Projekt-Management API ====================

@app.post("/api/projects")
def create_project(project: ProjectCreate):
    """
    Erstellt ein neues Projekt
    
    **Pflichtfelder:**
    - **name**: Projektname
    
    **Optionale Felder:**
    - **description**: Projektbeschreibung
    - **team_type**: "Techniker" oder "Entwickler" (kann später ergänzt werden)
    - **company_id**: Verknüpfung zu einer Firma
    - **status**: Projektstatus (default: "active")
    
    Wenn alle Felder ausgefüllt sind, wird das Projekt erstellt und du kannst weiterarbeiten.
    """
    # Validiere company_id falls angegeben
    if project.company_id and not doc_manager.company_exists(project.company_id):
        raise HTTPException(
            404, 
            f"Firma '{project.company_id}' nicht gefunden. Bitte erstelle zuerst die Firma oder lasse das Feld leer."
        )
    
    result = project_manager.create_project(
        name=project.name,
        description=project.description,
        team_type=project.team_type,
        company_id=project.company_id,
        status=project.status
    )
    
    return {
        "message": "Projekt erfolgreich erstellt",
        "project": result
    }


@app.get("/api/projects")
def list_projects(
    company_id: Optional[str] = None,
    team_type: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Listet alle Projekte mit optionalen Filtern
    
    **Filter:**
    - **company_id**: Filter nach Firma
    - **team_type**: Filter nach Team-Typ ("Techniker" oder "Entwickler")
    - **status**: Filter nach Status
    """
    projects = project_manager.list_projects(
        company_id=company_id,
        team_type=team_type,
        status=status
    )
    
    return {
        "count": len(projects),
        "projects": projects
    }


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    """Holt Details zu einem Projekt"""
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(404, f"Projekt '{project_id}' nicht gefunden")
    
    # Füge zusätzliche Informationen hinzu, falls company_id vorhanden
    if project.get("company_id"):
        company_info = doc_manager.metadata.get(project["company_id"], {})
        project["company_info"] = company_info
    
    return {"project": project}


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, project_update: ProjectUpdate):
    """
    Aktualisiert ein Projekt
    
    Nur übergebene Felder werden aktualisiert. Team-Feld kann später ergänzt werden.
    """
    if not project_manager.project_exists(project_id):
        raise HTTPException(404, f"Projekt '{project_id}' nicht gefunden")
    
    # Validiere company_id falls angegeben
    if project_update.company_id and not doc_manager.company_exists(project_update.company_id):
        raise HTTPException(404, f"Firma '{project_update.company_id}' nicht gefunden")
    
    updated = project_manager.update_project(
        project_id=project_id,
        name=project_update.name,
        description=project_update.description,
        team_type=project_update.team_type,
        company_id=project_update.company_id,
        status=project_update.status
    )
    
    return {
        "message": "Projekt erfolgreich aktualisiert",
        "project": updated
    }


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Löscht ein Projekt"""
    if project_manager.delete_project(project_id):
        return {
            "message": "Projekt erfolgreich gelöscht",
            "project_id": project_id
        }
    raise HTTPException(404, f"Projekt '{project_id}' nicht gefunden")


# ==================== Chat API ====================

@app.post("/chat")
def chat(data: ChatIn, company_id: str):
    """
    Chat-Endpoint - erfordert company_id
    
    - **company_id**: Pflichtfeld - ID der Firma (z.B. "planovo", "acme-corp")
    """
    if not company_id:
        raise HTTPException(400, "company_id ist erforderlich")
    
    if not doc_manager.company_exists(company_id):
        raise HTTPException(
            404, 
            f"Kein Dokument für Firma '{company_id}' gefunden. Bitte laden Sie zuerst ein Dokument über /api/companies/{company_id}/documents hoch."
        )
    
    # Nutze zentrale Chat-Verarbeitungslogik
    return process_chat_query(
        query=data.message,
        doc_manager=doc_manager,
        rag_engines=rag_engines,
        default_rag=None,
        default_index=None,
        company_id=company_id,
        top_k=data.top_k,
        use_rag=data.use_rag,
        llm_router=llm_router
    )


@app.post("/api/companies/{company_id}/chat")
def chat_with_company(company_id: str, data: ChatIn):
    """
    Chat-Endpoint für spezifische Firma mit RAG
    
    - **company_id**: ID der Firma (z.B. "planovo")
    """
    if not doc_manager.company_exists(company_id):
        raise HTTPException(404, f"Kein Dokument für Firma {company_id} gefunden")
    
    # Nutze zentrale Chat-Verarbeitungslogik
    return process_chat_query(
        query=data.message,
        doc_manager=doc_manager,
        rag_engines=rag_engines,
        default_rag=None,
        default_index=None,
        company_id=company_id,
        top_k=data.top_k,
        use_rag=data.use_rag,
        llm_router=llm_router
    )
