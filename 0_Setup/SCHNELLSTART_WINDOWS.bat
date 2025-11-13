@echo off
echo.
echo ========================================
echo   AI_BS Schnellstart
echo ========================================
echo.

REM Pruefe ob venv existiert
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual Environment nicht gefunden.
    echo Fuehre Setup aus...
    echo.
    call setup_windows.bat
    if %ERRORLEVEL% NEQ 0 exit /b 1
)

REM Aktiviere venv und starte Beispiel
echo [START] Fuehre Beispiel-Simulation aus...
echo.
call venv\Scripts\activate.bat
python beispiele\einfache_simulation.py

echo.
echo ========================================
echo   Simulation abgeschlossen!
echo ========================================
echo.
pause
