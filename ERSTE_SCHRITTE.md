# 🚀 Erste Schritte

Eine Schritt-für-Schritt-Anleitung für deine erste Gebäudesimulation.

## ✅ Voraussetzungen prüfen

### 1. Python-Version

```bash
python --version  # Sollte >= 3.10 sein
```

### 2. EnergyPlus Installation

EnergyPlus herunterladen: https://github.com/NREL/EnergyPlus/releases

**Getestete Versionen:** 23.2, 25.1

```powershell
# Windows - Prüfen ob installiert
Test-Path "C:\EnergyPlusV25-1-0\energyplus.exe"
# oder
Test-Path "C:\EnergyPlusV23-2-0\energyplus.exe"
```

```bash
# Linux/Mac
ls /usr/local/EnergyPlus-23-2-0/energyplus
```

### 3. Abhängigkeiten installieren

**Windows:**
```powershell
# Virtual Environment erstellen
python -m venv venv
.\venv\Scripts\Activate.ps1

# Core-Pakete installieren
pip install eppy pandas pydantic numpy pyyaml tqdm plotly
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install eppy pandas pydantic numpy pyyaml tqdm plotly
```

**Optional - Web-UI (benötigt C++ Compiler):**
```bash
pip install streamlit  # Installiert auch pyarrow
```

## 🎯 Methode 1: Python-Script (Empfohlen - Funktioniert sofort!)

### Schritt 0: Windows-Schnellstart

```powershell
# Optional: Nutze das fertige Setup-Script
.\SCHNELLSTART_WINDOWS.bat
```

## 💻 Methode 1a: Python-Script manuell

### Schritt 1: Beispiel-Script ausführen

```powershell
# Windows (im aktivierten venv)
python beispiele\einfache_simulation.py
```

```bash
# Linux/macOS
python beispiele/einfache_simulation.py
```

Das Script:
- Erstellt ein Gebäude (20m × 12m, 2 Stockwerke)
- Fügt HVAC-System hinzu (Ideal Loads)
- Führt EnergyPlus-Simulation aus (~3-7 Sekunden)
- Berechnet Kennzahlen und Effizienzklasse
- Erstellt interaktives Dashboard

**Erwartete Ausgabe:**
```
🏢 Einfache Gebäudesimulation
1️⃣ Erstelle Gebäudegeometrie...
   ✅ Gebäude: 20.0m x 12.0m x 6.0m
2️⃣ Generiere IDF-Modell...
   ✅ IDF erstellt
3️⃣ Füge HVAC-System hinzu...
   ✅ HVAC-System hinzugefügt
4️⃣ Führe Simulation aus...
   ✅ Simulation erfolgreich! (2.6s)
5️⃣ Werte Ergebnisse aus...
   Energiekennzahl: 72.4 kWh/m²a
   Effizienzklasse: B
6️⃣ Erstelle Visualisierungen...
   ✅ Dashboard: output/einfache_simulation/dashboard.html
```

### Schritt 2: Dashboard öffnen

```powershell
# Windows - Dashboard im Browser öffnen
start output\einfache_simulation\dashboard.html
```

```bash
# Linux
xdg-open output/einfache_simulation/dashboard.html

# macOS
open output/einfache_simulation/dashboard.html
```

### Schritt 3: Eigene Simulationen

Erstelle eine neue Datei `meine_simulation.py`:

```python
import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

from features.geometrie.box_generator import SimpleBoxGenerator, BuildingGeometry
from features.hvac.ideal_loads import create_building_with_hvac
from features.simulation.runner import EnergyPlusRunner
from features.auswertung.kpi_rechner import KennzahlenRechner

# Deine Parameter
geometrie = BuildingGeometry(
    length=25.0,
    width=15.0,
    height=9.0,
    num_floors=3,
    window_wall_ratio=0.4,
)

# Gebäude erstellen
generator = SimpleBoxGenerator()
idf = generator.create_model(geometrie, "mein_gebaeude.idf")
idf = create_building_with_hvac(idf)
idf.save("mein_gebaeude.idf")

# Simulation
runner = EnergyPlusRunner()
result = runner.run_simulation(
    "mein_gebaeude.idf",
    "data/weather/example.epw",
    output_dir="output/meine_simulation"
)

# Auswertung
if result.success:
    rechner = KennzahlenRechner(geometrie.total_floor_area)
    kpis = rechner.berechne_kennzahlen(sql_file=result.sql_file)
    print(f"Effizienzklasse: {kpis.effizienzklasse}")
    print(f"Energiekennzahl: {kpis.energiekennzahl_kwh_m2a:.1f} kWh/m²a")
```

## 🌐 Methode 2: Web-Interface (In Entwicklung)

**Status:** Die Web-UI ist derzeit in Entwicklung. Nur die Startseite ist verfügbar.

### Voraussetzungen

```powershell
# Windows - Visual Studio Build Tools erforderlich für pyarrow
pip install streamlit
```

### Starten

```bash
python scripts/ui_starten.py
# Öffnet http://localhost:8501
```

**Geplante Features:**
- Geometrie-Editor mit 3D-Vorschau
- HVAC-System-Konfigurator
- Simulation mit Fortschrittsanzeige
- Interaktive Ergebnis-Dashboards

## 🐛 Problemlösung

### EnergyPlus nicht gefunden

**Option 1: Config-Datei anpassen**
```yaml
# config/default_config.yaml
energyplus:
  installation_path: "C:/EnergyPlusV25-1-0"  # Dein Pfad
```

**Option 2: Python-Code**
```python
from core.config import get_config, set_config

config = get_config()
config.energyplus.installation_path = "C:/EnergyPlusV25-1-0"
set_config(config)
```

### Wetterdatei fehlt

Lade eine EPW-Datei herunter:
- https://energyplus.net/weather
- Speichere sie in `data/weather/`

### Simulation schlägt fehl

Prüfe die Error-Datei:
```bash
cat output/*/eplusout.err
```

## 📚 Nächste Schritte

- 📖 Erkunde weitere Beispiele in `beispiele/`
- 🎨 Passe Parameter in der Web-UI an
- 🔬 Führe Parameterstudien durch
- 📊 Vergleiche verschiedene Varianten

## 💡 Tipps

1. **Kleine Gebäude zuerst**: Beginne mit 1-2 Stockwerken
2. **Ideal Loads**: Verwende zunächst "Ideal Loads" für HVAC
3. **Kurze Simulationen**: Teste mit 1 Tag statt 1 Jahr
4. **Validierung**: Prüfe die Ergebnisse auf Plausibilität

## ❓ Hilfe

Bei Problemen:
1. Prüfe die Logs in `output/*/eplusout.err`
2. Validiere die IDF-Datei mit EnergyPlus
3. Erstelle ein Issue auf GitHub

---

Viel Erfolg! 🎉
