"""RAG Engine für Retrieval-Augmented Generation - nur lokale LLMs"""
import os
import re
from typing import List, Dict, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from app.vector_index import VectorIndex

from app.topic_index import TopicIndex


class RAGEngine:
    """RAG Engine kombiniert Retrieval mit lokaler LLM-Generierung"""
    
    def __init__(
        self, 
        index: Union[TopicIndex, "VectorIndex"], 
        use_local: bool = True,
        llm: Optional["LocalLLM"] = None
    ):
        """
        Initialisiert RAG Engine (nur lokale LLMs)
        
        Args:
            index: Index für Dokumentensuche
            use_local: Wenn True, nutze lokales LLM (Standard: True)
            llm: Lokales LLM (optional, wird erstellt wenn None)
        """
        self.index = index
        self.use_local = use_local
        
        if use_local:
            if llm is None:
                from app.local_llm import LocalLLM
                llm = LocalLLM()  # Hauptmodell (qwen2.5:7b)
            self.llm = llm
            # Schnelles Modell für einfache Fragen
            fast_model = os.getenv("LLM_FAST_MODEL", "qwen2.5:3b")
            self.fast_llm = LocalLLM(model=fast_model, fallback_model=os.getenv("LLM_FALLBACK_MODEL", "llama3.2:1b"))
        else:
            raise ValueError("Nur lokale LLMs werden unterstützt. Setze use_local=True.")
    
    def _extract_simple_answer(self, query: str, chunk_text: str) -> Optional[str]:
        """
        Extrahiert Antwort für einfache Business-Fragen direkt aus dem Chunk
        Returns NUR den Wert (z.B. "35.574,00 €") ohne zusätzlichen Text
        Returns None wenn keine einfache Frage erkannt wurde
        """
        query_lower = query.lower()
        
        # Gesamtbetrag - NUR Wert zurückgeben
        if "gesamtbetrag" in query_lower or ("wie hoch" in query_lower and "betrag" in query_lower):
            normalized_text = re.sub(r'\s+', ' ', chunk_text)
            betrag_match = re.search(r'Gesamtbetrag[:\s]*([\d.,]+\s*€)', normalized_text, re.IGNORECASE)
            if betrag_match:
                return betrag_match.group(1).strip()  # NUR Wert
        
        # Nettobetrag - NUR Wert zurückgeben
        if "nettobetrag" in query_lower:
            normalized_text = re.sub(r'\s+', ' ', chunk_text)
            betrag_match = re.search(r'Nettobetrag[:\s]*([\d.,]+\s*€)', normalized_text, re.IGNORECASE)
            if betrag_match:
                return betrag_match.group(1).strip()  # NUR Wert
        
        # Skonto - NUR Prozentsatz oder berechneter Wert
        if "skonto" in query_lower or "spare" in query_lower or ("wie viel" in query_lower and "spare" in query_lower):
            normalized_text = re.sub(r'\s+', ' ', chunk_text)
            skonto_match = re.search(r'(\d+)\s*%\s*Skonto', normalized_text, re.IGNORECASE)
            if skonto_match:
                skonto_prozent = int(skonto_match.group(1))
                # Suche nach Gesamtbetrag für Berechnung
                betrag_match = re.search(r'Gesamtbetrag[:\s]*([\d.,]+)\s*€', normalized_text, re.IGNORECASE)
                if betrag_match:
                    betrag_str = betrag_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        betrag = float(betrag_str)
                        skonto_betrag = betrag * (skonto_prozent / 100)
                        return f"{skonto_betrag:,.2f} €"  # NUR berechneter Wert
                    except:
                        pass
                return f"{skonto_prozent}%"  # NUR Prozentsatz
        
        # Datum - NUR Datum zurückgeben
        if "datum" in query_lower or "wann" in query_lower:
            if "fällig" in query_lower or "bis" in query_lower:
                fällig_match = re.search(r'(?:bis zum|fällig|bis)\s+(\d{1,2}\.\d{1,2}\.\d{4})', chunk_text, re.IGNORECASE)
                if fällig_match:
                    return fällig_match.group(1)  # NUR Datum
            # Rechnungsdatum
            date_match = re.search(r'Rechnungsdatum[:\s]*(\d{1,2}\.\d{1,2}\.\d{4})', chunk_text, re.IGNORECASE)
            if date_match:
                return date_match.group(1)  # NUR Datum
            # Fallback: Erstes Datum
            date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', chunk_text)
            if date_match:
                return date_match.group(1)  # NUR Datum
        
        # Firma/Unternehmen - NUR Name
        if "firma" in query_lower or "unternehmen" in query_lower or ("wie heißt" in query_lower and "firma" in query_lower):
            lines = chunk_text.split('\n')
            for line in lines[:15]:
                line = line.strip()
                words = line.split()
                if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
                    if not any(word.lower() in ["ihr", "unternehmen", "rechnung", "betreff", "seite", "damen", "herren"] for word in words):
                        return line  # NUR Name
            # Fallback: Regex
            firma_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+)', chunk_text)
            if firma_match and "Ihr" not in firma_match.group(1) and "Unternehmen" not in firma_match.group(1):
                return firma_match.group(1)  # NUR Name
        
        # Rechnungsnummer - NUR Nummer
        if "rechnungsnummer" in query_lower or ("rechnung" in query_lower and "nummer" in query_lower) or "inv" in query_lower:
            inv_match = re.search(r'(?:INV|Rechnung\s+Nr\.?)\s*[:\-]?\s*([A-Z0-9\-]+)', chunk_text, re.IGNORECASE)
            if inv_match:
                return inv_match.group(1)  # NUR Nummer
        
        # Fragen nach Kapiteln/Abschnitten (z.B. "Was ist das Fazit?", "Was steht in Kapitel 3.3?")
        if "fazit" in query_lower or "ausblick" in query_lower:
            lines = chunk_text.split('\n')
            relevant_lines = []
            found_keyword = False
            for line in lines:
                line_lower = line.lower()
                if ("fazit" in line_lower or "ausblick" in line_lower) and len(line.strip()) > 5:
                    found_keyword = True
                if found_keyword and len(line.strip()) > 10:
                    relevant_lines.append(line.strip())
                    if len(relevant_lines) >= 5:
                        break
            if relevant_lines:
                return '\n'.join(relevant_lines[:3])
        
        # Fragen nach spezifischen Kapiteln
        chapter_match = re.search(r'kapitel\s+(\d+\.\d+)', query_lower)
        if chapter_match:
            chapter_num = chapter_match.group(1)
            lines = chunk_text.split('\n')
            for i, line in enumerate(lines):
                if chapter_num in line and len(line.strip()) > 5:
                    relevant = [line.strip()]
                    for j in range(i+1, min(i+6, len(lines))):
                        if len(lines[j].strip()) > 10:
                            relevant.append(lines[j].strip())
                    if len(relevant) > 1:
                        return '\n'.join(relevant[:4])
        
        return None
    
    def _extract_smart_answer(self, query: str, chunk_text: str) -> Optional[str]:
        """
        Intelligente Extraktion für allgemeine Fragen - extrahiert relevante Teile
        """
        query_lower = query.lower()
        
        # Fragen nach "was ist X" oder "was bedeutet X"
        if "was ist" in query_lower or "was bedeutet" in query_lower:
            match = re.search(r'was (ist|bedeutet)\s+(.+?)(?:\?|$)', query_lower)
            if match:
                search_term = match.group(2).strip()
                lines = chunk_text.split('\n')
                relevant_lines = []
                for line in lines:
                    if search_term.lower() in line.lower() and len(line.strip()) > 10:
                        relevant_lines.append(line.strip())
                        if len(relevant_lines) >= 2:
                            break
                if relevant_lines:
                    return ' '.join(relevant_lines)
        
        # Fragen nach "welche Namen" oder "welche Begriffe"
        if "welche" in query_lower and ("namen" in query_lower or "begriffe" in query_lower or "kapitel" in query_lower):
            lines = chunk_text.split('\n')
            important_lines = []
            for line in lines[:20]:
                line = line.strip()
                if (re.search(r'^\d+\.', line) or 
                    (len(line) > 5 and len(line) < 100 and 
                     any(word[0].isupper() for word in line.split() if word))):
                    important_lines.append(line)
                    if len(important_lines) >= 5:
                        break
            if important_lines:
                return '\n'.join(important_lines)
        
        # Fragen nach spezifischen Begriffen
        question_words = [w for w in query_lower.split() if len(w) > 3 and w not in ['was', 'ist', 'welche', 'welcher', 'welches', 'sind', 'der', 'die', 'das']]
        if question_words:
            search_word = question_words[0]
            lines = chunk_text.split('\n')
            for line in lines:
                if search_word in line.lower() and len(line.strip()) > 10:
                    idx = lines.index(line)
                    result = line.strip()
                    if idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 20:
                        result += '\n' + lines[idx + 1].strip()
                    return result
        
        return None
    
    def _truncate_chunk(self, chunk_text: str, max_length: int = 300) -> str:
        """Kürzt Chunk auf max_length Zeichen"""
        if len(chunk_text) <= max_length:
            return chunk_text
        return chunk_text[:max_length] + "..."
    
    def _is_copy_paste(self, answer: str, chunk_text: str) -> bool:
        """
        Prüft ob LLM-Antwort zu ähnlich zum Original-Chunk ist (Copy-Paste-Erkennung)
        """
        answer_stripped = answer.strip()
        chunk_stripped = chunk_text.strip()
        
        answer_len = len(answer_stripped)
        chunk_len = len(chunk_stripped)
        
        # Wenn Antwort sehr lang ist (>30% der Chunk-Länge)
        if answer_len > chunk_len * 0.3:
            # Prüfe Wort-Überschneidung
            answer_words = set(answer_stripped.lower().split())
            chunk_words = set(chunk_stripped.lower().split())
            word_overlap = len(answer_words & chunk_words)
            word_overlap_ratio = word_overlap / len(answer_words) if answer_words else 0
            
            # Prüfe ob Antwort identisch oder enthält Chunk
            is_identical = answer_stripped == chunk_stripped
            answer_in_chunk = answer_stripped in chunk_stripped
            chunk_in_answer = chunk_stripped in answer_stripped
            
            # Sehr aggressiv: Wenn mehr als 40% Wort-Überschneidung ODER identisch/enthält
            if (is_identical or answer_in_chunk or chunk_in_answer or 
                word_overlap_ratio > 0.4 or answer_len > chunk_len * 0.6):
                return True
        
        return False
    
    def _generate_with_llm(self, query: str, context_chunks: List[Dict], rsq: float) -> str:
        """
        LLM-Generierung NUR für komplexe Fragen, die Extraktion nicht lösen konnte.
        Strenger Prompt gegen Copy-Paste.
        """
        # Kontext zusammenstellen
        context_parts = []
        for i, chunk in enumerate(context_chunks[:3], 1):  # Max 3 Chunks für Kontext
            title = chunk.get("title", "Abschnitt")
            text = chunk.get("text", "")
            context_parts.append(f"{i}. {title}:\n{text}")
        
        context = "\n\n".join(context_parts)
        
        # SEHR STRENGER Prompt gegen Copy-Paste
        prompt = f"""Du bist ein Dokumenten-Assistent. Antworte PRÄZISE und KURZ.

=== ABSOLUTES VERBOT ===
❌ NIEMALS den Dokumententext kopieren
❌ NIEMALS Seitenzahlen, Header oder Footer ausgeben
❌ NIEMALS mehr als 3 Sätze antworten
❌ NIEMALS den gesamten Abschnitt wiederholen

=== DOKUMENT ===
{context}

=== FRAGE ===
{query}

=== DEINE AUFGABE ===
1. Analysiere die Frage
2. Finde die relevante Information im Dokument
3. Antworte in MAXIMAL 2-3 Sätzen in eigenen Worten
4. Fokussiere dich NUR auf die Frage

=== ANTWORT (MAX 2-3 SÄTZE) ==="""

        try:
            answer = self.llm.generate(prompt, temperature=0.2, max_tokens=200)  # Kürzer!
            
            # Post-Processing: Prüfe auf Copy-Paste
            chunk_text = context_chunks[0].get("text", "")
            if self._is_copy_paste(answer, chunk_text):
                print("⚠ LLM hat kopiert, nutze Fallback")
                # Fallback: Erste 2 Sätze aus Chunk
                sentences = re.split(r'[.!?]+', chunk_text)
                relevant = [s.strip() for s in sentences if len(s.strip()) > 20][:2]
                return '. '.join(relevant) + '.' if relevant else chunk_text[:200] + "..."
            
            return answer
        except Exception as e:
            print(f"LLM Error: {e}")
            chunk_text = context_chunks[0].get("text", "")
            return self._truncate_chunk(chunk_text, max_length=200)
    
    def generate_answer(
        self, 
        query: str, 
        context_chunks: List[Dict], 
        rsq: float,
        use_rag: bool = True
    ) -> str:
        """
        Generiert Antwort mit klarer Reihenfolge:
        1. Retrieval (bereits erfolgt, context_chunks vorhanden)
        2. Heuristische Extraktion (Business-Werte)
        3. Intelligente Extraktion (allgemeine Fragen)
        4. Fallback: LLM (nur wenn Extraktion fehlschlägt)
        """
        if not context_chunks:
            return "Keine relevanten Informationen gefunden."
        
        chunk_text = context_chunks[0].get("text", "")
        
        # ===== SCHRITT 1: HEURISTISCHE EXTRAKTION (Business-Werte) =====
        # Für Fragen wie "Wie hoch ist der Gesamtbetrag?" → nur Wert zurückgeben
        extracted = self._extract_simple_answer(query, chunk_text)
        if extracted:
            print(f"✓ Business-Frage erkannt, direkte Extraktion: {extracted[:50]}...")
            return extracted
        
        # ===== SCHRITT 2: INTELLIGENTE EXTRAKTION (allgemeine Fragen) =====
        # Für Fragen wie "Was steht in Kapitel 3?" → relevante Teile extrahieren
        smart_extracted = self._extract_smart_answer(query, chunk_text)
        if smart_extracted:
            print(f"✓ Intelligente Extraktion erfolgreich")
            return smart_extracted
        
        # ===== SCHRITT 3: FALLBACK - LLM (nur wenn Extraktion fehlschlägt) =====
        if not use_rag:
            # Wenn RAG deaktiviert, gebe besten Chunk zurück (gekürzt)
            return self._truncate_chunk(chunk_text, max_length=300)
        
        # LLM nur für komplexe Fragen, die Extraktion nicht lösen konnte
        return self._generate_with_llm(query, context_chunks, rsq)
