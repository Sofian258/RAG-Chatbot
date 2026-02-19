# Script zum Laden der fehlenden Modelle
Write-Host "Lade fehlende Modelle..." -ForegroundColor Cyan
Write-Host ""

# Prüfe ob Docker läuft
try {
    $null = docker ps 2>&1
    Write-Host "✓ Docker läuft" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker läuft nicht! Bitte starte Docker Desktop." -ForegroundColor Red
    exit 1
}

# Prüfe ob Container läuft
$containerRunning = docker ps --filter "name=chatbotproject-ollama-1" --format "{{.Names}}"
if (-not $containerRunning) {
    Write-Host "✗ Ollama-Container läuft nicht! Starte mit: docker-compose up -d" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Ollama-Container läuft" -ForegroundColor Green
Write-Host ""

# Lade qwen2.5:3b
Write-Host "Lade qwen2.5:3b (Schnelles Modell)..." -ForegroundColor Yellow
docker exec chatbotproject-ollama-1 ollama pull qwen2.5:3b
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ qwen2.5:3b geladen" -ForegroundColor Green
} else {
    Write-Host "✗ Fehler beim Laden von qwen2.5:3b" -ForegroundColor Red
}

Write-Host ""

# Lade llama3.2:1b
Write-Host "Lade llama3.2:1b (Fallback-Modell)..." -ForegroundColor Yellow
docker exec chatbotproject-ollama-1 ollama pull llama3.2:1b
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ llama3.2:1b geladen" -ForegroundColor Green
} else {
    Write-Host "✗ Fehler beim Laden von llama3.2:1b" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Status aller Modelle ===" -ForegroundColor Cyan
docker exec chatbotproject-ollama-1 ollama list
