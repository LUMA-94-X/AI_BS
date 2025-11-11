@echo off
echo ================================================================================
echo   Starte Web-Oberflaeche (UI)
echo ================================================================================
echo.
echo   Die UI oeffnet sich automatisch im Browser...
echo   Zum Beenden: Druecke Ctrl+C
echo.
echo ================================================================================
echo.

REM Wechsel ins Projekt-Verzeichnis
cd /d "%~dp0"

REM Pruefe ob venv existiert
if not exist "venv\Scripts\activate.bat" (
    echo FEHLER: venv nicht gefunden!
    echo Bitte installiere zuerst das Virtual Environment.
    pause
    exit /b 1
)

REM Aktiviere venv
call venv\Scripts\activate.bat

REM Installiere streamlit falls nicht vorhanden
echo Installiere UI-Pakete (falls noetig)...
python -m pip install --quiet streamlit plotly

echo.
echo Starte UI...
echo.

REM Starte Streamlit
python -m streamlit run ui/app.py

pause
