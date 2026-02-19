# Script zum Laden der besten LLM-Modelle
Write-Host "=== Lade beste LLM-Modelle ===" -ForegroundColor Cyan
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

# Zeige verfügbare Modelle
Write-Host "=== Verfügbare Modelle (vorher) ===" -ForegroundColor Yellow
docker exec chatbotproject-ollama-1 ollama list
Write-Host ""

# Beste Modelle (nach Priorität)
$models = @(
    @{
        Name = "mixtral:8x22b"
        Description = "BESTES Reasoning-Modell (High-End)"
        Size = "~130-140 GB"
        VRAM = "128+ GB empfohlen"
    },
    @{
        Name = "qwen2.5:72b"
        Description = "High-End Reasoning"
        Size = "~45-50 GB"
        VRAM = "48+ GB empfohlen"
    },
    @{
        Name = "qwen2.5:32b"
        Description = "Strong Reasoning, Produktionstauglich"
        Size = "~20-25 GB"
        VRAM = "24+ GB empfohlen"
    }
)

Write-Host "=== Lade beste Modelle ===" -ForegroundColor Cyan
Write-Host "WARNUNG: Dies kann mehrere Stunden dauern und benötigt viel Speicherplatz!" -ForegroundColor Yellow
Write-Host ""

$downloaded = @()
$failed = @()

foreach ($model in $models) {
    Write-Host "Lade $($model.Name) ($($model.Description))..." -ForegroundColor Yellow
    Write-Host "  Größe: $($model.Size), VRAM: $($model.VRAM)" -ForegroundColor Gray
    
    $startTime = Get-Date
    $result = docker exec chatbotproject-ollama-1 ollama pull $model.Name 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMinutes
        Write-Host "✓ $($model.Name) erfolgreich geladen (Dauer: $([math]::Round($duration, 1)) Minuten)" -ForegroundColor Green
        $downloaded += $model.Name
    } else {
        Write-Host "✗ Fehler beim Laden von $($model.Name)" -ForegroundColor Red
        Write-Host "  $result" -ForegroundColor Red
        $failed += $model.Name
    }
    Write-Host ""
}

# Zeige Status
Write-Host "=== Status ===" -ForegroundColor Cyan
Write-Host "Erfolgreich geladen: $($downloaded.Count)" -ForegroundColor Green
if ($downloaded.Count -gt 0) {
    foreach ($model in $downloaded) {
        Write-Host "  ✓ $model" -ForegroundColor Green
    }
}

if ($failed.Count -gt 0) {
    Write-Host "Fehlgeschlagen: $($failed.Count)" -ForegroundColor Red
    foreach ($model in $failed) {
        Write-Host "  ✗ $model" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Verfügbare Modelle (nachher) ===" -ForegroundColor Yellow
docker exec chatbotproject-ollama-1 ollama list

# Erstelle Config-Datei mit besten Modellen
Write-Host ""
Write-Host "=== Erstelle Config-Datei ===" -ForegroundColor Cyan

$config = @{
    fast = @{
        model = "qwen2.5:3b"
        fallback = "llama3.2:1b"
        max_tokens = 150
        temperature = 0.1
        timeout = 10
        description = "Schnelles Modell für einfache Fragen"
    }
    standard = @{
        model = "qwen2.5:7b"
        fallback = "qwen2.5:3b"
        max_tokens = 400
        temperature = 0.2
        timeout = 30
        description = "Standard-Modell für normale Fragen"
    }
    reasoning = @{
        model = "mixtral:8x22b"
        fallback = "qwen2.5:72b"
        max_tokens = 1000
        temperature = 0.3
        timeout = 120
        description = "BESTES Reasoning-Modell für komplexe Fragen"
    }
}

# Prüfe welche Modelle verfügbar sind und passe Config an
$availableModels = docker exec chatbotproject-ollama-1 ollama list 2>&1 | Select-String -Pattern "qwen|mixtral" | ForEach-Object { $_.Line.Split()[0] }

if ($availableModels -notcontains "mixtral:8x22b") {
    if ($availableModels -contains "qwen2.5:72b") {
        Write-Host "⚠ mixtral:8x22b nicht verfügbar, nutze qwen2.5:72b als Reasoning-Modell" -ForegroundColor Yellow
        $config.reasoning.model = "qwen2.5:72b"
        $config.reasoning.fallback = "qwen2.5:32b"
    } elseif ($availableModels -contains "qwen2.5:32b") {
        Write-Host "⚠ mixtral:8x22b und qwen2.5:72b nicht verfügbar, nutze qwen2.5:32b als Reasoning-Modell" -ForegroundColor Yellow
        $config.reasoning.model = "qwen2.5:32b"
        $config.reasoning.fallback = "qwen2.5:7b"
    } else {
        Write-Host "⚠ Keine großen Reasoning-Modelle verfügbar, nutze qwen2.5:7b als Fallback" -ForegroundColor Yellow
        $config.reasoning.model = "qwen2.5:7b"
        $config.reasoning.fallback = "qwen2.5:3b"
    }
}

# Konvertiere zu JSON und speichere
$json = $config | ConvertTo-Json -Depth 10
$json | Out-File -FilePath "llm_config.json" -Encoding UTF8

Write-Host "✓ Config-Datei erstellt: llm_config.json" -ForegroundColor Green
Write-Host ""
Write-Host "=== Nächste Schritte ===" -ForegroundColor Cyan
Write-Host "1. Container neu starten: docker-compose restart chatbot" -ForegroundColor White
Write-Host "2. Oder Config-Pfad setzen: `$env:LLM_CONFIG_PATH='llm_config.json'" -ForegroundColor White
Write-Host "3. System nutzt jetzt automatisch die besten verfügbaren Modelle!" -ForegroundColor White
