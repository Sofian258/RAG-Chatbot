# Port-Konflikt-Management

## Problem
Beim Starten von Docker-Containern können Port-Konflikte auftreten, wenn Ports bereits belegt sind. Diese Scripts helfen dabei, Port-Konflikte automatisch zu erkennen und zu beheben.

## Scripts

### 1. `start-container.ps1` - Intelligenter Container-Start

Startet Container mit automatischer Port-Konflikt-Erkennung und -Behebung.

**Features:**
- ✅ Prüft ob Port belegt ist
- ✅ Zeigt welcher Prozess/Container den Port blockiert
- ✅ Bietet Lösungsoptionen:
  1. Automatisch freien Port finden
  2. Blockierenden Prozess beenden
  3. Docker-Container stoppen
  4. Abbrechen
- ✅ Aktualisiert automatisch `docker-compose.yml` bei Port-Änderung

**Verwendung:**
```powershell
.\start-container.ps1
# oder mit spezifischem Port:
.\start-container.ps1 -Port 9000
```

### 2. `check-ports.ps1` - Port-Status prüfen

Zeigt den Status aller wichtigen Ports (8000, 11434, 3000, 5000, 9000) und laufende Docker-Container.

**Verwendung:**
```powershell
.\check-ports.ps1
```

**Ausgabe:**
```
Port-Status:
  Port 8000 : 🔴 BELEGT (Docker)
    → Container: chatbotproject-chatbot-1 (ID: abc123)
  Port 11434 : ✅ FREI
  Port 3000 : ✅ FREI
```

## Workflow

### Standard-Workflow:
```powershell
# 1. Ports prüfen
.\check-ports.ps1

# 2. Container starten (mit Auto-Fix)
.\start-container.ps1
```

### Manueller Workflow:
```powershell
# Port-Konflikt manuell beheben
docker ps  # Zeige laufende Container
docker stop <container-id>  # Container stoppen

# Oder Prozess beenden
netstat -ano | findstr :8000  # Finde Prozess
taskkill /PID <pid> /F  # Prozess beenden
```

## Integration in Cursor

Diese Scripts können als **Tasks** in Cursor konfiguriert werden:

### `.vscode/tasks.json` (Cursor-kompatibel):
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start Container (Auto-Port-Fix)",
      "type": "shell",
      "command": "powershell",
      "args": ["-File", "${workspaceFolder}/start-container.ps1"],
      "problemMatcher": []
    },
    {
      "label": "Check Ports",
      "type": "shell",
      "command": "powershell",
      "args": ["-File", "${workspaceFolder}/check-ports.ps1"],
      "problemMatcher": []
    }
  ]
}
```

## Erweiterte Features

### Automatischer Port-Rebind
Das Script findet automatisch einen freien Port und aktualisiert `docker-compose.yml`:
- Startet bei Port 8000
- Prüft bis Port 8010
- Aktualisiert automatisch die Port-Mapping

### Docker-Container-Erkennung
Das Script erkennt automatisch, ob ein Port von einem Docker-Container belegt wird und bietet an, diesen zu stoppen.

## Troubleshooting

### Port bleibt belegt nach Stop
```powershell
# Container vollständig entfernen
docker-compose down

# Port manuell prüfen
.\check-ports.ps1
```

### Script-Fehler
```powershell
# PowerShell Execution Policy prüfen
Get-ExecutionPolicy

# Falls nötig, temporär ändern:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

## Zukünftige Verbesserungen

- [ ] Automatische Port-Auswahl ohne Benutzer-Interaktion
- [ ] Integration in Cursor's Docker-Start-Flow
- [ ] Port-Historie speichern
- [ ] Multi-Container-Port-Management
