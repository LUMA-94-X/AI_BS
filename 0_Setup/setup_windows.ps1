# AI_BS Setup für Windows (PowerShell)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup für AI_BS auf Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Prüfe ob Python installiert ist
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[FEHLER] Python ist nicht installiert oder nicht im PATH!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Bitte installiere Python von: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "WICHTIG: Wähle bei der Installation 'Add Python to PATH'!" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Drücke Enter zum Beenden"
    exit 1
}

Write-Host "[1/4] Python gefunden:" -ForegroundColor Green
python --version
Write-Host ""

# Lösche altes venv falls vorhanden
if (Test-Path "venv") {
    Write-Host "[2/4] Lösche altes Virtual Environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force venv
}

# Erstelle neues venv
Write-Host "[3/4] Erstelle Virtual Environment..." -ForegroundColor Green
python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FEHLER] Konnte Virtual Environment nicht erstellen!" -ForegroundColor Red
    Read-Host "Drücke Enter zum Beenden"
    exit 1
}

# Installiere Dependencies
Write-Host "[4/4] Installiere Abhängigkeiten..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup erfolgreich abgeschlossen!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Cyan
Write-Host "  1. Aktiviere das Environment: .\venv\Scripts\Activate.ps1"
Write-Host "  2. Starte UI: python scripts\ui_starten.py"
Write-Host "  3. ODER Beispiel: python beispiele\einfache_simulation.py"
Write-Host ""
Read-Host "Drücke Enter zum Beenden"
