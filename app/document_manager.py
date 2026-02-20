"""Document Manager für dynamisches Laden und Verwalten von Dokumenten"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Union
from app.doc_loader import load_sections_from_txt, load_sections_from_pdf, load_sections_from_image
from app.topic_index import TopicIndex
from app.vector_index import VectorIndex
import json
import os


class DocumentManager:
    """Verwaltet Dokumente für verschiedene Firmen (Multi-Tenant)"""
    
    def __init__(self, storage_dir: str = "documents", use_vector_db: bool = True):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.use_vector_db = use_vector_db
        self.indices: Dict[str, Union[TopicIndex, VectorIndex]] = {}  # company_id -> index
        self.vector_indices: Dict[str, VectorIndex] = {}  # company_id -> VectorIndex (für schnellen Zugriff)
        self.metadata: Dict[str, dict] = {}  # company_id -> metadata
        self._load_metadata()
    
    def _load_metadata(self):
        """Lädt gespeicherte Metadaten"""
        metadata_file = self.storage_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                
                # WICHTIG: Lade Indizes für alle vorhandenen Dokumente neu
                self._reload_indices()
            except Exception as e:
                print(f"Fehler beim Laden der Metadaten: {e}")
                self.metadata = {}
    
    def _reload_indices(self):
        """Lädt alle Indizes aus gespeicherten Dokumenten neu (nach Neustart)"""
        for company_id, meta in self.metadata.items():
            file_path = meta.get("file_path")
            if file_path and Path(file_path).exists():
                try:
                    # Lade Dokument und erstelle Index neu (basierend auf Dateityp)
                    file_ext = file_path.lower().split('.')[-1] if '.' in file_path else ''
                    
                    if file_ext == 'pdf':
                        sections = load_sections_from_pdf(file_path)
                    elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
                        sections = load_sections_from_image(file_path)
                    else:
                        sections = load_sections_from_txt(file_path)
                    if sections:
                        # Erstelle Index (VectorIndex mit lokalen Embeddings oder TopicIndex)
                        use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
                        # Multi-Modell Router (wird in main.py übergeben)
                        llm_router = None  # Wird von main.py gesetzt
                        if self.use_vector_db:
                            try:
                                if use_local:
                                    index = VectorIndex(company_id, sections, use_local=True)
                                else:
                                    api_key = os.getenv("OPENAI_API_KEY")
                                    index = VectorIndex(company_id, sections, use_local=False, api_key=api_key)
                                
                                if isinstance(index, VectorIndex):
                                    self.vector_indices[company_id] = index
                                print(f"✓ VectorIndex für {company_id} neu geladen ({len(sections)} Abschnitte)")
                            except Exception as e:
                                print(f"⚠ Fehler beim Laden von VectorIndex, nutze TopicIndex: {e}")
                                index = TopicIndex(sections)
                        else:
                            index = TopicIndex(sections)
                        self.indices[company_id] = index
                        print(f"✓ Index für {company_id} neu geladen ({len(sections)} Abschnitte)")
                    else:
                        print(f"⚠ Warnung: Keine Abschnitte für {company_id} gefunden")
                except Exception as e:
                    print(f"✗ Fehler beim Neuladen des Index für {company_id}: {e}")
            else:
                print(f"⚠ Datei für {company_id} nicht gefunden: {file_path}")
    
    def _save_metadata(self):
        """Speichert Metadaten"""
        metadata_file = self.storage_dir / "metadata.json"
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Metadaten: {e}")
    
    def upload_document(
        self, 
        company_id: str, 
        file_content: Union[str, bytes], 
        filename: str
    ) -> dict:
        """
        Lädt ein Dokument hoch und erstellt Index
        
        Unterstützt:
        - TXT-Dateien (als String)
        - PDF-Dateien (als bytes)
        - Bilddateien (jpg, png, etc. als bytes) - mit OCR
        
        Args:
            company_id: Eindeutige ID der Firma
            file_content: Inhalt der Datei als String (TXT) oder bytes (PDF/Bilder)
            filename: Original-Dateiname
        
        Returns:
            Dict mit Upload-Status
        """
        # Speichere Dokument
        doc_path = self.storage_dir / f"{company_id}_{filename}"
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        
        # Bestimme Dateityp und speichere entsprechend
        if file_ext == 'pdf':
            # PDF als Binary speichern
            if isinstance(file_content, str):
                file_content = file_content.encode('utf-8')
            doc_path.write_bytes(file_content)
        elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            # Bild als Binary speichern
            if isinstance(file_content, str):
                file_content = file_content.encode('latin-1')  # Für Bilder
            doc_path.write_bytes(file_content)
        else:
            # TXT als Text speichern
            if isinstance(file_content, bytes):
                file_content = file_content.decode("utf-8")
            doc_path.write_text(file_content, encoding="utf-8")
        
        # Parse Dokument basierend auf Dateityp
        if file_ext == 'pdf':
            sections = load_sections_from_pdf(str(doc_path))
        elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
            sections = load_sections_from_image(str(doc_path))
        else:
            # TXT oder unbekannter Typ - versuche als TXT
            sections = load_sections_from_txt(str(doc_path))
        
        if not sections:
            return {
                "company_id": company_id,
                "status": "error",
                "message": f"Dokument konnte nicht geparst werden (Typ: {file_ext})"
            }
        
        # Erstelle Index (VectorIndex mit lokalen Embeddings oder TopicIndex)
        use_local = os.getenv("USE_LOCAL_MODELS", "true").lower() == "true"
        if self.use_vector_db:
            try:
                if use_local:
                    index = VectorIndex(company_id, sections, use_local=True)
                else:
                    api_key = os.getenv("OPENAI_API_KEY")
                    index = VectorIndex(company_id, sections, use_local=False, api_key=api_key)
                
                if isinstance(index, VectorIndex):
                    self.vector_indices[company_id] = index
                print(f"✓ VectorIndex für {company_id} erstellt")
            except Exception as e:
                print(f"⚠ Fehler beim Erstellen von VectorIndex, nutze TopicIndex: {e}")
                index = TopicIndex(sections)
        else:
            index = TopicIndex(sections)
        self.indices[company_id] = index
        
        # Speichere Metadata
        self.metadata[company_id] = {
            "filename": filename,
            "sections_count": len(sections),
            "file_path": str(doc_path),
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        self._save_metadata()
        
        return {
            "company_id": company_id,
            "sections": len(sections),
            "status": "uploaded",
            "filename": filename
        }
    
    def get_index(self, company_id: str) -> Optional[Union[TopicIndex, VectorIndex]]:
        """Holt Index für eine Firma (VectorIndex oder TopicIndex)"""
        return self.indices.get(company_id)
    
    def get_vector_index(self, company_id: str) -> Optional[VectorIndex]:
        """Holt VectorIndex für eine Firma (falls vorhanden)"""
        return self.vector_indices.get(company_id)
    
    def update_document(
        self, 
        company_id: str, 
        file_content: Union[str, bytes], 
        filename: str
    ) -> dict:
        """Aktualisiert Dokument (ersetzt altes)"""
        # Lösche alte Datei falls vorhanden
        if company_id in self.metadata:
            old_path = self.metadata[company_id].get("file_path")
            if old_path and Path(old_path).exists():
                Path(old_path).unlink()
        
        return self.upload_document(company_id, file_content, filename)
    
    def delete_document(self, company_id: str) -> bool:
        """Löscht Dokument und Index"""
        if company_id in self.indices:
            del self.indices[company_id]
            
            # Lösche VectorIndex falls vorhanden
            if company_id in self.vector_indices:
                # ChromaDB Collection löschen
                try:
                    vector_index = self.vector_indices[company_id]
                    vector_index.chroma_client.delete_collection(
                        name=f"documents_{company_id}"
                    )
                except Exception as e:
                    print(f"⚠ Fehler beim Löschen der ChromaDB Collection: {e}")
                del self.vector_indices[company_id]
            
            # Lösche Datei
            if company_id in self.metadata:
                file_path = self.metadata[company_id].get("file_path")
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                del self.metadata[company_id]
                self._save_metadata()
            
            # Lösche ChromaDB Verzeichnis
            chroma_dir = Path(f"./chroma_db/{company_id}")
            if chroma_dir.exists():
                import shutil
                try:
                    shutil.rmtree(chroma_dir)
                except Exception as e:
                    print(f"⚠ Fehler beim Löschen des ChromaDB Verzeichnisses: {e}")
            
            return True
        return False
    
    def list_companies(self) -> List[dict]:
        """Listet alle Firmen mit Dokumenten"""
        return [
            {
                "company_id": cid,
                **meta
            }
            for cid, meta in self.metadata.items()
        ]
    
    def company_exists(self, company_id: str) -> bool:
        """Prüft ob Firma existiert"""
        return company_id in self.indices
