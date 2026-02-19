# Quick Start: Cursor Tasks

## Schnellstart

### Ports prüfen
1. `Ctrl+Shift+P` → `Tasks: Run Task` → `Check Ports`

### Container starten
1. `Ctrl+Shift+P` → `Tasks: Run Task` → `Start Chatbot Container`

##  Alle verfügbaren Tasks

| Task | Tastenkombination | Beschreibung |
|------|-------------------|--------------|
| **Check Ports** | `Ctrl+Shift+P` → `Tasks: Run Task` | Prüft Port-Status und Docker-Container |
| **Start Chatbot Container** | `Ctrl+Shift+B` (Build) | Startet Container mit Port-Konflikt-Fix |
| **Stop Chatbot Container** | `Ctrl+Shift+P` → `Tasks: Run Task` | Stoppt alle Container |
| **Restart Chatbot Container** | `Ctrl+Shift+P` → `Tasks: Run Task` | Startet Container neu |
| **View Container Logs** | `Ctrl+Shift+P` → `Tasks: Run Task` | Zeigt Container-Logs (live) |

##  Häufige Workflows

### Workflow 1: Container starten (mit Port-Check)
```
1. Ctrl+Shift+P
2. "Tasks: Run Task"
3. "Start Chatbot Container"
4. Bei Port-Konflikt: Option wählen (1-4)
```

### Workflow 2: Ports prüfen vor Start
```
1. Ctrl+Shift+P
2. "Tasks: Run Task"
3. "Check Ports"
4. Dann "Start Chatbot Container" ausführen
```

### Workflow 3: Container neu starten
```
1. Ctrl+Shift+P
2. "Tasks: Run Task"
3. "Restart Chatbot Container"
```

##  Tipps

- **Interaktive Tasks**: Bei "Start Chatbot Container" können Sie im Terminal interagieren
- **Logs ansehen**: "View Container Logs" zeigt live-Logs (mit `Ctrl+C` beenden)
- **Schnellzugriff**: `Ctrl+Shift+B` öffnet direkt Build-Tasks

## Troubleshooting

### Task wird nicht gefunden
- Prüfen Sie, ob `.vscode/tasks.json` existiert
- Laden Sie Cursor neu (`Ctrl+Shift+P` → `Developer: Reload Window`)

### PowerShell-Fehler
- Die Tasks verwenden automatisch `-ExecutionPolicy Bypass`
- Falls Probleme: PowerShell Execution Policy prüfen

### Port-Konflikte
- Verwenden Sie "Check Ports" vor dem Start
- "Start Chatbot Container" bietet automatische Lösungen

