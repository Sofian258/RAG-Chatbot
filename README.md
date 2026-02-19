# Cursor Tasks für Chatbot-Projekt

Dieses Verzeichnis enthält die Task-Konfiguration für das Chatbot-Projekt.

## Verfügbare Tasks

### Port-Management

**Check Ports**
- Prüft den Status aller wichtigen Ports (8000, 11434, 3000, 5000, 9000)
- Zeigt laufende Docker-Container an
- Identifiziert, welche Prozesse Ports blockieren

**Start Chatbot Container**
- Startet den Chatbot-Container mit automatischer Port-Konflikt-Erkennung
- Bietet Lösungsoptionen bei Port-Konflikten:
  - Automatisch freien Port finden
  - Blockierenden Prozess beenden
  - Docker-Container stoppen

### Container-Management

**Stop Chatbot Container**
- Stoppt alle Container des Chatbot-Projekts

**Restart Chatbot Container**
- Startet alle Container neu

**View Container Logs**
- Zeigt die Logs aller Container (letzte 50 Zeilen, live)

## Verwendung

### Über das Command Palette:
1. Drücken Sie `Ctrl+Shift+P` (oder `Cmd+Shift+P` auf Mac)
2. Tippen Sie "Tasks: Run Task"
3. Wählen Sie den gewünschten Task aus

### Über die Tastenkombination:
- `Ctrl+Shift+B` → Öffnet "Run Build Task" (für Build-Tasks)
- `Ctrl+Shift+T` → Öffnet "Run Test Task" (für Test-Tasks)

### Über das Terminal-Menü:
1. Öffnen Sie das Terminal (`Ctrl+`` `)
2. Klicken Sie auf das Dropdown-Menü "Tasks"
3. Wählen Sie den gewünschten Task aus

## Task-Gruppen

- **Build-Tasks**: Start Chatbot Container, Stop Chatbot Container, Restart Chatbot Container
- **Test-Tasks**: Check Ports, View Container Logs

## Hinweise

- Alle PowerShell-Scripts werden mit `-ExecutionPolicy Bypass` ausgeführt
- Die Tasks öffnen ein neues Terminal-Panel für die Ausgabe
- Bei interaktiven Scripts (z.B. Start Chatbot Container) können Sie im Terminal interagieren
