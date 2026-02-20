# Projekt-Erstellung Widget

Ein modernes Frontend-Widget für die Erstellung von Projekten bei Planvo (IT & Automation).

## Features

- ✅ Alle Felder aus dem Planvo-Text unterstützt
- ✅ Team-Feld optional (kann später ergänzt werden)
- ✅ Responsive Design
- ✅ Validierung und Fehlerbehandlung
- ✅ Erfolgs-Feedback mit Projekt-ID
- ✅ Modernes UI im Stil des Chat-Widgets

## Verwendung

### 1. Widget in HTML einbinden

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="widget/project.css">
</head>
<body>
  <!-- Dein Content -->
  
  <!-- Widget einbinden -->
  <script src="widget/project.js" data-api-url="http://localhost:8000/api/projects"></script>
</body>
</html>
```

### 2. Oder als eigenständige Seite öffnen

Öffne `widget/project.html` direkt im Browser.

### 3. API-URL anpassen

Standard: `http://localhost:8000/api/projects`

Anpassen über `data-api-url` Attribut:
```html
<script src="widget/project.js" data-api-url="https://deine-api.de/api/projects"></script>
```

## Unterstützte Felder

### Pflichtfeld
- **Name**: Kurzer Titel (z.B. "Firewall-Upgrade Standort B")

### Optionale Felder
- **Beschreibung**: Was gemacht werden soll
- **Ort**: Adresse oder "Remote"
- **Startdatum**: Geplanter Start (YYYY-MM-DD)
- **Enddatum**: Enddatum, falls bekannt
- **Projekttyp**: Automation, IT-Infrastruktur, Sicherheit, Kundenspezifisch
- **Ansprechpartner**: Wer entscheidet
- **Team**: Techniker oder Entwickler (kann später ergänzt werden)
- **Firma**: company_id (optional)

## API-Tests

Verwende das PowerShell-Test-Skript:

```powershell
.\test_project_api.ps1
```

Das Skript testet:
1. Projekt ohne Team erstellen
2. Team später hinzufügen
3. Projekt mit Team direkt erstellen
4. Alle Projekte auflisten
5. Nach Team filtern

## Beispiel-Requests

### Minimal (nur Name)
```json
POST /api/projects
{
  "name": "Firewall-Upgrade Standort B"
}
```

### Vollständig
```json
POST /api/projects
{
  "name": "SPS-Anpassung Linie 3",
  "description": "Integration neuer Sensorik",
  "ort": "Remote",
  "startdatum": "2024-12-15",
  "enddatum": "2025-01-15",
  "projekttyp": "Automation",
  "ansprechpartner": "Max Mustermann",
  "team_type": "Entwickler"
}
```

### Team später hinzufügen
```json
PUT /api/projects/{project_id}
{
  "team_type": "Techniker"
}
```

## Design

Das Widget verwendet:
- Gradient-Buttons (Lila/Blau)
- Moderne Formulare mit Fokus-States
- Responsive Design (Mobile-ready)
- Smooth Animations
- Erfolgs-Feedback mit Auto-Close

## Browser-Support

- Chrome/Edge (neueste Versionen)
- Firefox (neueste Versionen)
- Safari (neueste Versionen)
