@echo off
echo ================================================================================
echo   Starte EnergyPlus Simulation
echo ================================================================================
echo.

REM Aktiviere venv
call venv\Scripts\activate.bat

REM Starte Simulation
python examples\03_building_with_hvac_template.py

echo.
echo ================================================================================
echo   Fertig! Druecke eine Taste um Ergebnisse zu oeffnen...
echo ================================================================================
pause

REM Öffne Ergebnisse
explorer.exe output\building_with_hvac\simulation\

pause
