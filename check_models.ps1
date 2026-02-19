# Script zum Prüfen der geladenen Modelle
Write-Host "Prüfe geladene Modelle..." -ForegroundColor Cyan
docker exec chatbotproject-ollama-1 ollama list
Write-Host "`nErwartete Modelle:" -ForegroundColor Yellow
Write-Host "  - qwen2.5:7b (Hauptmodell)" -ForegroundColor White
Write-Host "  - qwen2.5:3b (Schnelles Modell)" -ForegroundColor White
Write-Host "  - llama3.2:1b (Fallback-Modell)" -ForegroundColor White
