# Getting Started Guide

Ein Schritt-für-Schritt-Guide für die ersten Schritte mit dem EnergyPlus Automation Tool.

## Voraussetzungen prüfen

### 1. Python-Version prüfen

```bash
python --version
# Sollte Python 3.10 oder höher anzeigen
```

Falls Python nicht installiert ist:
- Download: https://www.python.org/downloads/
- Bei Installation: "Add Python to PATH" aktivieren!

### 2. EnergyPlus installieren

1. Besuchen Sie: https://energyplus.net/downloads
2. Laden Sie die neueste Version herunter (empfohlen: 23.2 oder höher)
3. Installieren Sie in das Standard-Verzeichnis:
   - **Windows**: `C:\EnergyPlusV23-2-0\`
   - **Linux**: `/usr/local/EnergyPlus-23-2-0/`
   - **macOS**: `/Applications/EnergyPlus-23-2-0/`

### 3. Überprüfen Sie die EnergyPlus-Installation

```bash
# Windows
"C:\EnergyPlusV23-2-0\energyplus.exe" --version

# Linux/macOS
/usr/local/EnergyPlus-23-2-0/energyplus --version
```

## Installation des Tools

### Schritt 1: Projekt herunterladen

```bash
# Falls git installiert ist
git clone <repository-url>
cd energyplus-automation

# Oder: ZIP-Datei herunterladen und entpacken
```

### Schritt 2: Virtual Environment erstellen

```bash
# Virtual Environment erstellen
python -m venv venv

# Aktivieren
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat

# Linux/macOS
source venv/bin/activate
```

Sie sollten jetzt `(venv)` vor Ihrer Kommandozeile sehen.

### Schritt 3: Dependencies installieren

```bash
# Alle erforderlichen Pakete installieren
pip install --upgrade pip
pip install -r requirements.txt
```

Dies installiert:
- eppy (EnergyPlus Python API)
- geomeppy (Geometrie-Handling)
- pandas (Datenverarbeitung)
- pydantic (Datenvalidierung)
- und weitere...

### Schritt 4: Installation überprüfen

```bash
# Python-Konsole starten
python

# Pakete importieren
>>> import eppy
>>> import pandas
>>> import pydantic
>>> print("Installation erfolgreich!")
>>> exit()
```

## Konfiguration

### Konfigurationsdatei anpassen

Öffnen Sie `config/default_config.yaml` in einem Texteditor:

```yaml
energyplus:
  # Passen Sie diesen Pfad an Ihre Installation an
  installation_path: "C:/EnergyPlusV23-2-0"  # Windows
  # installation_path: "/usr/local/EnergyPlus-23-2-0"  # Linux
  # installation_path: "/Applications/EnergyPlus-23-2-0"  # macOS

simulation:
  num_processes: 4  # Passen Sie an Ihre CPU-Kerne an
  output_dir: "output"
```

**Tipp**: Die Anzahl der Prozesse sollte nicht höher sein als die Anzahl Ihrer CPU-Kerne.

### Verzeichnisse erstellen

Die Verzeichnisse sollten bereits existieren, aber prüfen Sie:

```bash
# Diese Verzeichnisse sollten existieren
ls -la data/weather/
ls -la output/
ls -la config/
```

## Wetterdatei herunterladen

### Schritt 1: Wetterdatenquelle besuchen

Öffnen Sie: https://energyplus.net/weather

### Schritt 2: Ihren Standort wählen

1. Wählen Sie Ihre Region (z.B. Europa > Deutschland)
2. Wählen Sie Ihre Stadt oder die nächstgelegene Stadt
3. Klicken Sie auf "Download Weather File"

### Schritt 3: Datei platzieren

```bash
# Kopieren Sie die heruntergeladene EPW-Datei
# Beispiel:
cp ~/Downloads/DEU_Berlin.epw data/weather/

# Oder unter Windows:
# Kopieren Sie die Datei in den Ordner data\weather\
```

### Schritt 4: Dateiname notieren

Merken Sie sich den Dateinamen, z.B.:
- `DEU_Berlin.epw`
- `USA_CA_San.Francisco.epw`
- `AUT_Vienna.epw`

Sie benötigen diesen Namen für die Simulationen.

## Ihr erstes Beispiel ausführen

### Option 1: Nur Modell erstellen (ohne Wetterdatei)

```bash
# Dieses Skript erstellt nur das IDF-Modell
python examples/01_simple_box_simulation.py
```

Falls keine Wetterdatei vorhanden ist, wird eine Warnung angezeigt, aber das IDF wird trotzdem erstellt.

### Option 2: Vollständige Simulation (mit Wetterdatei)

Bearbeiten Sie zuerst `examples/01_simple_box_simulation.py`:

```python
# Zeile ~52, ändern Sie:
weather_file = Path("data/weather/example.epw")

# zu (mit Ihrem tatsächlichen Dateinamen):
weather_file = Path("data/weather/DEU_Berlin.epw")
```

Dann ausführen:

```bash
python examples/01_simple_box_simulation.py
```

### Erwartete Ausgabe

```
======================================================================
Simple Box Building Simulation Example
======================================================================

Building Geometry:
  Dimensions: 10.0m × 8.0m × 6.0m
  Number of floors: 2
  Floor area: 80.0 m²
  Total floor area: 160.0 m²
  Volume: 480.0 m³
  Window-to-wall ratio: 30%

Creating building model...
IDF file created: output/example_simple_box/simple_box.idf

