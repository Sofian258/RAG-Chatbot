from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import re
from typing import Dict, Optional

from app.doc_loader import load_sections_from_txt
from app.topic_index import TopicIndex
from app.document_manager import DocumentManager
from app.rag_engine import RAGEngine

app = FastAPI(
    title="RAG Chatbot API",
    description="Wiederverwendbarer RAG-Chatbot mit dynamischem Dokumenten-Management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Document Manager für Multi-Tenant-Support
doc_manager = DocumentManager()
rag_engines: Dict[str, RAGEngine] = {}  # company_id -> RAGEngine

# Fallback: Lade Standard-Dokument für Kompatibilität
try:
    DOCS = load_sections_from_txt("app/company_doc.txt")
    default_index = TopicIndex(DOCS)
    use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
    default_rag = RAGEngine(default_index, use_local=use_local)
except Exception as e:
    print(f"Warnung: Standard-Dokument konnte nicht geladen werden: {e}")
    default_index = None
    default_rag = None


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(3, ge=1, le=5)
    use_rag: bool = Field(True, description="Nutze RAG für Antwort-Generierung")


def is_greeting(text: str) -> bool:
    return text.strip().lower() in {
        "hallo", "hi", "hey",
        "guten tag", "guten morgen",
        "guten abend", "servus", "moin"
    }




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
            "company_info": "/api/companies/{company_id}"
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
    use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
    index = doc_manager.get_index(company_id)
    if index:
        rag_engines[company_id] = RAGEngine(index, use_local=use_local)
    
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
    use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
    index = doc_manager.get_index(company_id)
    if index:
        rag_engines[company_id] = RAGEngine(index, use_local=use_local)
    
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


# ==================== Chat API ====================

@app.post("/chat")
def chat(data: ChatIn, company_id: Optional[str] = None):
    """
    Chat-Endpoint (Kompatibilität: ohne company_id nutzt Standard-Dokument)
    
    - **company_id**: Optional - Wenn angegeben, nutze Dokument dieser Firma
    """
    q = data.message.strip()

    # 1) Greeting Check
    if is_greeting(q):
        return {
            "answer": "Hallo! Wie kann ich dir helfen?",
            "mode": "greeting",
        }

    # Wähle Index und RAG Engine
    if company_id and doc_manager.company_exists(company_id):
        index = doc_manager.get_index(company_id)
        rag_engine = rag_engines.get(company_id)
        if not rag_engine:
            use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
            rag_engine = RAGEngine(index, use_local=use_local)
            rag_engines[company_id] = rag_engine
    else:
        # Fallback auf Standard-Dokument
        if not default_index:
            raise HTTPException(500, "Kein Dokument verfügbar")
        index = default_index
        rag_engine = default_rag

    # 2) Retrieval: Suche relevante Dokumenten-Abschnitte (datengetrieben, keine vordefinierten Fragen)
    # Nutze mehr Chunks für besseren Kontext, besonders bei komplexen Fragen
    search_top_k = min(data.top_k + 1, 5)  # Ein zusätzlicher Chunk für mehr Kontext
    hits = index.search(q, top_k=search_top_k)
    rsq = index.rsq_from_hits(hits)

    # 3) ChatGPT-Style: RAG für ALLE Fragen (wenn aktiviert)
    context_chunks = [h.doc for h in hits] if hits else []
    
    if context_chunks:
        # RAG IMMER nutzen wenn aktiviert (wie ChatGPT - intelligente Antworten auf alle Fragen)
        if rag_engine and data.use_rag:
            try:
                answer = rag_engine.generate_answer(q, context_chunks, rsq, use_rag=True)
                mode = "rag"
            except Exception as e:
                print(f"RAG Error: {e}, Fallback zu intelligenter Extraktion")
                # Fallback: Intelligente Extraktion
                extracted = rag_engine._extract_simple_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar.")) if rag_engine else None
                if not extracted and rag_engine:
                    extracted = rag_engine._extract_smart_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar."))
                chunk_text = context_chunks[0].get("text", "")
                is_extracted = extracted != chunk_text and len(extracted) < len(chunk_text) * 0.5
                if is_extracted:
                    answer = extracted
                    mode = "retrieval_fallback"
                else:
                    if rsq < 0.05:
                        answer = (
                            "Die Dokumente enthalten keine ausreichend relevanten Informationen zu Ihrer Frage. "
                            "Bitte formulieren Sie die Frage anders oder kontaktieren Sie den Support."
                        )
                        mode = "low_relevance"
                    else:
                        answer = context_chunks[0].get("text", "Keine Antwort verfügbar.")
                        mode = "retrieval_fallback"
        else:
            # Wenn RAG nicht verfügbar: Intelligente Extraktion
            extracted = rag_engine._extract_simple_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar.")) if rag_engine else None
            if not extracted and rag_engine:
                extracted = rag_engine._extract_smart_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar."))
            chunk_text = context_chunks[0].get("text", "")
            is_extracted = extracted != chunk_text and len(extracted) < len(chunk_text) * 0.5
            
            if is_extracted:
                answer = extracted
                mode = "retrieval_fast"
            else:
                if rsq < 0.05:
                    answer = (
                        "Die Dokumente enthalten keine ausreichend relevanten Informationen zu Ihrer Frage. "
                        "Bitte formulieren Sie die Frage anders oder kontaktieren Sie den Support."
                    )
                    mode = "low_relevance"
                else:
                    answer = context_chunks[0].get("text", "Keine Antwort verfügbar.")
                    mode = "retrieval"
    else:
        # Nur wenn wirklich keine Daten gefunden wurden
        return {
            "answer": (
                "Ich habe dazu keine Informationen im Firmendokument gefunden. "
                "Bitte formuliere deine Frage anders oder kontaktiere den Support."
            ),
            "rsq": rsq,
            "mode": "fallback",
        }

    return {
        "answer": answer,
        "topic": context_chunks[0].get("title"),
        "rsq": rsq,
        "mode": mode,
        "sources": [
            {
                "title": h.doc.get("title"),
                "score": round(h.score, 3),
                "source_id": h.doc.get("id"),
            }
            for h in hits
        ],
    }


@app.post("/api/companies/{company_id}/chat")
def chat_with_company(company_id: str, data: ChatIn):
    """
    Chat-Endpoint für spezifische Firma mit RAG
    
    - **company_id**: ID der Firma
    """
    if not doc_manager.company_exists(company_id):
        raise HTTPException(404, f"Kein Dokument für Firma {company_id} gefunden")
    
    q = data.message.strip()

    # 1) Greeting Check
    if is_greeting(q):
        return {
            "answer": "Hallo! Wie kann ich dir helfen?",
            "mode": "greeting",
        }

    # Hole Index und RAG Engine
    index = doc_manager.get_index(company_id)
    rag_engine = rag_engines.get(company_id)
    
    if not rag_engine:
        use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
        rag_engine = RAGEngine(index, use_local=use_local)
        rag_engines[company_id] = rag_engine

    # 2) Retrieval: Datengetriebene Suche (keine vordefinierten Fragen)
    # Nutze mehr Chunks für besseren Kontext, besonders bei komplexen Fragen
    search_top_k = min(data.top_k + 1, 5)  # Ein zusätzlicher Chunk für mehr Kontext
    hits = index.search(q, top_k=search_top_k)
    rsq = index.rsq_from_hits(hits)

    # 3) Retrieval: Hole relevante Chunks
    context_chunks = [h.doc for h in hits] if hits else []
    
    if not context_chunks:
        return {
            "answer": "Ich habe dazu keine Informationen gefunden.",
            "rsq": rsq,
            "mode": "no_results"
        }
    
    # 4) ALLE Logik in RAGEngine.generate_answer()
    try:
        answer = rag_engine.generate_answer(q, context_chunks, rsq, use_rag=data.use_rag)
        mode = "rag" if data.use_rag else "extraction"
    except Exception as e:
        print(f"Error: {e}")
        answer = "Fehler bei der Antwort-Generierung."
        mode = "error"
    
    return {
        "answer": answer,
        "rsq": rsq,
        "mode": mode,
        "sources": [
            {
                "title": h.doc.get("title"),
                "score": round(h.score, 3),
                "source_id": h.doc.get("id"),
            }
            for h in hits
        ],
    }
