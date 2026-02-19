#!/usr/bin/env python3
"""Wende alle Änderungen direkt auf die Datei an"""

# Lese die Datei
with open('app/rag_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Ändere _extract_simple_answer - nur Werte zurückgeben
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Gesamtbetrag - nur Wert
    if 'return f"Der Gesamtbetrag beträgt' in line:
        new_lines.append('                return betrag_match.group(1).strip()  # NUR der Betrag\n')
        i += 1
        continue
    
    # Nettobetrag - nur Wert
    if 'return f"Der Nettobetrag beträgt' in line:
        new_lines.append('                return betrag_match.group(1).strip()  # NUR der Betrag\n')
        i += 1
        continue
    
    # Fälligkeitsdatum - nur Datum
    if 'return f"Die Rechnung ist bis zum' in line:
        new_lines.append('                    return fällig_match.group(1)  # NUR das Datum\n')
        i += 1
        continue
    
    # Rechnungsdatum - nur Datum
    if 'return f"Das Rechnungsdatum ist' in line:
        new_lines.append('                return date_match.group(1)  # NUR das Datum\n')
        i += 1
        continue
    
    # Datum - nur Datum
    if 'return f"Das Datum ist' in line:
        new_lines.append('                return date_match.group(1)  # NUR das Datum\n')
        i += 1
        continue
    
    # Rechnungsnummer - nur Nummer
    if 'return f"Die Rechnungsnummer ist' in line:
        new_lines.append('                return inv_match.group(1)  # NUR die Nummer\n')
        i += 1
        continue
    
    # Firma - nur Name
    if 'return f"Die Firma heißt {line}"' in line or 'return f"Die Firma heißt {firma_match.group(1)}"' in line:
        if '{line}' in line:
            new_lines.append('                        return line  # NUR der Firmenname\n')
        else:
            new_lines.append('                return firma_match.group(1)  # NUR der Firmenname\n')
        i += 1
        continue
    
    # Skonto - nur Prozentsatz
    if 'return f"Es gibt {skonto_prozent}% Skonto"' in line:
        new_lines.append('                return f"{skonto_prozent}%"  # NUR der Prozentsatz\n')
        i += 1
        continue
    
    # Komplexe Skonto-Berechnung entfernen
    if 'return f"Bei {skonto_prozent}% Skonto sparen Sie' in line:
        new_lines.append('                        return f"{skonto_prozent}%"  # NUR der Prozentsatz\n')
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

# Schreibe zurück
with open('app/rag_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ Änderungen angewendet")
