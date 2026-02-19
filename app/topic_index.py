from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class TopicHit:
    doc: Dict
    score: float


class TopicIndex:
    def __init__(self, docs: List[Dict]):
        self.docs = docs
        # Optimierte TF-IDF Konfiguration für besseres Retrieval
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),  # Einzelwörter + Bigramme für bessere semantische Erfassung
            min_df=1,  # Mindestens 1 Dokument (keine Filterung)
            max_df=0.95,  # Ignoriere Wörter, die in >95% der Dokumente vorkommen (Stopwords)
            analyzer='word',  # Wort-basierte Analyse
            token_pattern=r'(?u)\b\w+\b',  # Erkenne Wörter mit Unicode-Unterstützung
        )
        self.doc_matrix = self.vectorizer.fit_transform([d["text"] for d in docs])

    def search(self, query: str, top_k: int = 3) -> List[TopicHit]:
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.doc_matrix)[0]  # (n_docs,)
        idx = np.argsort(-sims)[:top_k]
        return [TopicHit(self.docs[i], float(sims[i])) for i in idx]

    @staticmethod
    def rsq_from_hits(hits: List[TopicHit]) -> float:
        # RSQ = absoluter bester Score + Abstand zum zweitbesten (Margin)
        if not hits:
            return 0.0
        best = hits[0].score
        second = hits[1].score if len(hits) > 1 else 0.0
        margin = max(0.0, best - second)

        rsq = 0.75 * best + 0.25 * margin
        return float(max(0.0, min(1.0, round(rsq, 3))))
    
    def get_by_title(self, title: str):
        t = (title or "").strip().upper()
        for d in self.docs:
            if (d.get("title") or "").strip().upper() == t:
                return d
        return None

