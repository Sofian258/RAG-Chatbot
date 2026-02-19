# Script zum Prüfen aller verwendeten Ports
Write-Host "Prüfe Ports..." -ForegroundColor Cyan
Write-Host ""

$ports = @(8000, 11434, 3000, 5000, 9000)
$dockerContainers = docker ps --format "{{.ID}}|{{.Names}}|{{.Ports}}" 2>$null

Write-Host "Port-Status:" -ForegroundColor Yellow
Write-Host ""

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
        $status = "BELEGT"
        $color = "Red"
        
        # Prüfe ob Docker-Container
        $dockerInfo = $dockerContainers | Select-String ":$port"
        if ($dockerInfo) {
            $status = "BELEGT (Docker)"
            $color = "Yellow"
        }
        
        Write-Host "  Port $port : $status" -ForegroundColor $color
        if ($process) {
            Write-Host "    → Prozess: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Gray
        }
        if ($dockerInfo) {
            $parts = ($dockerInfo -split "\|")
            Write-Host "    → Container: $($parts[1]) (ID: $($parts[0]))" -ForegroundColor Cyan
        }
    } else {
        Write-Host "  Port $port : FREI" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Docker-Container:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

 
