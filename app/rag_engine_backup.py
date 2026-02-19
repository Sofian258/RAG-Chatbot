"""RAG Engine für Retrieval-Augmented Generation"""
import os
import re
from typing import List, Dict, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from app.vector_index import VectorIndex
    from app.local_llm import LocalLLM

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.topic_index import TopicIndex


class RAGEngine:
    """RAG Engine kombiniert Retrieval mit LLM-Generierung (lokal oder OpenAI)"""
    
    def __init__(
        self, 
        index: Union[TopicIndex, "VectorIndex"], 
        use_local: bool = True,
        llm: Optional["LocalLLM"] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialisiert RAG Engine
        
        Args:
            index: Index für Dokumentensuche
            use_local: Wenn True, nutze lokales LLM, sonst OpenAI
            llm: Lokales LLM (optional, wird erstellt wenn None)
            api_key: OpenAI API Key (nur wenn use_local=False)
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
            self.client = None
            self.api_key = None
        else:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI nicht verfügbar. Nutze use_local=True für lokales LLM.")
            self.llm = None
            self.api_key = api_key
            self.client = OpenAI(api_key=api_key) if api_key else None
    
    def _extract_simple_answer(self, query: str, chunk_text: str) -> Optional[str]:
        """
        Extrahiert Antwort für einfache Fragen direkt aus dem Chunk
        Returns None wenn keine einfache Frage erkannt wurde
        """
        query_lower = query.lower()
        
        # Gesamtbetrag
        if "gesamtbetrag" in query_lower or ("wie hoch" in query_lower and "betrag" in query_lower):
            # Normalisiere Text: Entferne überflüssige Whitespace
            normalized_text = re.sub(r'\s+', ' ', chunk_text)
            betrag_match = re.search(r'Gesamtbetrag[:\s]*([\d.,]+\s*€)', normalized_text, re.IGNORECASE)
            if betrag_match:
                return f"Der Gesamtbetrag beträgt {betrag_match.group(1).strip()}"
        
        # Nettobetrag
        if "nettobetrag" in query_lower:
            normalized_text = re.sub(r'\s+', ' ', chunk_text)
            betrag_match = re.search(r'Nettobetrag[:\s]*([\d.,]+\s*€)', normalized_text, re.IGNORECASE)
            if betrag_match:
                return f"Der Nettobetrag beträgt {betrag_match.group(1).strip()}"
        
        # Skonto-Berechnung
        if "skonto" in query_lower or "spare" in query_lower or ("wie viel" in query_lower and "spare" in query_lower):
            normalized_text = re.sub(r'\s+', ' ', chunk_text)
            # Suche nach Skonto-Prozentsatz
            skonto_match = re.search(r'(\d+)\s*%\s*Skonto', normalized_text, re.IGNORECASE)
            if skonto_match:
                skonto_prozent = int(skonto_match.group(1))
                # Suche nach Gesamtbetrag
                betrag_match = re.search(r'Gesamtbetrag[:\s]*([\d.,]+)\s*€', normalized_text, re.IGNORECASE)
                if betrag_match:
                    betrag_str = betrag_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        betrag = float(betrag_str)
                        skonto_betrag = betrag * (skonto_prozent / 100)
                        return f"Bei {skonto_prozent}% Skonto sparen Sie {skonto_betrag:,.2f} € ({skonto_prozent}% von {betrag:,.2f} €)"
                    except:
                        pass
                return f"Es gibt {skonto_prozent}% Skonto"
        
        # Datum
        if "datum" in query_lower or "wann" in query_lower:
            if "fällig" in query_lower or "bis" in query_lower:
                # Suche nach Fälligkeitsdatum
                fällig_match = re.search(r'(?:bis zum|fällig|bis)\s+(\d{1,2}\.\d{1,2}\.\d{4})', chunk_text, re.IGNORECASE)
                if fällig_match:
                    return f"Die Rechnung ist bis zum {fällig_match.group(1)} fällig"
            # Suche nach Rechnungsdatum
            date_match = re.search(r'Rechnungsdatum[:\s]*(\d{1,2}\.\d{1,2}\.\d{4})', chunk_text, re.IGNORECASE)
            if date_match:
                return f"Das Rechnungsdatum ist {date_match.group(1)}"
            # Fallback: Erstes Datum finden
            date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', chunk_text)
            if date_match:
                return f"Das Datum ist {date_match.group(1)}"
        
        # Firma/Unternehmen
        if "firma" in query_lower or "unternehmen" in query_lower or ("wie heißt" in query_lower and "firma" in query_lower):
            # Suche nach Firmennamen (z.B. "Testwerk Solutions")
            lines = chunk_text.split('\n')
            for line in lines[:15]:  # Erste 15 Zeilen prüfen
                line = line.strip()
                words = line.split()
                if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
                    if not any(word.lower() in ["ihr", "unternehmen", "rechnung", "betreff", "seite", "damen", "herren"] for word in words):
                        return f"Die Firma heißt {line}"
            # Fallback: Regex-Suche
            firma_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+)', chunk_text)
            if firma_match and "Ihr" not in firma_match.group(1) and "Unternehmen" not in firma_match.group(1):
                return f"Die Firma heißt {firma_match.group(1)}"
        
        # Rechnungsnummer
        if "rechnungsnummer" in query_lower or ("rechnung" in query_lower and "nummer" in query_lower) or "inv" in query_lower:
            inv_match = re.search(r'(?:INV|Rechnung\s+Nr\.?)\s*[:\-]?\s*([A-Z0-9\-]+)', chunk_text, re.IGNORECASE)
            if inv_match:
                return f"Die Rechnungsnummer ist {inv_match.group(1)}"
        
        # Fragen nach Kapiteln/Abschnitten (z.B. "Was ist das Fazit?", "Was steht in Kapitel 3.3?")
        if "fazit" in query_lower or "ausblick" in query_lower:
            # Suche nach Zeilen, die "Fazit" oder "Ausblick" enthalten
            lines = chunk_text.split('\n')
            relevant_lines = []
            found_keyword = False
            for line in lines:
                line_lower = line.lower()
                if ("fazit" in line_lower or "ausblick" in line_lower) and len(line.strip()) > 5:
                    found_keyword = True
                if found_keyword and len(line.strip()) > 10:
                    relevant_lines.append(line.strip())
                    if len(relevant_lines) >= 5:  # Max 5 relevante Zeilen
                        break
            if relevant_lines:
                return '\n'.join(relevant_lines[:3])  # Erste 3 relevante Zeilen
        
        # Fragen nach spezifischen Kapiteln (z.B. "Kapitel 3.3", "Abschnitt 4.1")
        chapter_match = re.search(r'kapitel\s+(\d+\.\d+)', query_lower)
        if chapter_match:
            chapter_num = chapter_match.group(1)
            # Suche nach Zeilen mit dieser Kapitelnummer
            lines = chunk_text.split('\n')
            for i, line in enumerate(lines):
                if chapter_num in line and len(line.strip()) > 5:
                    # Nimm diese Zeile und die nächsten 3-5 Zeilen
                    relevant = [line.strip()]
                    for j in range(i+1, min(i+6, len(lines))):
                        if len(lines[j].strip()) > 10:
                            relevant.append(lines[j].strip())
                    if len(relevant) > 1:
                        return '\n'.join(relevant[:4])  # Max 4 Zeilen
        
        return None
    
    def _extract_smart_answer(self, query: str, chunk_text: str) -> Optional[str]:
        """
        Intelligente Extraktion für allgemeine Fragen - extrahiert relevante Teile
        """
        query_lower = query.lower()
        
        # Fragen nach "was ist X" oder "was bedeutet X"
        if "was ist" in query_lower or "was bedeutet" in query_lower:
            # Suche nach dem gesuchten Begriff im Text
            # Extrahiere den Begriff aus der Frage
            match = re.search(r'was (ist|bedeutet)\s+(.+?)(?:\?|$)', query_lower)
            if match:
                search_term = match.group(2).strip()
                # Suche nach Zeilen, die den Begriff enthalten
                lines = chunk_text.split('\n')
                relevant_lines = []
                for line in lines:
                    if search_term.lower() in line.lower() and len(line.strip()) > 10:
                        relevant_lines.append(line.strip())
                        if len(relevant_lines) >= 2:  # Max 2 relevante Zeilen
                            break
                if relevant_lines:
                    return ' '.join(relevant_lines)
        
        # Fragen nach "welche Namen" oder "welche Begriffe"
        if "welche" in query_lower and ("namen" in query_lower or "begriffe" in query_lower or "kapitel" in query_lower):
            # Extrahiere Überschriften oder wichtige Begriffe
            lines = chunk_text.split('\n')
            important_lines = []
            for line in lines[:20]:  # Erste 20 Zeilen
                line = line.strip()
                # Suche nach Zeilen mit Zahlen (Kapitelnummern) oder wichtigen Begriffen
                if (re.search(r'^\d+\.', line) or  # Zeilen die mit Zahl beginnen
                    (len(line) > 5 and len(line) < 100 and 
                     any(word[0].isupper() for word in line.split() if word))):
                    important_lines.append(line)
                    if len(important_lines) >= 5:  # Max 5 Einträge
                        break
            if important_lines:
                return '\n'.join(important_lines)
        
        # Fragen nach spezifischen Begriffen im Text
        # Suche nach dem wichtigsten Wort in der Frage
        question_words = [w for w in query_lower.split() if len(w) > 3 and w not in ['was', 'ist', 'welche', 'welcher', 'welches', 'sind', 'sind', 'der', 'die', 'das']]
        if question_words:
            search_word = question_words[0]
            # Suche nach Zeilen, die dieses Wort enthalten
            lines = chunk_text.split('\n')
            for line in lines:
                if search_word in line.lower() and len(line.strip()) > 10:
                    # Extrahiere den relevanten Teil
                    # Wenn es eine Überschrift ist, nimm die nächste Zeile auch
                    idx = lines.index(line)
                    result = line.strip()
                    if idx + 1 < len(lines) and len(lines[idx + 1].strip()) > 20:
                        result += '\n' + lines[idx + 1].strip()
                    return result
        
        return None
    
    def generate_answer(
        self, 
        query: str, 
        context_chunks: List[Dict], 
        rsq: float,
        use_rag: bool = True
    ) -> str:
        """
        Generiert Antwort mit RAG (Retrieval-Augmented Generation)
        
        Args:
            query: Benutzerfrage
            context_chunks: Relevante Dokumenten-Abschnitte aus Retrieval
            rsq: Relevance Score Quality (0.0 - 1.0)
            use_rag: Wenn True, nutze LLM für Generierung, sonst nur beste Chunk
        
        Returns:
            Generierte Antwort
        """
        if not context_chunks:
            return "Keine relevanten Informationen gefunden."
        
        # RSQ-Prüfung entfernt - RAG soll immer versuchen zu analysieren
        # (Die RSQ-Prüfung erfolgt bereits in main.py als letzter Fallback bei rsq < 0.05)
        
        # Fallback: Wenn RAG deaktiviert, gebe besten Chunk zurück
        if not use_rag:
            return context_chunks[0].get("text", "Keine Antwort verfügbar.")
        
        # WICHTIG: Bei einfachen Fragen ZUERST Extraktion versuchen
        chunk_text = context_chunks[0].get("text", "")
        extracted = self._extract_simple_answer(query, chunk_text)
        if extracted:
            print(f"✓ Einfache Frage erkannt, nutze direkte Extraktion")
            return extracted
        
        # Kontext aus relevanten Dokumenten zusammenstellen
        # Nutze alle bereitgestellten Chunks für maximalen Kontext
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            title = chunk.get("title", "Abschnitt")
            text = chunk.get("text", "")
            context_parts.append(f"{i}. {title}:\n{text}")
        
        context = "\n\n".join(context_parts)
        
        # Stärkerer Prompt mit klaren Verboten und Anweisungen
        prompt = f"""Du bist ein intelligenter Dokumenten-Assistent. Deine Aufgabe ist es, Fragen präzise und verständlich zu beantworten.

=== ⚠️ KRITISCHE REGEL - NIEMALS KOPIEREN ⚠️ ===
❌ STRENG VERBOTEN:
- Den Dokumententext einfach kopieren oder wiederholen
- Längere Textpassagen aus den Dokumenten übernehmen
- Inhaltsverzeichnisse oder Seitenzahlen ausgeben
- Den gesamten Dokumentenabschnitt zurückgeben

✅ ERLAUBT UND ERWÜNSCHT:
- Analysieren und verstehen
- In eigenen Worten zusammenfassen
- Präzise, fokussierte Antworten geben
- Nur die relevanten Informationen extrahieren
- Denken und logische Schlüsse ziehen

=== DOKUMENTE ===
{context}

=== FRAGE DES BENUTZERS ===
{query}

=== DEINE AUFGABE ===
1. VERSTEHE die Frage vollständig - was wird wirklich gefragt?
2. ANALYSIERE die Dokumente gründlich - finde die relevanten Informationen
3. DENKE nach - was ist die beste Antwort?
4. FORMULIERE eine präzise Antwort in EIGENEN WORTEN
5. FOKUSSIERE dich - antworte nur auf die Frage, nicht mehr

=== ANTWORT-RICHTLINIEN ===
- Bei einfachen Fragen: Kurze, präzise Antwort (1-2 Sätze)
- Bei komplexen Fragen: Strukturierte Antwort mit Erklärung (3-5 Sätze)
- Bei "Was ist X?": Erkläre X basierend auf den Dokumenten
- Bei "Welche...": Liste die relevanten Punkte auf
- Bei "Wie...": Erkläre den Prozess oder die Methode
- Nutze NUR Informationen aus den Dokumenten
- Wenn Information fehlt: Sage das klar

=== BEISPIELE FÜR GUTE ANTWORTEN ===
Frage: "Wie hoch ist der Gesamtbetrag?"
✅ GUT: "Der Gesamtbetrag beträgt 35.574,00 €"
❌ SCHLECHT: "--- Seite 1 --- Ihr Unternehmen Testwerk Solutions Rechnung INV-0001..."

Frage: "Was ist das Fazit?"
✅ GUT: "Das Fazit befindet sich in Kapitel 5. Es beschreibt die Ergebnisse der Arbeit und zeigt, dass die modulare Architektur erfolgreich war. Die Lösung bietet eine skalierbare Basis für weitere Entwicklungen."
❌ SCHLECHT: "II --- Seite 5 --- Inhaltsverzeichnis 3.3 Anwendung von Machine-Learning..."

Frage: "Was ist Anwendung von Machine-Learning?"
✅ GUT: "Die Anwendung von Machine-Learning wird in Kapitel 3.3 beschrieben. Es geht um die Integration von ML-Methoden, insbesondere Isolation Forest für die Anomalieerkennung in RLT-Anlagen."
❌ SCHLECHT: [Gibt gesamten Dokumententext zurück]

=== ANTWORT ===
Denke jetzt nach und antworte PRÄZISE in EIGENEN WORTEN. NIEMALS den Dokumententext kopieren!"""

        # Smart Routing: Entscheide welches Modell basierend auf Frage-Typ
        if self.use_local and self.llm:
            # Prüfe ob einfache Frage (nutze schnelles Modell)
            query_lower = query.lower()
            simple_keywords = ["wie hoch", "betrag", "preis", "kosten", "datum", "wann", "fällig", "rechnungsnummer", "firma", "unternehmen", "name", "skonto", "spare", "rabatt", "wie viel", "gesamtbetrag"]
            is_simple_question = any(kw in query_lower for kw in simple_keywords)
            
            # Für einfache Fragen mit guter Relevanz: Nutze schnelles Modell
            if is_simple_question and rsq > 0.3 and hasattr(self, 'fast_llm'):
                try:
                    print(f"📊 Einfache Frage erkannt, nutze schnelles Modell ({self.fast_llm.model})")
                    answer = self.fast_llm.generate(prompt, temperature=0.1, max_tokens=150, use_fallback=False)
                except Exception as e:
                    print(f"⚠ Schnelles Modell fehlgeschlagen: {e}, nutze Hauptmodell")
                    # Fallback zu Hauptmodell
                    answer = self.llm.generate(prompt, temperature=0.2, max_tokens=400)
                
                # Post-Processing: Prüfe ob LLM nur den Chunk zurückgegeben hat
                chunk_text = context_chunks[0].get("text", "")
                answer_stripped = answer.strip()
                chunk_stripped = chunk_text.strip()
                
                # Prüfe ob Antwort identisch oder sehr ähnlich zum Chunk ist
                # Verbesserte Ähnlichkeitsprüfung
                answer_len = len(answer_stripped)
                chunk_len = len(chunk_stripped)
                
                # Sehr aggressive Ähnlichkeitsprüfung: Wenn Antwort sehr lang ist (>30% der Chunk-Länge)
                if answer_len > chunk_len * 0.3:
                    # Prüfe Wort-Überschneidung
                    answer_words = set(answer_stripped.lower().split())
                    chunk_words = set(chunk_stripped.lower().split())
                    word_overlap = len(answer_words & chunk_words)
                    word_overlap_ratio = word_overlap / len(answer_words) if answer_words else 0
                    
                    # Prüfe ob Antwort den Chunk enthält oder umgekehrt
                    is_identical = answer_stripped == chunk_stripped
                    answer_in_chunk = answer_stripped in chunk_stripped
                    chunk_in_answer = chunk_stripped in answer_stripped
                    
                    # Sehr aggressiv: Wenn mehr als 40% Wort-Überschneidung ODER Antwort ist identisch/enthält Chunk ODER sehr lang
                    if (is_identical or answer_in_chunk or chunk_in_answer or 
                        word_overlap_ratio > 0.4 or answer_len > chunk_len * 0.6):
                        
                        print(f"⚠ LLM hat wahrscheinlich nur Chunk zurückgegeben ({answer_len} Zeichen, {word_overlap_ratio:.1%} Wort-Überschneidung), nutze intelligente Extraktion")
                        
                        # Versuche intelligente Extraktion
                        extracted = self._extract_simple_answer(query, chunk_text)
                        if extracted:
                            return extracted
                        
                        # Intelligente Extraktion für allgemeine Fragen
                        smart_extracted = self._extract_smart_answer(query, chunk_text)
                        if smart_extracted:
                            return smart_extracted
                        
                        # Fallback: Erste 2-3 Sätze extrahieren
                        sentences = re.split(r'[.!?]+', chunk_text)
                        relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
                        if relevant_sentences:
                            return '. '.join(relevant_sentences) + '.'
                        
                        # Letzter Fallback: Kürze Antwort
                        return answer[:300] + "..." if len(answer) > 300 else answer
                
                return answer
            else:
                # Für komplexe Fragen: Nutze Hauptmodell
                try:
                    print(f"🧠 Komplexe Frage, nutze Hauptmodell ({self.llm.model})")
                    answer = self.llm.generate(prompt, temperature=0.2, max_tokens=400)
                    
                    # Post-Processing: Prüfe ob LLM nur den Chunk zurückgegeben hat
                    chunk_text = context_chunks[0].get("text", "")
                    answer_stripped = answer.strip()
                    chunk_stripped = chunk_text.strip()
                    
                    # Verbesserte Ähnlichkeitsprüfung
                    answer_len = len(answer_stripped)
                    chunk_len = len(chunk_stripped)
                    
                    # Sehr aggressive Ähnlichkeitsprüfung: Wenn Antwort sehr lang ist (>30% der Chunk-Länge)
                    if answer_len > chunk_len * 0.3:
                        # Prüfe Wort-Überschneidung
                        answer_words = set(answer_stripped.lower().split())
                        chunk_words = set(chunk_stripped.lower().split())
                        word_overlap = len(answer_words & chunk_words)
                        word_overlap_ratio = word_overlap / len(answer_words) if answer_words else 0
                        
                        # Prüfe ob Antwort den Chunk enthält oder umgekehrt
                        is_identical = answer_stripped == chunk_stripped
                        answer_in_chunk = answer_stripped in chunk_stripped
                        chunk_in_answer = chunk_stripped in answer_stripped
                        
                        # Sehr aggressiv: Wenn mehr als 40% Wort-Überschneidung ODER Antwort ist identisch/enthält Chunk ODER sehr lang
                        if (is_identical or answer_in_chunk or chunk_in_answer or 
                            word_overlap_ratio > 0.4 or answer_len > chunk_len * 0.6):
                            
                            print(f"⚠ LLM hat wahrscheinlich nur Chunk zurückgegeben ({answer_len} Zeichen, {word_overlap_ratio:.1%} Wort-Überschneidung), nutze intelligente Extraktion")
                            
                            # Versuche intelligente Extraktion
                            extracted = self._extract_simple_answer(query, chunk_text)
                            if extracted:
                                return extracted
                            
                            # Intelligente Extraktion für allgemeine Fragen
                            smart_extracted = self._extract_smart_answer(query, chunk_text)
                            if smart_extracted:
                                return smart_extracted
                            
                            # Fallback: Erste 2-3 Sätze extrahieren
                            sentences = re.split(r'[.!?]+', chunk_text)
                            relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
                            if relevant_sentences:
                                return '. '.join(relevant_sentences) + '.'
                            
                            # Letzter Fallback: Kürze Antwort
                            return answer[:300] + "..." if len(answer) > 300 else answer
                    
                    return answer
                except Exception as e:
                    print(f"Lokales LLM Error: {e}")
                    # Fallback: Beste Übereinstimmung zurückgeben
                    return context_chunks[0].get("text", "Fehler bei der Generierung mit lokalem LLM.")
        elif self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"OpenAI RAG Error: {e}")
                return context_chunks[0].get("text", "Fehler bei der Generierung.")
        else:
            # Kein LLM verfügbar
            return context_chunks[0].get("text", "Keine Antwort verfügbar.")

