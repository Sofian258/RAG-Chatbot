"""RAG Engine für Retrieval-Augmented Generation"""
import os
import re
import logging
from typing import List, Dict, Optional, Union, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.vector_index import VectorIndex
    from app.local_llm import LocalLLM
    from app.llm_router import LLMRouter

from app.topic_index import TopicIndex


class RAGEngine:
    """RAG Engine kombiniert Retrieval mit LLM-Generierung (nur lokale LLMs)"""
    
    def __init__(
        self, 
        index: Union[TopicIndex, "VectorIndex"], 
        use_local: bool = True,
        llm: Optional["LocalLLM"] = None,
        api_key: Optional[str] = None,
        llm_router: Optional["LLMRouter"] = None
    ):
        """
        Initialisiert RAG Engine
        
        Args:
            index: Index für Dokumentensuche
            use_local: Wenn True, nutze lokales LLM (Standard: True)
            llm: Lokales LLM (optional, wird erstellt wenn None) - DEPRECATED, nutze llm_router
            api_key: Deprecated - wird nicht mehr verwendet
            llm_router: LLM Router für Multi-Modell-Support (optional)
        """
        self.index = index
        self.use_local = use_local
        
        # Multi-Modell Router (neu)
        if llm_router:
            self.llm_router = llm_router
            self.use_router = True
            print("✓ RAG Engine nutzt Multi-Modell Router")
        else:
            self.use_router = False
            # Legacy: Einzelne LLM-Instanzen (für Kompatibilität)
            if use_local:
                if llm is None:
                    from app.local_llm import LocalLLM
                    llm = LocalLLM()  # Hauptmodell (qwen2.5:7b)
                self.llm = llm
                # Schnelles Modell für einfache Fragen
                fast_model = os.getenv("LLM_FAST_MODEL", "qwen2.5:3b")
                self.fast_llm = LocalLLM(model=fast_model, fallback_model=os.getenv("LLM_FALLBACK_MODEL", "llama3.2:1b"))
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
    
    def _extract_list_answer(self, query: str, chunk_text: str) -> Optional[str]:
        """
        Extrahiert Listen-Antworten für Fragen wie "Welche drei Module?" oder "Welche Patterns?"
        """
        query_lower = query.lower()
        
        # Erkenne Listenfragen mit Zahlen (z.B. "drei Module", "zwei Patterns")
        list_patterns = [
            r'(?:welche|was sind|nenne|zähle)\s+(?:die\s+)?(?:drei|zwei|vier|fünf|sechs|sieben|acht|neun|zehn)\s+([a-zäöü]+)',
            r'(?:welche|was sind|nenne|zähle)\s+([a-zäöü]+)\s+(?:gibt es|sind|existieren)',
        ]
        
        for pattern in list_patterns:
            match = re.search(pattern, query_lower)
            if match:
                search_term = match.group(1).strip()
                
                # Suche nach dem Begriff im Text (z.B. "Module", "Patterns")
                full_text = chunk_text
                found_items = []
                
                # PRIORITÄT 1: Suche ZUERST nach Klammern mit Modulen
                # "drei zentralen Modulen (Input-Modul, Processing-Modul und Output-Modul)"
                module_match = re.search(r'\(([^)]*(?:-Modul|-Pattern)[^)]*)\)', full_text, re.IGNORECASE)
                if module_match:
                    modules_str = module_match.group(1)
                    # Teile bei "und" zuerst
                    modules = re.split(r'\s+und\s+', modules_str)
                    # Dann teile jedes Element bei Kommas
                    all_modules = []
                    for m in modules:
                        if ',' in m:
                            all_modules.extend([x.strip() for x in m.split(',')])
                        else:
                            all_modules.append(m.strip())
                    # Filtere nur Module/Patterns
                    found_items = [m.strip() for m in all_modules if m.strip() and ('modul' in m.lower() or 'pattern' in m.lower())]
                    if found_items:
                        # Bereinige die Items
                        found_items = [item for item in found_items if item.lower() not in ['und', ''] and len(item) > 3]
                
                # PRIORITÄT 2: Suche nach allen "X-Modul" oder "X-Pattern" im gesamten Text
                if not found_items:
                    module_pattern = r'([A-Z][a-zA-ZäöüÄÖÜ]+(?:-Modul|-Pattern))'
                    all_modules = re.findall(module_pattern, full_text)
                    if all_modules:
                        # Entferne Duplikate, behalte Reihenfolge
                        seen = set()
                        found_items = []
                        for mod in all_modules:
                            if mod not in seen:
                                seen.add(mod)
                                found_items.append(mod)
                        if len(found_items) > 10:
                            found_items = found_items[:10]
                
                # PRIORITÄT 3: Suche nach expliziten Listen (nur wenn noch nichts gefunden)
                if not found_items:
                    lines = chunk_text.split('\n')
                    for i, line in enumerate(lines):
                        line_stripped = line.strip()
                        
                        # Nur echte Listen-Elemente (kurz, beginnt mit - oder • oder Nummerierung)
                        if ((line_stripped.startswith('-') or 
                             line_stripped.startswith('•') or
                             re.match(r'^\d+[\.\)]\s+', line_stripped)) and
                            len(line_stripped) < 100):  # Maximal 100 Zeichen
                            
                            clean_line = re.sub(r'^[-•\d\.\)\s]+', '', line_stripped)
                            # Prüfe ob es ein Modul/Pattern ist
                            if clean_line and ('modul' in clean_line.lower() or 'pattern' in clean_line.lower()):
                                found_items.append(clean_line)
                
                if found_items:
                    # Formatiere als nummerierte Liste
                    formatted = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(found_items[:10])])
                    print(f"DEBUG _extract_list_answer: found_items={found_items}, formatted={formatted[:100]}")
                    return formatted
                else:
                    print(f"DEBUG _extract_list_answer: Keine Items gefunden für search_term='{search_term}'")
                
                return None
        
        return None
    
    def _extract_smart_answer(self, query: str, chunk_text: str) -> Optional[str]:
        """
        Intelligente Extraktion für allgemeine Fragen - extrahiert relevante Teile
        """
        query_lower = query.lower()
        
        # NEU: Listenfragen zuerst behandeln
        list_answer = self._extract_list_answer(query, chunk_text)
        if list_answer:
            return list_answer
        
        # Fragen nach "wie" (Prozess-Fragen)
        if "wie" in query_lower and ("erstelle" in query_lower or "erstellen" in query_lower or "anlegen" in query_lower or "anlege" in query_lower):
            # Suche nach Prozess-Beschreibungen
            lines = chunk_text.split('\n')
            relevant_parts = []
            found_start = False
            
            for line in lines:
                line_lower = line.lower()
                line_stripped = line.strip()
                
                # Erkenne Start einer Prozess-Beschreibung
                if ("projekt" in line_lower and ("erstellen" in line_lower or "anlegen" in line_lower or "brauchen" in line_lower or "angaben" in line_lower)):
                    found_start = True
                
                # Sammle relevante Zeilen
                if found_start and len(line_stripped) > 10:
                    # Überschriften überspringen
                    if not re.match(r'^[A-ZÄÖÜ][a-zäöü]+$', line_stripped) or len(line_stripped) > 50:
                        relevant_parts.append(line_stripped)
                        if len(relevant_parts) >= 10:  # Max 10 Zeilen
                            break
            
            if relevant_parts:
                # Formatiere als zusammenhängende Antwort
                answer = ' '.join(relevant_parts[:8])  # Max 8 Zeilen
                # Kürze auf sinnvolle Länge
                if len(answer) > 500:
                    sentences = re.split(r'[.!?]+', answer)
                    answer = '. '.join([s.strip() for s in sentences if len(s.strip()) > 20][:5]) + '.'
                return answer
        
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
    
    def clean_answer(self, text: str, company_id: Optional[str] = None) -> str:
        """
        Bereinigt Antwort von unerwünschten Strukturen (nur für Planovo)
        
        Args:
            text: Rohe Antwort vom LLM
            company_id: Optional - Firma-ID für spezifische Bereinigung
        
        Returns:
            Bereinigte Antwort
        """
        if not company_id or company_id.lower() != "planovo":
            return text  # Nur für Planovo bereinigen
        
        if not text:
            return text
        
        # WICHTIG: Entferne "Quellen:" Zeilen komplett (mit Regex für alles nach "Quellen:")
        # Entfernt z.B. "Quellen: PROJEKT ERSTELLEN IN PLANOVO, FELD: Beschreibung, FELD: Ausführungsort"
        text = re.sub(r'Quellen:.*?(?=\n|$)', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Blacklist von unerwünschten Strukturen
        blacklist = [
            "FELD:",
            "Pflicht:",
            "Typische Nutzerfragen",
            "FRAGE:",
            "ERWARTETE ANTWORT:",
            "TESTFRAGEN",
            "=== ",
            "--- ",
            "**",
        ]
        
        # Entferne Blacklist-Items
        cleaned = text
        for item in blacklist:
            cleaned = cleaned.replace(item, "")
        
        # Entferne Zeilen die mit Blacklist-Items anfangen oder nur Labels sind
        lines = cleaned.split('\n')
        cleaned_lines = []
        forbidden_starters = ["FRAGE:", "ERWARTETE ANTWORT:", "FELD:", "Pflicht:", "Typische Nutzerfragen", "Quellen:", "TESTFRAGEN"]
        
        for line in lines:
            line_stripped = line.strip()
            
            # Überspringe Zeilen die mit verbotenen Wörtern anfangen (case-insensitive)
            skip = False
            line_upper = line_stripped.upper()
            for forbidden in forbidden_starters:
                if line_upper.startswith(forbidden.upper()):
                    skip = True
                    break
            if skip:
                continue
            
            # NEU: Entferne Zeilen die nur die Frage wiederholen (z.B. "- Welchen Projekttyp soll ich wählen")
            # Erkenne Frage-Wiederholungen: Zeilen die mit "- " oder "• " anfangen und die Frage enthalten
            if line_stripped.startswith(("- ", "• ")):
                # Wenn die Zeile nur eine Frage ist (endet mit "?" oder ist sehr kurz), überspringe sie
                if line_stripped.endswith("?") or len(line_stripped.split()) <= 5:
                    # Prüfe ob es eine echte Liste ist (mehrere Zeilen mit "- " oder "• ")
                    # Nur überspringen wenn es isoliert ist
                    continue
            
            # Überspringe leere Zeilen oder Zeilen die nur Labels sind
            if line_stripped and not (line_stripped.endswith(':') and len(line_stripped) < 30):
                # Überspringe auch Zeilen die nur aus Großbuchstaben bestehen (Überschriften)
                if not (line_stripped.isupper() and len(line_stripped) > 5):
                    # Überspringe Zeilen die nur aus einem Wort bestehen (wahrscheinlich Label-Reste)
                    if len(line_stripped.split()) > 1 or len(line_stripped) > 15:
                        cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        # NEU: Entferne Frage-Wiederholungen am Anfang
        # Wenn die Antwort mit einer Frage beginnt (endet mit "?"), entferne diese Zeile
        result_lines = result.split('\n')
        if result_lines and result_lines[0].strip().endswith('?'):
            # Prüfe ob es wirklich eine Frage-Wiederholung ist (kurz, endet mit "?")
            first_line = result_lines[0].strip()
            if len(first_line.split()) <= 8:  # Kurze Frage
                result_lines = result_lines[1:]  # Entferne erste Zeile
                result = '\n'.join(result_lines).strip()
        
        # Entferne mehrfache Leerzeilen
        result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
        
        return result
    
    def generate_answer(
        self, 
        query: str, 
        context_chunks: List[Dict], 
        rsq: float,
        use_rag: bool = True,
        company_id: Optional[str] = None
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
            answer = context_chunks[0].get("text", "Keine Antwort verfügbar.")
            return self.clean_answer(answer, company_id)
        
        # WICHTIG: Nur bei sehr einfachen Faktenfragen: Direkte Extraktion
        chunk_text = context_chunks[0].get("text", "")
        query_lower = query.lower()
        simple_fact_keywords = ["gesamtbetrag", "nettobetrag", "rechnungsnummer", "datum", "fällig", "firma", "unternehmen", "name"]
        is_simple_fact = any(kw in query_lower for kw in simple_fact_keywords)
        
        if is_simple_fact:
            extracted = self._extract_simple_answer(query, chunk_text)
            if extracted:
                print(f"✓ Einfache Faktenfrage erkannt, nutze direkte Extraktion")
                extracted = self.clean_answer(extracted, company_id)
                return extracted
        
        # Kontext aus relevanten Dokumenten zusammenstellen
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            title = chunk.get("title", "Abschnitt")
            text = chunk.get("text", "")
            context_parts.append(f"{title}:\n{text}")
        
        context = "\n\n".join(context_parts)
        
        # DEBUG: Prüfe company_id
        print(f"🔍 DEBUG generate_answer: company_id='{company_id}', lower='{company_id.lower() if company_id else None}'")
        
        # PROMPT-Auswahl basierend auf company_id
        if company_id and company_id.lower() == "planovo":
            # Planovo Support-Prompt (HARTE Output-Regeln)
            prompt = f"""Du bist Planovo Support.

Beantworte die Nutzerfrage kurz und direkt.
Nutze die Dokumente nur als Wissensquelle.

WICHTIGE REGELN:
- Gib NUR die fertige Antwort aus.
- KEINE Überschriften.
- KEINE Feldnamen.
- KEINE Wörter wie: "FRAGE:", "ERWARTETE ANTWORT:", "FELD:", "Pflicht:", "Typische Nutzerfragen", "Quellen:", "TESTFRAGEN".
- KEINE Quellen-Informationen oder Quellen-Angaben in der Antwort.
- KEINE Meta-Erklärung.
- KEINE Struktur-Labels.
- Wenn die Frage nach Optionen/Auswahl fragt (z.B. "welchen X soll ich wählen"), liste die verfügbaren Optionen auf.
- Antworte IMMER direkt - wiederhole NICHT die Frage.

DOKUMENTE:
{context}

NUTZERFRAGE:
{query}

ANTWORT (nur die Antwort, keine Labels, keine Frage-Wiederholung):"""
        else:
            # Standard-Prompt (für Dev/andere)
            prompt = f"""Du bist ein Support-Mitarbeiter. Antworte auf die Frage des Kunden basierend auf den folgenden Dokumenten.

=== WICHTIG ===
- Antworte direkt auf die konkrete Frage
- Nutze die Informationen aus den Dokumenten
- Sei kurz und präzise
- Frage nach, wenn wichtige Informationen fehlen

=== DOKUMENTE ===
{context}

=== FRAGE DES KUNDEN ===
{query}

=== DEINE ANTWORT ===
Antworte jetzt direkt auf die Frage. Nutze die Informationen aus den Dokumenten, aber formuliere in eigenen Worten."""

        # Multi-Modell Router (neu) - intelligente Modell-Auswahl
        if self.use_router and self.use_local:
            try:
                print(f"🧠 Nutze Multi-Modell Router für intelligente Modell-Auswahl")
                is_planovo = company_id and company_id.lower() == "planovo"
                answer = self.llm_router.generate(query, context_chunks, rsq, prompt, is_planovo=is_planovo)
                
                # Post-Filter für Planovo: Entferne unerwünschte Strukturen
                answer = self.clean_answer(answer, company_id)
                
                # SEHR WENIGER AGGRESSIVE Ähnlichkeitsprüfung - nur bei EXAKT identischen Antworten
                chunk_text = context_chunks[0].get("text", "")
                answer_stripped = answer.strip()
                chunk_stripped = chunk_text.strip()
                
                # Nur wenn Antwort EXAKT identisch ist (keine Teilstrings mehr prüfen)
                is_identical = answer_stripped == chunk_stripped
                
                if is_identical:
                    print(f"⚠ LLM hat Chunk exakt zurückgegeben, nutze intelligente Extraktion")
                    # Nur dann Extraktion versuchen
                    extracted = self._extract_simple_answer(query, chunk_text)
                    if extracted:
                        extracted = self.clean_answer(extracted, company_id)
                        return extracted
                    smart_extracted = self._extract_smart_answer(query, chunk_text)
                    if smart_extracted:
                        smart_extracted = self.clean_answer(smart_extracted, company_id)
                        return smart_extracted
                    # Wenn Extraktion fehlschlägt, gib die LLM-Antwort trotzdem zurück (besser als nichts)
                    return answer
                
                return answer
            except Exception as e:
                logger.error(f"Router-Fehler: {e}", exc_info=True)
                print(f"⚠ Router-Fehler: {e}, Fallback zu intelligenter Extraktion")
                # Fallback: Versuche intelligente Extraktion statt roher Chunks
                chunk_text = context_chunks[0].get("text", "")
                extracted = self._extract_simple_answer(query, chunk_text)
                if extracted:
                    return self.clean_answer(extracted, company_id)
                smart_extracted = self._extract_smart_answer(query, chunk_text)
                if smart_extracted:
                    return self.clean_answer(smart_extracted, company_id)
                # Letzter Fallback: Erste 2-3 Sätze extrahieren
                sentences = re.split(r'[.!?]+', chunk_text)
                relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
                if relevant_sentences:
                    answer = '. '.join(relevant_sentences) + '.'
                    return self.clean_answer(answer, company_id)
                # Nur wenn alles fehlschlägt: Erste 200 Zeichen
                answer = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                return self.clean_answer(answer, company_id)
        
        # Legacy: Smart Routing mit einzelnen Modellen
        if self.use_local and self.llm and not self.use_router:
            # Prüfe ob einfache Frage (nutze schnelles Modell)
            query_lower = query.lower()
            simple_keywords = ["wie hoch", "betrag", "preis", "kosten", "datum", "wann", "fällig", "rechnungsnummer", "firma", "unternehmen", "name", "skonto", "spare", "rabatt", "wie viel", "gesamtbetrag"]
            is_simple_question = any(kw in query_lower for kw in simple_keywords)
            
            # Für einfache Fragen mit guter Relevanz: Nutze schnelles Modell
            if is_simple_question and rsq > 0.3 and hasattr(self, 'fast_llm'):
                try:
                    print(f"📊 Einfache Frage erkannt, nutze schnelles Modell ({self.fast_llm.model})")
                    is_planovo = company_id and company_id.lower() == "planovo"
                    answer = self.fast_llm.generate(prompt, temperature=0.1, max_tokens=150, use_fallback=False, is_planovo=is_planovo)
                except Exception as e:
                    print(f"⚠ Schnelles Modell fehlgeschlagen: {e}, nutze Hauptmodell")
                    # Fallback zu Hauptmodell
                    is_planovo = company_id and company_id.lower() == "planovo"
                    answer = self.llm.generate(prompt, temperature=0.2, max_tokens=400, is_planovo=is_planovo)
                    # Post-Filter für Planovo
                    answer = self.clean_answer(answer, company_id)
                
                # SEHR WENIGER AGGRESSIVE Ähnlichkeitsprüfung - nur bei EXAKT identischen Antworten
                chunk_text = context_chunks[0].get("text", "")
                answer_stripped = answer.strip()
                chunk_stripped = chunk_text.strip()
                
                # Nur wenn Antwort EXAKT identisch ist
                is_identical = answer_stripped == chunk_stripped
                
                if is_identical:
                    print(f"⚠ LLM hat Chunk exakt zurückgegeben, nutze intelligente Extraktion")
                    extracted = self._extract_simple_answer(query, chunk_text)
                    if extracted:
                        return self.clean_answer(extracted, company_id)
                    smart_extracted = self._extract_smart_answer(query, chunk_text)
                    if smart_extracted:
                        return self.clean_answer(smart_extracted, company_id)
                    # Wenn Extraktion fehlschlägt, gib die LLM-Antwort trotzdem zurück
                    return answer
                
                return answer
            else:
                # Für komplexe Fragen: Nutze Hauptmodell mit mehr Tokens für besseres Denken
                try:
                    print(f"🧠 Komplexe Frage, nutze Hauptmodell ({self.llm.model})")
                    # Erhöhte Temperature für mehr "Denken" und Kreativität
                    # Mehr Tokens für längere, durchdachte Antworten
                    is_planovo = company_id and company_id.lower() == "planovo"
                    answer = self.llm.generate(prompt, temperature=0.3, max_tokens=600, is_planovo=is_planovo)
                    # Post-Filter für Planovo
                    answer = self.clean_answer(answer, company_id)
                    
                    # WENIGER AGGRESSIVE Ähnlichkeitsprüfung - nur bei identischen Antworten
                    chunk_text = context_chunks[0].get("text", "")
                    answer_stripped = answer.strip()
                    chunk_stripped = chunk_text.strip()
                    
                    is_identical = answer_stripped == chunk_stripped
                    answer_in_chunk = answer_stripped in chunk_stripped
                    chunk_in_answer = chunk_stripped in answer_stripped
                    
                    if is_identical or answer_in_chunk or chunk_in_answer:
                        print(f"⚠ LLM hat Chunk zurückgegeben, nutze intelligente Extraktion")
                        extracted = self._extract_simple_answer(query, chunk_text)
                        if extracted:
                            extracted = self.clean_answer(extracted, company_id)
                            return extracted
                        smart_extracted = self._extract_smart_answer(query, chunk_text)
                        if smart_extracted:
                            smart_extracted = self.clean_answer(smart_extracted, company_id)
                            return smart_extracted
                    
                    return answer
                except Exception as e:
                    print(f"Lokales LLM Error: {e}")
                    # Fallback: Versuche intelligente Extraktion statt roher Chunks
                    chunk_text = context_chunks[0].get("text", "")
                    extracted = self._extract_simple_answer(query, chunk_text)
                    if extracted:
                        extracted = self.clean_answer(extracted, company_id)
                        return extracted
                    smart_extracted = self._extract_smart_answer(query, chunk_text)
                    if smart_extracted:
                        smart_extracted = self.clean_answer(smart_extracted, company_id)
                        return smart_extracted
                    # Letzter Fallback: Erste 2-3 Sätze extrahieren
                    sentences = re.split(r'[.!?]+', chunk_text)
                    relevant_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:3]
                    if relevant_sentences:
                        fallback_answer = '. '.join(relevant_sentences) + '.'
                        fallback_answer = self.clean_answer(fallback_answer, company_id)
                        return fallback_answer
                    # Nur wenn alles fehlschlägt: Beste Übereinstimmung
                    final_answer = context_chunks[0].get("text", "Fehler bei der Generierung mit lokalem LLM.")
                    final_answer = self.clean_answer(final_answer, company_id)
                    return final_answer
        else:
            # Kein LLM verfügbar
            answer = context_chunks[0].get("text", "Keine Antwort verfügbar.")
            return self.clean_answer(answer, company_id)
