"""Lokale Embeddings mit sentence-transformers"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
import os


class LocalEmbeddingModel:
    """Lokales Embedding-Modell für ChromaDB"""
    
    def __init__(self, model_name: str = None):
        """
        Initialisiert lokales Embedding-Modell
        
        Args:
            model_name: Name des Modells (optional, sonst aus ENV)
        
        Empfohlene deutsche Modelle:
        - "paraphrase-multilingual-MiniLM-L12-v2" (klein, schnell, gut für DE)
        - "paraphrase-multilingual-mpnet-base-v2" (größer, besser)
        - "intfloat/multilingual-e5-base" (sehr gut für DE)
        """
        default_model = os.getenv(
            "EMBEDDING_MODEL", 
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.model_name = model_name or default_model
        
        print(f"Lade lokales Embedding-Modell: {self.model_name}...")
        try:
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✓ Embedding-Modell geladen (Dimension: {self.dimension})")
        except Exception as e:
            print(f"✗ Fehler beim Laden des Embedding-Modells: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Erstellt Embeddings für Text(e)
        
        Args:
            texts: Einzelner Text oder Liste von Texten
        
        Returns:
            Liste von Embedding-Vektoren
        """
        if isinstance(texts, str):
            texts = [texts]
        
        try:
            embeddings = self.model.encode(
                texts, 
                convert_to_numpy=True,
                normalize_embeddings=True  # Wichtig für ChromaDB (Cosine Similarity)
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"Fehler beim Erstellen der Embeddings: {e}")
            raise
    
    def encode_single(self, text: str) -> List[float]:
        """
        Erstellt Embedding für einen einzelnen Text
        
        Args:
            text: Text zum Embedden
        
        Returns:
            Embedding-Vektor
        """
        return self.encode(text)[0]
