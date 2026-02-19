from __future__ import annotations
from pathlib import Path
import re
import io

def load_sections_from_txt(path: str) -> list[dict]:
    """
    Lädt und segmentiert Dokumente für optimiertes Retrieval.
    
    Verbesserte Chunking-Strategie:
    - Erkennt verschiedene Überschrift-Formate
    - Behält Kontext bei (Titel + Inhalt)
    - Erstellt eindeutige IDs für besseres Retrieval
    - Optimiert für TF-IDF und semantische Suche
    """
    text = Path(path).read_text(encoding="utf-8")
    lines = [ln.rstrip() for ln in text.splitlines()]

    sections: list[dict] = []
    current_title = None
    current_lines: list[str] = []

    def flush():
        """Speichert aktuellen Abschnitt und bereitet neuen vor"""
        nonlocal current_title, current_lines
        if current_title and current_lines:
            # Bereinige und kombiniere Inhalt
            body = "\n".join([l for l in current_lines if l.strip()]).strip()
            if body:
                # Erstelle eindeutige ID für besseres Retrieval
                section_id = re.sub(r'[^\w\s-]', '', current_title.lower())
                section_id = re.sub(r'\s+', '_', section_id)[:50]  # Max 50 Zeichen
                
                # Kombiniere Titel und Inhalt für besseren Kontext
                full_text = f"{current_title}\n{body}"
                
                sections.append({
                    "id": section_id or f"section_{len(sections)}",
                    "title": current_title.strip(),
                    "text": full_text,
                })
        current_title = None
        current_lines = []

    for ln in lines:
        s = ln.strip()
        if not s:
            # Leere Zeilen als Absatz-Trenner beibehalten
            if current_lines:
                current_lines.append("")
            continue

        # Überschrift-Heuristik 1: Komplett Großbuchstaben (z.B. "ÖFFNUNGSZEITEN")
        if s.isupper() and len(s) <= 50 and len(s.split()) <= 8:
            flush()
            current_title = s
            continue
        
        # Überschrift-Heuristik 2: Nummerierte Überschriften (z.B. "1. Unternehmensprofil", "10. Kontakt")
        if len(s) <= 60:
            # Erkenne Muster: Zahl + Punkt + Leerzeichen + Text
            match = re.match(r'^(\d+)\.\s+(.+)$', s)
            if match:
                flush()
                current_title = s
                continue
        
        # Überschrift-Heuristik 3: Markdown-ähnliche Überschriften (z.B. "## Überschrift")
        if s.startswith("#") and len(s) <= 60:
            flush()
            current_title = s.lstrip("#").strip()
            continue
        
        # Überschrift-Heuristik 4: Unterstrichene Überschriften (z.B. "Überschrift\n---")
        # (wird durch nächste Zeile erkannt, hier nur für Vollständigkeit)
        
        # Normale Textzeile
        current_lines.append(ln)

    # Letzten Abschnitt speichern
    flush()

    # Fallback: Wenn keine Überschriften gefunden wurden, teile in logische Blöcke
    if not sections:
        # Versuche nach Absätzen zu segmentieren (2+ Leerzeilen = neuer Abschnitt)
        clean_text = "\n".join([l for l in lines if l.strip()]).strip()
        if clean_text:
            # Teile bei doppelten Zeilenumbrüchen
            paragraphs = re.split(r'\n\s*\n+', clean_text)
            for i, para in enumerate(paragraphs):
                if para.strip():
                    # Erste Zeile als Titel verwenden, wenn kurz
                    para_lines = para.strip().split('\n')
                    if len(para_lines) > 0 and len(para_lines[0]) <= 50:
                        title = para_lines[0]
                        body = '\n'.join(para_lines[1:]) if len(para_lines) > 1 else ""
                    else:
                        title = f"Abschnitt {i+1}"
                        body = para.strip()
                    
                    section_id = re.sub(r'[^\w\s-]', '', title.lower())
                    section_id = re.sub(r'\s+', '_', section_id)[:50]
                    
                    sections.append({
                        "id": section_id or f"section_{i}",
                        "title": title,
                        "text": f"{title}\n{body}" if body else title,
                    })
        
        # Wenn immer noch nichts, alles als ein Dokument
        if not sections:
            sections = [{
                "id": "doc_0",
                "title": "DOKUMENT",
                "text": clean_text or "Leeres Dokument"
            }]

    return sections


def load_sections_from_pdf(path: str) -> list[dict]:
    """
    Lädt Text aus PDF-Datei und segmentiert in Abschnitte
    
    Args:
        path: Pfad zur PDF-Datei
        
    Returns:
        Liste von Abschnitten (gleiches Format wie load_sections_from_txt)
    """
    try:
        import PyPDF2
        
        text_parts = []
        with open(path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Seite {page_num} ---\n{text}")
                except Exception as e:
                    print(f"Fehler beim Extrahieren von Seite {page_num}: {e}")
        
        if not text_parts:
            return []
        
        # Kombiniere alle Seiten
        full_text = "\n".join(text_parts)
        
        # Speichere als temporäre TXT-Datei für weiteres Parsing
        temp_txt = str(path).replace('.pdf', '_temp.txt')
        Path(temp_txt).write_text(full_text, encoding="utf-8")
        
        # Nutze bestehende TXT-Parsing-Logik
        sections = load_sections_from_txt(temp_txt)
        
        # Lösche temporäre Datei
        try:
            Path(temp_txt).unlink()
        except:
            pass
        
        return sections
        
    except ImportError:
        print("PyPDF2 nicht installiert. Bitte installiere: pip install PyPDF2")
        return []
    except Exception as e:
        print(f"Fehler beim Laden der PDF: {e}")
        return []


def load_sections_from_image(path: str) -> list[dict]:
    """
    Extrahiert Text aus Bildern/Fotos mit OCR (Optical Character Recognition)
    
    Args:
        path: Pfad zur Bilddatei (jpg, png, etc.)
        
    Returns:
        Liste von Abschnitten (gleiches Format wie load_sections_from_txt)
    """
    try:
        from PIL import Image
        import pytesseract
        
        # Lade Bild
        image = Image.open(path)
        
        # OCR: Extrahiere Text aus Bild
        # Nutze Deutsch als Sprache für bessere Erkennung
        try:
            text = pytesseract.image_to_string(image, lang='deu+eng')
        except:
            # Fallback: Nur Englisch wenn Deutsch nicht verfügbar
            text = pytesseract.image_to_string(image, lang='eng')
        
        if not text.strip():
            return []
        
        # Speichere als temporäre TXT-Datei für weiteres Parsing
        temp_txt = str(path).rsplit('.', 1)[0] + '_temp.txt'
        Path(temp_txt).write_text(text, encoding="utf-8")
        
        # Nutze bestehende TXT-Parsing-Logik
        sections = load_sections_from_txt(temp_txt)
        
        # Lösche temporäre Datei
        try:
            Path(temp_txt).unlink()
        except:
            pass
        
        return sections
        
    except ImportError:
        print("pytesseract oder Pillow nicht installiert. Bitte installiere: pip install pytesseract Pillow")
        return []
    except Exception as e:
        print(f"Fehler beim OCR aus Bild: {e}")
        return []