Running EnergyPlus simulation...
This may take a few minutes...

======================================================================
Simulation Results
======================================================================
✓ Simulation completed successfully!
  Execution time: 45.23 seconds
  Output directory: output/example_simple_box/simulation_results
  SQL database: output/example_simple_box/simulation_results/simple_boxout.sql
  Size: 1234.5 KB

Next steps:
  - View results in the output directory
  - Open .htm file in a browser for summary reports
  - Query .sql file for detailed hourly data

======================================================================
Example completed successfully!
======================================================================
```

## Ergebnisse anschauen

### Im Browser

Öffnen Sie die HTML-Datei im Browser:

```bash
# Windows
start output/example_simple_box/simulation_results/simple_boxouttable.html

# Linux
xdg-open output/example_simple_box/simulation_results/simple_boxouttable.html

# macOS
open output/example_simple_box/simulation_results/simple_boxouttable.html
```

Hier sehen Sie:
- Zusammenfassungsberichte
- Heiz- und Kühlenergiebedarfe
- Komfort-Metriken
- Und vieles mehr

### SQL-Datenbank abfragen

```bash
# Python-Konsole starten
python
```

```python
import sqlite3
import pandas as pd

# Verbindung zur Datenbank
conn = sqlite3.connect("output/example_simple_box/simulation_results/simple_boxout.sql")

# Verfügbare Tabellen anzeigen
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
print(tables)

# Beispiel: Jahresenergiebedarf
query = """
SELECT
    RowName as Metric,
    Value,
    Units
FROM TabularDataWithStrings
WHERE ReportName = 'AnnualBuildingUtilityPerformanceSummary'
AND TableName = 'End Uses'
"""

df = pd.read_sql(query, conn)
print(df)
```

## Nächste Schritte

### 1. Parameter anpassen

Bearbeiten Sie `examples/01_simple_box_simulation.py` und ändern Sie:

```python
geometry = BuildingGeometry(
    length=15.0,      # Länge ändern
    width=12.0,       # Breite ändern
    height=9.0,       # Höhe ändern (3 Geschosse)
    num_floors=3,     # Anzahl Geschosse
    window_wall_ratio=0.4,  # Mehr Fenster
    orientation=180.0  # Süd-orientiert
)
```

### 2. Batch-Simulationen ausprobieren

```bash
python examples/02_batch_simulation.py
```

Dies führt 5 verschiedene Gebäudevarianten parallel aus.

### 3. Eigenes Skript erstellen

Erstellen Sie eine neue Datei `my_simulation.py`:

```python
from pathlib import Path
from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.simulation.runner import EnergyPlusRunner

# Ihr Gebäude
geometry = BuildingGeometry(
    length=20.0,
    width=15.0,
    height=12.0,
    num_floors=4,
    window_wall_ratio=0.25,
    orientation=0.0
)

# Modell erstellen
generator = SimpleBoxGenerator()
idf_path = "output/my_building.idf"
idf = generator.create_model(geometry, idf_path=idf_path)
print(f"Modell erstellt: {idf_path}")

# Simulation
runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=idf_path,
    weather_file="data/weather/DEU_Berlin.epw",
    output_dir="output/my_simulation"
)

if result.success:
    print("Erfolg!")
else:
    print(f"Fehler: {result.error_message}")
```

## Häufige Probleme

### Problem 1: "EnergyPlus executable not found"

**Lösung**:
1. Überprüfen Sie, ob EnergyPlus installiert ist
2. Öffnen Sie `config/default_config.yaml`
3. Setzen Sie `installation_path` auf den korrekten Pfad

### Problem 2: "ModuleNotFoundError"

**Lösung**:
```bash
# Virtual Environment aktivieren
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Dependencies neu installieren
pip install -r requirements.txt
```

### Problem 3: Simulation dauert sehr lange

**Mögliche Ursachen**:
- Zu feines Zeitintervall (Standard: 4 Steps/Stunde ist OK)
- Sehr komplexes Gebäude
- Langsamer Computer

**Lösung**:
- Reduzieren Sie die Anzahl der Zonen
- Verwenden Sie "IdealLoadsAirSystem" statt detaillierter HVAC
- Erhöhen Sie nicht `num_processes` über Ihre CPU-Kerne hinaus

### Problem 4: "Fatal Error" in Simulation

**Lösung**:
1. Öffnen Sie die `.err` Datei im Output-Verzeichnis
2. Suchen Sie nach "** Fatal **"
3. Häufige Fehler:
   - Zu kleine Zonen (< 10 m³) → Vergrößern Sie das Gebäude
   - Fehlende Materialien → Überprüfen Sie `src/materials/standard_constructions.py`
   - Ungültige Geometrie → Prüfen Sie die Geometrie-Parameter

## Weitere Hilfe

- **Dokumentation**: Siehe `docs/` Ordner
- **Beispiele**: Siehe `examples/` Ordner
- **EnergyPlus Docs**: https://energyplus.net/documentation
- **eppy Tutorial**: https://eppy.readthedocs.io/en/latest/tutorial.html

## Zusammenfassung

Sie sollten jetzt in der Lage sein:
- ✓ Das Tool zu installieren und zu konfigurieren
- ✓ Einfache Gebäudemodelle zu erstellen
- ✓ EnergyPlus-Simulationen auszuführen
- ✓ Ergebnisse anzuschauen und zu analysieren
- ✓ Parameter zu variieren und eigene Modelle zu erstellen

Viel Erfolg mit Ihren Gebäudesimulationen!
