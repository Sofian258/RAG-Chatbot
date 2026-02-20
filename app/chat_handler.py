"""Zentrale Chat-Verarbeitungslogik für alle Chat-Endpunkte"""
from typing import Optional, Dict
import logging
from app.topic_index import TopicIndex
from app.rag_engine import RAGEngine
from app.document_manager import DocumentManager
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def process_chat_query(
    query: str,
    doc_manager: DocumentManager,
    rag_engines: Dict,
    default_rag: Optional[RAGEngine],
    default_index: Optional[TopicIndex],
    company_id: Optional[str] = None,
    top_k: int = 3,
    use_rag: bool = True,
    llm_router = None
) -> Dict:
    """
    Zentrale Chat-Verarbeitungslogik
    Erfordert company_id - keine Fallback-Logik mehr
    
    Args:
        query: Benutzerfrage
        doc_manager: DocumentManager Instanz
        rag_engines: Dict mit RAG Engines
        default_rag: Nicht mehr verwendet (für Kompatibilität behalten)
        default_index: Nicht mehr verwendet (für Kompatibilität behalten)
        company_id: Pflichtfeld - Firma-ID für firmenspezifische Dokumente
        top_k: Anzahl relevanter Dokumente
        use_rag: Ob RAG verwendet werden soll
        llm_router: LLM Router Instanz
    
    Returns:
        Dict mit answer, mode, rsq, sources, etc.
    """
    from app.main import format_chunk_fallback, is_greeting
    import os
    import re
    
    q = query.strip()
    
    # Greeting Check
    if is_greeting(q):
        return {
            "answer": "Hallo! Womit kann ich Ihnen helfen?",
            "mode": "greeting",
        }
    
    # WICHTIG: company_id ist jetzt Pflichtfeld
    if not company_id:
        raise HTTPException(400, "company_id ist erforderlich")
    
    if not doc_manager.company_exists(company_id):
        raise HTTPException(
            404, 
            f"Kein Dokument für Firma '{company_id}' gefunden. Bitte laden Sie zuerst ein Dokument über /api/companies/{company_id}/documents hoch."
        )
    
    # Index und RAG Engine auswählen (nur für company_id)
    index = doc_manager.get_index(company_id)
    if not index:
        raise HTTPException(500, f"Index für Firma '{company_id}' konnte nicht geladen werden")
    
    rag_engine = rag_engines.get(company_id)
    if not rag_engine:
        use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
        rag_engine = RAGEngine(index, use_local=use_local, llm_router=llm_router)
        rag_engines[company_id] = rag_engine
    
    # Retrieval: Suche relevante Dokumenten-Abschnitte
    search_top_k = min(top_k + 1, 5)
    hits = index.search(q, top_k=search_top_k)
    rsq = index.rsq_from_hits(hits)
    
    # ChatGPT-Style: RAG für ALLE Fragen
    context_chunks = [h.doc for h in hits] if hits else []
    
    if context_chunks:
        if rag_engine and use_rag:
            try:
                # WICHTIG: company_id übergeben für Prompt-Auswahl
                answer = rag_engine.generate_answer(
                    q, 
                    context_chunks, 
                    rsq, 
                    use_rag=True,
                    company_id=company_id  # Für Planovo-spezifischen Prompt
                )
                mode = "rag"
            except Exception as e:
                logger.error(f"RAG Error: {e}", exc_info=True)
                print(f"RAG Error: {e}, Fallback zu intelligenter Extraktion")
                # Fallback: Intelligente Extraktion
                extracted = rag_engine._extract_simple_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar.")) if rag_engine else None
                if not extracted and rag_engine:
                    extracted = rag_engine._extract_smart_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar."))
                chunk_text = context_chunks[0].get("text", "")
                is_extracted = extracted and extracted != chunk_text and len(extracted) < len(chunk_text) * 0.5
                if is_extracted:
                    answer = extracted
                    mode = "retrieval_fallback"
                else:
                    if rsq < 0.05:
                        answer = "Dazu habe ich leider keine Informationen. Können Sie die Frage anders formulieren? Oder sagen Sie mir, wobei ich Ihnen konkret helfen kann."
                        mode = "low_relevance"
                    else:
                        # Fallback: Intelligente Extraktion statt roher Chunk
                        chunk_text = context_chunks[0].get("text", "Keine Antwort verfügbar.")
                        extracted = rag_engine._extract_smart_answer(q, chunk_text) if rag_engine else None
                        if extracted and len(extracted) > 10:
                            answer = extracted
                        else:
                            # Letzter Fallback: Erste 2-3 Sätze extrahieren
                            sentences = re.split(r'[.!?]+', chunk_text)
                            relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
                            if relevant_sentences:
                                answer = '. '.join(relevant_sentences) + '.'
                            else:
                                answer = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                        # Post-Filter für Planovo
                        if company_id and company_id.lower() == "planovo" and rag_engine:
                            answer = rag_engine.clean_answer(answer, company_id)
                        mode = "retrieval_fallback"
        else:
            # Wenn RAG nicht verfügbar: Intelligente Extraktion
            extracted = rag_engine._extract_simple_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar.")) if rag_engine else None
            if not extracted and rag_engine:
                extracted = rag_engine._extract_smart_answer(q, context_chunks[0].get("text", "Keine Antwort verfügbar."))
            chunk_text = context_chunks[0].get("text", "")
            is_extracted = extracted and extracted != chunk_text and len(extracted) < len(chunk_text) * 0.5
            
            if is_extracted:
                answer = extracted
                mode = "retrieval_fast"
            else:
                if rsq < 0.05:
                    answer = "Dazu habe ich leider keine Informationen. Können Sie die Frage anders formulieren? Oder sagen Sie mir, wobei ich Ihnen konkret helfen kann."
                    mode = "low_relevance"
                else:
                    # Fallback: Intelligente Extraktion statt roher Chunk
                    chunk_text = context_chunks[0].get("text", "Keine Antwort verfügbar.")
                    extracted = rag_engine._extract_smart_answer(q, chunk_text) if rag_engine else None
                    if extracted and len(extracted) > 10:
                        answer = extracted
                    else:
                        # Letzter Fallback: Erste 2-3 Sätze extrahieren
                        sentences = re.split(r'[.!?]+', chunk_text)
                        relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
                        if relevant_sentences:
                            answer = '. '.join(relevant_sentences) + '.'
                        else:
                            answer = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                    # Post-Filter für Planovo
                    if company_id and company_id.lower() == "planovo" and rag_engine:
                        answer = rag_engine.clean_answer(answer, company_id)
                    mode = "retrieval"
    else:
        # Nur wenn wirklich keine Daten gefunden wurden
        return {
            "answer": "Dazu habe ich keine Informationen gefunden. Können Sie die Frage anders formulieren? Oder sagen Sie mir, wobei ich Ihnen helfen kann.",
            "rsq": rsq,
            "mode": "fallback",
        }
    
    # Quellen nur zurückgeben wenn NICHT Planovo (Support-Bot braucht keine Quellen)
    return_sources = [] if (company_id and company_id.lower() == "planovo") else [
        {
            "title": h.doc.get("title"),
            "score": round(h.score, 3),
            "source_id": h.doc.get("id"),
        }
        for h in hits
    ]
    
    return {
        "answer": answer,
        "topic": context_chunks[0].get("title") if context_chunks else None,
        "rsq": rsq,
        "mode": mode,
        "sources": return_sources,  # Leer für Planovo
    }
