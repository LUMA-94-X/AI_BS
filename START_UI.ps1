# PowerShell Script zum Starten der UI
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Starte Web-Oberflaeche (UI)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Die UI oeffnet sich automatisch im Browser..." -ForegroundColor Yellow
Write-Host "  Zum Beenden: Druecke Ctrl+C" -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Wechsel ins Script-Verzeichnis
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Prüfe ob venv existiert
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "FEHLER: venv nicht gefunden!" -ForegroundColor Red
    Write-Host "Bitte installiere zuerst das Virtual Environment." -ForegroundColor Red
    Read-Host "Druecke Enter zum Beenden"
    exit 1
}

# Aktiviere venv
Write-Host "Aktiviere Virtual Environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

# Installiere UI-Pakete
Write-Host "Installiere UI-Pakete (falls noetig)..." -ForegroundColor Green
python -m pip install --quiet streamlit plotly

Write-Host ""
Write-Host "Starte UI..." -ForegroundColor Green
Write-Host ""

# Starte Streamlit
python -m streamlit run ui/app.py

Read-Host "Druecke Enter zum Beenden"
