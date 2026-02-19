"""Vector Index mit ChromaDB und lokalen/OpenAI Embeddings"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, TYPE_CHECKING
import os

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠ ChromaDB nicht installiert. Installiere mit: pip install chromadb")

if TYPE_CHECKING:
    from app.local_embeddings import LocalEmbeddingModel

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class VectorHit:
    doc: Dict
    score: float


class VectorIndex:
    """Vektordatenbank-basierter Index mit lokalen/OpenAI Embeddings"""
    
    def __init__(
        self, 
        company_id: str, 
        docs: List[Dict], 
        use_local: bool = True,
        embedding_model: Optional["LocalEmbeddingModel"] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialisiert VectorIndex mit ChromaDB
        
        Args:
            company_id: Eindeutige ID der Firma (für Collection-Name)
            docs: Liste von Dokumenten-Abschnitten
            use_local: Wenn True, nutze lokale Embeddings, sonst OpenAI
            embedding_model: Lokales Embedding-Modell (optional, wird erstellt wenn None)
            api_key: OpenAI API Key für Embeddings (nur wenn use_local=False)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB ist nicht installiert. Bitte installiere: pip install chromadb")
        
        self.company_id = company_id
        self.docs = docs
        self.use_local = use_local
        
        # Lokale Embeddings oder OpenAI
        if use_local:
            if embedding_model is None:
                from app.local_embeddings import LocalEmbeddingModel
                embedding_model = LocalEmbeddingModel()
            self.embedding_model = embedding_model
            self.client = None
            self.api_key = None
        else:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI nicht verfügbar. Nutze use_local=True für lokale Embeddings.")
            self.embedding_model = None
            self.api_key = api_key
            self.client = OpenAI(api_key=api_key) if api_key else None
        
        # ChromaDB Client initialisieren (persistent)
        persist_directory = f"./chroma_db/{company_id}"
        os.makedirs(persist_directory, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Collection für diese Firma erstellen oder laden
        collection_name = f"documents_{company_id}"
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            print(f"✓ ChromaDB Collection '{collection_name}' geladen")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"company_id": company_id}
            )
            print(f"✓ ChromaDB Collection '{collection_name}' erstellt")
        
        # Dokumente in Vektordatenbank speichern
        self._index_documents(docs)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Erstellt Embedding für Text - lokal oder OpenAI"""
        if self.use_local and self.embedding_model:
            try:
                return self.embedding_model.encode_single(text)
            except Exception as e:
                print(f"Fehler beim Erstellen des lokalen Embeddings: {e}")
                raise
        elif self.client:
            try:
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"Fehler beim Erstellen des OpenAI Embeddings: {e}")
                raise
        else:
            raise ValueError("Kein Embedding-Modell verfügbar. Setze use_local=True oder api_key.")
    
    def _index_documents(self, docs: List[Dict]):
        """Indexiert Dokumente in ChromaDB"""
        if not docs:
            return
        
        # Prüfe ob Collection bereits Dokumente enthält
        existing_count = self.collection.count()
        if existing_count > 0:
            print(f"Collection enthält bereits {existing_count} Dokumente. Lösche alte Collection für Update...")
            # Lösche alte Collection für konsistente Updates
            try:
                self.chroma_client.delete_collection(name=self.collection.name)
                # Erstelle neue Collection
                self.collection = self.chroma_client.create_collection(
                    name=self.collection.name,
                    metadata={"company_id": self.company_id}
                )
                print(f"✓ Alte Collection gelöscht, neue Collection erstellt")
            except Exception as e:
                print(f"⚠ Fehler beim Löschen der Collection: {e}")
                return
        
        print(f"Indexiere {len(docs)} Dokumente in ChromaDB...")
        
        # Batch-Processing für bessere Performance
        batch_size = 100
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, doc in enumerate(docs):
            doc_id = f"{self.company_id}_{doc.get('id', i)}"
            text = doc.get("text", "")
            title = doc.get("title", "Unbekannt")
            
            if not text.strip():
                continue
            
            # Embedding erstellen
            try:
                embedding = self._get_embedding(text)
            except Exception as e:
                print(f"Fehler bei Dokument {i}: {e}")
                continue
            
            ids.append(doc_id)
            embeddings.append(embedding)
            documents.append(text)
            metadatas.append({
                "title": title,
                "doc_id": doc.get("id", ""),
                "index": i
            })
            
            # Batch hinzufügen wenn voll
            if len(ids) >= batch_size:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                ids, embeddings, documents, metadatas = [], [], [], []
                print(f"  {i+1}/{len(docs)} Dokumente indexiert...")
        
        # Rest hinzufügen
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
        
        print(f"✓ {len(docs)} Dokumente erfolgreich in ChromaDB indexiert")
    
    def search(self, query: str, top_k: int = 3) -> List[VectorHit]:
        """
        Sucht ähnliche Dokumente mit semantischer Suche
        
        Args:
            query: Suchanfrage
            top_k: Anzahl der Ergebnisse
            
        Returns:
            Liste von VectorHit-Objekten
        """
        # Erstelle Query-Embedding (lokal oder OpenAI)
        try:
            query_embedding = self._get_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
        except Exception as e:
            print(f"Fehler bei der Suche: {e}")
            # Fallback: Nutze ChromaDB's eigene Embedding-Funktion (wenn verfügbar)
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k
                )
            except Exception as e2:
                print(f"Fallback-Suche fehlgeschlagen: {e2}")
                return []
        
        hits = []
        if results and results.get("ids") and len(results["ids"][0]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                # Finde Original-Dokument
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distances = results["distances"][0] if results.get("distances") else []
                
                # Konvertiere Distanz zu Similarity-Score (1 - normalized distance)
                distance = distances[i] if i < len(distances) else 1.0
                # ChromaDB verwendet L2-Distanz, konvertiere zu Similarity (0-1)
                similarity = max(0.0, 1.0 - min(1.0, distance))
                
                # Finde Original-Dokument
                doc_index = metadata.get("index", -1)
                if doc_index >= 0 and doc_index < len(self.docs):
                    doc = self.docs[doc_index]
                else:
                    # Fallback: Erstelle Dokument aus Metadaten
                    doc = {
                        "id": metadata.get("doc_id", doc_id),
                        "title": metadata.get("title", "Unbekannt"),
                        "text": results["documents"][0][i] if results.get("documents") else ""
                    }
                
                hits.append(VectorHit(doc=doc, score=float(similarity)))
        
        return hits
    
    @staticmethod
    def rsq_from_hits(hits: List[VectorHit]) -> float:
        """Berechnet RSQ (Relevance Score Quality) aus Hits"""
        if not hits:
            return 0.0
        best = hits[0].score
        second = hits[1].score if len(hits) > 1 else 0.0
        margin = max(0.0, best - second)
        
        rsq = 0.75 * best + 0.25 * margin
        return float(max(0.0, min(1.0, round(rsq, 3))))
    
    def get_by_title(self, title: str) -> Optional[Dict]:
        """Findet Dokument nach Titel"""
        t = (title or "").strip().upper()
        for d in self.docs:
            if (d.get("title") or "").strip().upper() == t:
                return d
        return None
