@echo off
echo.
echo ========================================
echo   Setup fuer AI_BS auf Windows
echo ========================================
echo.

REM Pruefe ob Python installiert ist
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FEHLER] Python ist nicht installiert oder nicht im PATH!
    echo.
    echo Bitte installiere Python von: https://www.python.org/downloads/
    echo WICHTIG: Waehle bei der Installation "Add Python to PATH"!
    echo.
    pause
    exit /b 1
)

echo [1/4] Python gefunden:
python --version
echo.

REM Loesche altes venv falls vorhanden
if exist "venv" (
    echo [2/4] Loesche altes Virtual Environment...
    rmdir /s /q venv
)

REM Erstelle neues venv
echo [3/4] Erstelle Virtual Environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [FEHLER] Konnte Virtual Environment nicht erstellen!
    pause
    exit /b 1
)

REM Installiere Dependencies
echo [4/4] Installiere Abhaengigkeiten...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo   Setup erfolgreich abgeschlossen!
echo ========================================
echo.
echo Naechste Schritte:
echo   1. Aktiviere das Environment: venv\Scripts\activate.bat
echo   2. Starte UI: python scripts\ui_starten.py
echo   3. ODER Beispiel: python beispiele\einfache_simulation.py
echo.
pause
