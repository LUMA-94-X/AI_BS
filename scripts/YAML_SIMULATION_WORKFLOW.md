# 📋 YAML Simulation Workflow - Komplette Anleitung

Schritt-für-Schritt Prozess für reproduzierbare EnergyPlus-Simulationen mit YAML-Konfigurationsdateien.

---

## 📑 Inhaltsverzeichnis

1. [Voraussetzungen](#-voraussetzungen)
2. [YAML-Konfiguration erstellen](#-yaml-konfiguration-erstellen)
3. [Konfiguration validieren](#-konfiguration-validieren)
4. [Simulation ausführen](#-simulation-ausführen)
5. [Ergebnisse analysieren](#-ergebnisse-analysieren)
6. [Troubleshooting](#-troubleshooting)
7. [Best Practices](#-best-practices)
8. [Erweiterte Workflows](#-erweiterte-workflows)

---

## ✅ Voraussetzungen

### 1. Software installieren

**Python 3.10+**
```bash
# Prüfen
python --version  # oder python3 --version
```

**EnergyPlus 23.2+**
- Download: https://github.com/NREL/EnergyPlus/releases
- Installation: Standard-Pfad verwenden (C:/EnergyPlusV25-1-0 oder /usr/local/EnergyPlus-25-1-0)

**Projekt-Dependencies**
```bash
# Setup-Script ausführen (empfohlen)
# Windows:
0_Setup\SCHNELLSTART_WINDOWS.bat

# Linux/macOS:
bash 0_Setup/setup_linux.sh

# Oder manuell:
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r 0_Setup/requirements.txt
```

### 2. EnergyPlus-Pfad prüfen

```bash
python -c "from core.config import get_config; print(get_config().energyplus.get_executable_path())"
```

**Expected Output:**
```
/mnt/c/EnergyPlusV25-1-0/energyplus.exe  # WSL
C:\EnergyPlusV25-1-0\energyplus.exe      # Windows
/usr/local/EnergyPlus-25-1-0/energyplus  # Linux
```

**Falls nicht gefunden:**
- Bearbeite `config/default_config.yaml`
- Setze `energyplus.installation_path` auf deinen Pfad

### 3. Wetterdaten bereitstellen

**Standard-Location:**
```
resources/energyplus/weather/austria/example.epw  ✓ Bereits vorhanden
```

**Zusätzliche EPW-Dateien:**
1. Download von https://energyplus.net/weather
2. Speichern in `resources/energyplus/weather/{land}/`
3. Naming: `{LAND}_{STADT}_{DATASET}.epw` (z.B. `DEU_Berlin_IWEC.epw`)

---

## 🏗️ YAML-Konfiguration erstellen

### Workflow-Auswahl

Das Tool unterstützt **zwei Workflows**:

1. **SimpleBox** - Parametrisches Modell für schnelle Studien
2. **Energieausweis** - 5-Zonen-Modell basierend auf Energieausweis-Daten (NEU!)

### Methode 1: Von Template kopieren (Empfohlen)

**1. Wähle passendes Template:**

```bash
# SimpleBox - Residential:
cp scenarios/efh_standard.yaml scenarios/mein_gebaeude.yaml

# SimpleBox - High-performance:
cp scenarios/efh_passivhaus.yaml scenarios/mein_passivhaus.yaml

# SimpleBox - Commercial:
cp scenarios/office_small.yaml scenarios/mein_buero.yaml

# Energieausweis - 5-Zone Model (NEU!):
cp scenarios/energieausweis_efh_example.yaml scenarios/mein_ea_gebaeude.yaml
```

**2. Bearbeite die Konfiguration:**

```bash
# Mit Editor deiner Wahl:
nano scenarios/mein_gebaeude.yaml
code scenarios/mein_gebaeude.yaml
vim scenarios/mein_gebaeude.yaml
```

### Methode 2: Von Grund auf erstellen

#### SimpleBox-Workflow

**Minimal-Beispiel:**

```yaml
# scenarios/mein_gebaeude.yaml
name: "Mein Gebäude"
description: "Beschreibung des Gebäudes"
version: "1.0"

building:
  name: "Gebaeude_2025"
  building_type: "residential"  # oder "office", "retail", "mixed"
  source: "simplebox"

  geometry:
    length: 12.0        # Länge in Metern
    width: 10.0         # Breite in Metern
    height: 6.0         # Gesamthöhe in Metern
    num_floors: 2       # Anzahl Geschosse
    window_wall_ratio: 0.25  # Fensterflächenanteil (0.0 - 1.0)
    orientation: 0.0    # Ausrichtung in Grad (0 = Norden)

  envelope:
    # U-Werte in W/m²K
    wall_u_value: 0.30
    roof_u_value: 0.25
    floor_u_value: 0.35
    window_u_value: 1.3
    window_shgc: 0.6    # Solar Heat Gain Coefficient

  default_zone:
    zone_type: "residential"

    # Interne Lasten
    people_density: 0.02      # Personen pro m²
    lighting_power: 5.0       # W/m²
    equipment_power: 3.0      # W/m²

    # Zeitpläne
    occupancy_schedule: "residential"
    lighting_schedule: "residential"
    equipment_schedule: "residential"

    # Infiltration
    infiltration_rate: 0.5    # Luftwechselrate (ACH)

hvac:
  system_type: "ideal_loads"

  ideal_loads:
    heating_setpoint: 20.0    # Heizgrenze °C
    cooling_setpoint: 26.0    # Kühlgrenze °C
    outdoor_air_flow_rate: 0.0
    economizer: false

simulation:
  weather_file: "resources/energyplus/weather/austria/example.epw"

  period:
    start_month: 1
    start_day: 1
    end_month: 12
    end_day: 31

  output:
    output_dir: "output/mein_gebaeude"
    save_idf: true
    save_sql: true

    output_variables:
      - "Zone Mean Air Temperature"
      - "Zone Air System Sensible Heating Energy"
      - "Zone Air System Sensible Cooling Energy"

    reporting_frequency: "Hourly"

  timeout: 3600  # Sekunden
```

#### Energieausweis-Workflow (NEU!)

**Minimal-Beispiel mit Energieausweis-Daten:**

```yaml
# scenarios/mein_ea_gebaeude.yaml
name: "EA Gebäude 2010"
description: "5-Zonen-Modell basierend auf Energieausweis"
version: "1.0"

building:
  name: "EFH_2010_5Zone"
  building_type: "residential"
  source: "energieausweis"  # WICHTIG: Workflow-Selektor

  energieausweis:
    # Pflichtfelder aus Energieausweis
    nettoflaeche_m2: 150.0
    u_wert_wand: 0.28
    u_wert_dach: 0.20
    u_wert_boden: 0.35
    u_wert_fenster: 1.3

    # Optional: Hüllflächen (für Geometrie-Rekonstruktion)
    wandflaeche_m2: 240.0
    dachflaeche_m2: 80.0
    bodenflaeche_m2: 80.0

    # Geometrie-Hints
    anzahl_geschosse: 2
    geschosshoehe_m: 2.8
    aspect_ratio_hint: 1.3

    # Fenster (exakte Flächen nach Orientierung ODER window_wall_ratio)
    fenster:
      nord_m2: 8.0
      ost_m2: 12.0
      sued_m2: 20.0
      west_m2: 10.0

    g_wert_fenster: 0.6       # g-Wert / SHGC

    # Lüftung
    luftwechselrate_h: 0.5
    infiltration_ach50: 4.0   # Optional: Blower-Door-Wert

    # Metadata
    gebaeudetyp: "EFH"        # EFH, MFH, oder NWG
    baujahr: 2010

  # Berechnete Geometrie (wird aus EA-Daten rekonstruiert - optional)
  calculated_geometry:
    length: 10.0
    width: 8.0
    height: 5.6
    num_floors: 2
    window_wall_ratio: 0.21
    orientation: 0.0

  default_zone:
    zone_type: "residential"
    people_density: 0.02
    lighting_power: 5.0
    equipment_power: 3.0
    infiltration_rate: 0.5

hvac:
  system_type: "ideal_loads"
  ideal_loads:
    heating_setpoint: 20.0
    cooling_setpoint: 26.0

simulation:
  weather_file: "resources/energyplus/weather/austria/example.epw"
  timestep: 4

  period:
    start_month: 1
    start_day: 1
    end_month: 12
    end_day: 31

  output:
    output_dir: "output/ea_efh_2010"
    save_idf: true
    save_sql: true
    output_variables:
      - "Zone Mean Air Temperature"
      - "Zone Air System Sensible Heating Energy"
      - "Zone Air System Sensible Cooling Energy"
    reporting_frequency: "Hourly"

  timeout: 3600
```

**Vorteile des Energieausweis-Workflows:**
- ✅ Realistische U-Werte direkt aus Energieausweis
- ✅ 5-Zonen-Modell (Nord, Ost, Süd, West, Core) für genauere Orientierungs-Effekte
- ✅ Geometrie-Rekonstruktion aus Hüllflächen
- ✅ Fenster nach Orientierung individuell anpassbar
- ✅ Export aus Web-UI → Simulation via CLI reproduzierbar

### 🎨 Anpassung: Wichtige Parameter

#### Geometrie
```yaml
geometry:
  length: 15.0          # Gebäudelänge
  width: 12.0           # Gebäudebreite
  height: 9.0           # Gesamthöhe
  num_floors: 3         # Anzahl Geschosse
  floor_height: 3.0     # Höhe pro Geschoss (optional, überschreibt height)
  window_wall_ratio: 0.30  # 30% Fensteranteil
  orientation: 45.0     # 45° gedreht (Südost)
```

#### Envelope (Gebäudehülle)
```yaml
envelope:
  # Typische U-Werte für verschiedene Standards:

  # Altbau (vor 1980):
  wall_u_value: 1.2
  roof_u_value: 0.8
  window_u_value: 5.0

  # Standard (1980-2000):
  wall_u_value: 0.5
  roof_u_value: 0.4
  window_u_value: 2.8

  # Neubau (nach 2000):
  wall_u_value: 0.30
  roof_u_value: 0.25
  window_u_value: 1.3

  # Niedrigenergie:
  wall_u_value: 0.20
  roof_u_value: 0.18
  window_u_value: 1.0

  # Passivhaus:
  wall_u_value: 0.10
  roof_u_value: 0.10
  window_u_value: 0.80
```

#### Interne Lasten
```yaml
default_zone:
  # Residential:
  people_density: 0.02      # 2 Personen pro 100m²
  lighting_power: 4.0       # W/m²
  equipment_power: 3.0      # W/m²

  # Office:
  people_density: 0.05      # 5 Personen pro 100m²
  lighting_power: 10.0      # W/m²
  equipment_power: 8.0      # W/m²

  # Retail:
  people_density: 0.10      # 10 Personen pro 100m²
  lighting_power: 20.0      # W/m²
  equipment_power: 6.0      # W/m²
```

#### HVAC-Sollwerte
```yaml
hvac:
  ideal_loads:
    # Komfort-Standard:
    heating_setpoint: 20.0
    cooling_setpoint: 26.0

    # Energiesparend:
    heating_setpoint: 19.0
    cooling_setpoint: 27.0

    # Hoher Komfort:
    heating_setpoint: 21.0
    cooling_setpoint: 24.0
```

---

## ✔️ Konfiguration validieren

**Vor der Simulation IMMER validieren!**

### Basis-Validation

```bash
python scripts/run_from_config.py scenarios/mein_gebaeude.yaml --validate-only
```

**Erfolgreiche Validation:**
```
INFO - Loading configuration: scenarios/mein_gebaeude.yaml
INFO - ✓ Loaded: Mein Gebäude
INFO - Validating configuration...
INFO -   ✓ Weather file: example.epw
INFO -   ✓ Geometry: 12.0m × 10.0m × 6.0m
INFO -   ✓ Floors: 2
INFO -   ✓ WWR: 25.0%
INFO -   ✓ Total floor area: 240.0 m²
INFO - Configuration is valid!
INFO - Validation complete (--validate-only mode)
```

### Typische Validierungsfehler

**1. Wetterdatei nicht gefunden:**
```
FileNotFoundError: Weather file not found: resources/energyplus/weather/germany/berlin.epw
```
→ **Lösung:** EPW-Datei herunterladen und unter `resources/energyplus/weather/germany/` speichern

**2. Ungültige Werte:**
```
pydantic.ValidationError:
  window_wall_ratio
    Input should be less than or equal to 1 [type=less_than_equal]
```
→ **Lösung:** WWR muss zwischen 0.0 und 1.0 liegen (z.B. 0.3 für 30%)

**3. YAML-Syntaxfehler:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```
→ **Lösung:** YAML-Syntax prüfen (Einrückung, Doppelpunkte, etc.)

### Validation-Checkliste

- [ ] YAML-Syntax korrekt (Einrückung mit Leerzeichen, nicht Tabs)
- [ ] Alle U-Werte > 0
- [ ] Window-Wall-Ratio zwischen 0.0 und 1.0
- [ ] Gebäudedimensionen > 0
- [ ] Wetterdatei existiert
- [ ] Output-Verzeichnis schreibbar
- [ ] Setpoints sinnvoll (heating < cooling)

---

## 🚀 Simulation ausführen

### Basis-Ausführung

```bash
python scripts/run_from_config.py scenarios/mein_gebaeude.yaml
```

**Output während der Ausführung:**
```
INFO - Loading configuration: scenarios/mein_gebaeude.yaml
INFO - ✓ Loaded: Mein Gebäude
INFO - Validating configuration...
INFO -   ✓ Weather file: example.epw
INFO -   ✓ Geometry: 12.0m × 10.0m × 6.0m
INFO - Configuration is valid!
============================================================
Starting simulation: Mein Gebäude
============================================================
INFO - Output directory: /path/to/output/mein_gebaeude
INFO - Creating building model...
INFO -   Building: 12.0m × 10.0m × 6.0m
INFO -   Floor area: 240.0 m²
INFO -   ✓ IDF created: building.idf
INFO - Adding HVAC system (Ideal Loads)...
INFO -   Heating setpoint: 20.0°C
INFO -   Cooling setpoint: 26.0°C
INFO -   ✓ HVAC system added
INFO - Running EnergyPlus simulation...
INFO - ✓ Simulation completed in 15.3s
============================================================
✓ Simulation completed successfully!
  Total time: 18.7s
  Output: /path/to/output/mein_gebaeude
============================================================
INFO - Calculating KPIs...

============================================================
SIMULATION RESULTS
============================================================
Energy Performance: 95.3 kWh/m²a
Efficiency Class:   B
Heating Demand:     78.2 kWh/m²a
Cooling Demand:     17.1 kWh/m²a
Thermal Comfort:    Gut

Assessment: Das Gebäude entspricht einem modernen Neubau-Standard...
============================================================
```

### Erweiterte Optionen

**Custom Output-Verzeichnis:**
```bash
python scripts/run_from_config.py scenarios/mein_gebaeude.yaml --output results/test_v1
```

**Verbose Logging:**
```bash
python scripts/run_from_config.py scenarios/mein_gebaeude.yaml --verbose
```

**Kombiniert:**
```bash
python scripts/run_from_config.py scenarios/mein_gebaeude.yaml \
    --output results/passivhaus_v3 \
    --verbose
```

### Execution-Zeit

**Typische Simulationszeiten:**
- Klein (120m², 1-2 Zonen): 10-20 Sekunden
- Mittel (500m², 3-5 Zonen): 20-40 Sekunden
- Groß (2000m², 10+ Zonen): 60-120 Sekunden

**Bei sehr langer Laufzeit (>5min):**
- Timeout erhöhen in YAML: `simulation.timeout: 7200`
- Gebäudekomplexität reduzieren
- EnergyPlus-Logs prüfen (`output/*/eplusout.err`)

---

## 📊 Ergebnisse analysieren

### Output-Verzeichnis-Struktur

Nach erfolgreicher Simulation:

```
output/mein_gebaeude/
├── building.idf              # Generiertes IDF-Modell
├── eplusout.sql              # Haupt-Ergebnisdatenbank (SQLite)
├── eplusout.err              # Error/Warning Log
├── eplusout.end              # Completion Status
├── eplusout.eio              # Input Echo
├── eplusout.mtr              # Meter outputs
├── eplusout.mtd              # Meter details
├── eplustbl.htm              # HTML-Report
└── (weitere CSV-Dateien)     # Detaillierte Ausgaben
```

### Wichtigste Dateien

**1. SQL-Datenbank (`eplusout.sql`)**
- Enthält ALLE Simulationsergebnisse
- Zugriff via SQLite oder Python (sqlite3, pandas)
- Beispiel:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('output/mein_gebaeude/eplusout.sql')
df = pd.read_sql("SELECT * FROM ReportVariableData", conn)
print(df.head())
```

**2. Error-Log (`eplusout.err`)**
- Warnings und Errors von EnergyPlus
- IMMER prüfen, auch bei erfolgreicher Simulation!
- Beispiel:
```bash
cat output/mein_gebaeude/eplusout.err | grep -i "severe\|fatal"
```

**3. HTML-Report (`eplustbl.htm`)**
- Übersichtliche Zusammenfassung
- Im Browser öffnen
- Zeigt: Energieverbrauch, Komfort, Lastgänge

### KPI-Auswertung (Automatisch)

Der Script berechnet automatisch:

```
Energy Performance: 95.3 kWh/m²a    # Gesamtenergiebedarf
Efficiency Class:   B                # Effizienzklasse (A++ bis H)
Heating Demand:     78.2 kWh/m²a    # Heizbedarf
Cooling Demand:     17.1 kWh/m²a    # Kühlbedarf
Thermal Comfort:    Gut              # Thermische Behaglichkeit
```

### Manuelle Analyse

**Mit Python:**
```python
from features.auswertung.kpi_rechner import KennzahlenRechner
from pathlib import Path

sql_file = Path("output/mein_gebaeude/eplusout.sql")
rechner = KennzahlenRechner(nettoflaeche_m2=240.0)
kpis = rechner.berechne_kennzahlen(sql_file=sql_file)

print(f"Heizenergie: {kpis.heizkennzahl_kwh_m2a:.1f} kWh/m²a")
print(f"Klasse: {kpis.effizienzklasse}")
```

**Mit SQLite direkt:**
```bash
sqlite3 output/mein_gebaeude/eplusout.sql "
  SELECT
    Name,
    SUM(Value) as Total_kWh
  FROM
    ReportVariableData
  WHERE
    Name LIKE '%Heating Energy%'
  GROUP BY
    Name;
"
```

### Visualisierung

**HTML-Dashboard erstellen:**
```python
from features.auswertung.visualisierung import ErgebnisVisualisierer
from pathlib import Path

viz = ErgebnisVisualisierer()
sql_file = Path("output/mein_gebaeude/eplusout.sql")

# Dashboard erstellen
dashboard = viz.erstelle_dashboard(kpis, sql_file)
dashboard.write_html("output/mein_gebaeude/dashboard.html")
```

**Im Browser öffnen:**
```bash
# Windows
start output/mein_gebaeude/dashboard.html

# Linux
xdg-open output/mein_gebaeude/dashboard.html

# macOS
open output/mein_gebaeude/dashboard.html
```

---

## 🔧 Troubleshooting

### Problem 1: EnergyPlus nicht gefunden

**Fehler:**
```
FileNotFoundError: Could not auto-detect EnergyPlus installation
```

**Lösung:**
1. Prüfe Installation:
   ```bash
   ls /mnt/c/EnergyPlusV25-1-0/  # WSL
   ls C:\EnergyPlusV25-1-0\      # Windows
   ```

2. Setze Pfad in `config/default_config.yaml`:
   ```yaml
   energyplus:
     installation_path: "/mnt/c/EnergyPlusV25-1-0"  # Deinen Pfad
   ```

### Problem 2: Simulation fehlgeschlagen

**Fehler:**
```
RuntimeError: Simulation failed: EnergyPlus terminated with errors
```

**Debug-Schritte:**

1. **Error-Log prüfen:**
   ```bash
   cat output/mein_gebaeude/eplusout.err | grep "** Severe\|** Fatal"
   ```

2. **Häufige Fehler:**

   **a) Zu kleine Zonen:**
   ```
   ** Severe  ** Zone="Zone1" is too small
   ```
   → Gebäude größer machen (length, width erhöhen)

   **b) Ungültige Konstruktionen:**
   ```
   ** Severe  ** Construction has invalid layers
   ```
   → U-Werte prüfen (müssen > 0 sein)

   **c) Fenster zu groß:**
   ```
   ** Severe  ** Window area exceeds wall area
   ```
   → WWR reduzieren (z.B. von 0.4 auf 0.3)

3. **IDF manuell prüfen:**
   ```bash
   cat output/mein_gebaeude/building.idf | less
   ```

### Problem 3: Unrealistische Ergebnisse

**Symptom:** Energiebedarf viel zu hoch/niedrig

**Checks:**

1. **U-Werte plausibel?**
   ```yaml
   # FALSCH:
   wall_u_value: 30.0    # Viel zu hoch!

   # RICHTIG:
   wall_u_value: 0.30    # W/m²K
   ```

2. **Infiltration realistisch?**
   ```yaml
   # Zu hoch (unrealistisch viel Lüftungsverluste):
   infiltration_rate: 5.0

   # Realistisch:
   infiltration_rate: 0.5
   ```

3. **Interne Lasten korrekt?**
   ```yaml
   # Zu hoch (Büro-Loads für Wohnhaus):
   people_density: 0.10
   lighting_power: 20.0

   # Für Wohnhaus:
   people_density: 0.02
   lighting_power: 5.0
   ```

### Problem 4: Python-Import-Fehler

**Fehler:**
```
ModuleNotFoundError: No module named 'eppy'
```

**Lösung:**
```bash
# Virtual Environment aktivieren
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r 0_Setup/requirements.txt
```

### Problem 5: Permission Denied

**Fehler:**
```
PermissionError: [Errno 13] Permission denied: 'output/mein_gebaeude'
```

**Lösung:**
- Output-Verzeichnis anderswo: `--output ~/simulations/test1`
- Schreibrechte prüfen: `chmod 755 output/`

---

## 💡 Best Practices

### 1. Naming Conventions

**YAML-Dateien:**
```
scenarios/
├── efh_standard_2000.yaml          # Jahr/Standard
├── efh_passivhaus_sued.yaml        # Besonderheit
├── office_3floors_berlin.yaml      # Größe, Standort
├── retail_shopping_center.yaml     # Typ
└── test_high_insulation.yaml       # Experimentell
```

**Output-Verzeichnisse:**
```yaml
output:
  output_dir: "output/projektname_variante_datum"
  # Beispiele:
  # "output/efh_passivhaus_v1_20250113"
  # "output/office_berlin_baseline"
  # "output/test_wwr_30"
```

### 2. Version Control (Git)

**YAML-Dateien tracken:**
```bash
git add scenarios/mein_gebaeude.yaml
git commit -m "Add: EFH Passivhaus configuration"
```

**Output NICHT committen:**
```bash
# .gitignore sollte enthalten:
output/
*.sql
*.idf
```

**Ergebnisse dokumentieren:**
```bash
# In separater Datei:
scenarios/results_summary.md
```

### 3. Parameter-Studien

**Mehrere Varianten erstellen:**
```bash
# Basis-Config
cp scenarios/efh_standard.yaml scenarios/study_baseline.yaml

# Variante 1: Bessere Dämmung
cp scenarios/study_baseline.yaml scenarios/study_insulation_improved.yaml
# → wall_u_value: 0.20 (statt 0.30)

# Variante 2: Mehr Fenster
cp scenarios/study_baseline.yaml scenarios/study_windows_40.yaml
# → window_wall_ratio: 0.40 (statt 0.25)

# Batch-Ausführung
for config in scenarios/study_*.yaml; do
    python scripts/run_from_config.py "$config"
done
```

### 4. Dokumentation

**In YAML-Kommentaren:**
```yaml
building:
  geometry:
    # Gebäudeabmessungen basierend auf Grundriss v2.1
    length: 12.5  # Angepasst für bessere Raumaufteilung
    width: 10.0

  envelope:
    # U-Werte aus Energieausweis 2024
    wall_u_value: 0.28  # Nachgewiesen durch Thermografie
```

**Separate README:**
```markdown
# scenarios/my_project/README.md

## Projekt: Passivhaus Musterstraße

### Varianten
- baseline.yaml: Ist-Zustand
- variant_a.yaml: Passivhaus-Sanierung
- variant_b.yaml: Standard-Sanierung

### Ergebnisse
- Baseline: 180 kWh/m²a (Klasse D)
- Variant A: 12 kWh/m²a (Passivhaus!)
- Variant B: 65 kWh/m²a (Klasse B)
```

### 5. Qualitätssicherung

**Checkliste vor finaler Simulation:**

- [ ] Validation durchgeführt (`--validate-only`)
- [ ] U-Werte plausibel geprüft
- [ ] Geometrie sinnvoll (L/B-Verhältnis, Geschosshöhe)
- [ ] Interne Lasten für Gebäudetyp passend
- [ ] HVAC-Setpoints realistisch
- [ ] Wetterdatei für Standort korrekt
- [ ] Output-Verzeichnis eindeutig benannt
- [ ] YAML-Kommentare aussagekräftig
- [ ] Git-Commit mit sinnvoller Message

---

## 🔬 Erweiterte Workflows

### Batch-Processing

**Alle Szenarien simulieren:**
```bash
#!/bin/bash
# scripts/run_all_scenarios.sh

for scenario in scenarios/*.yaml; do
    echo "Running $scenario..."
    python scripts/run_from_config.py "$scenario" || echo "Failed: $scenario"
done
```

**Parallel (mit GNU Parallel):**
```bash
ls scenarios/*.yaml | parallel -j 4 python scripts/run_from_config.py {}
```

### Automatisierte Tests

**Test-Script:**
```python
# tests/test_scenarios.py
import subprocess
from pathlib import Path

scenarios = Path("scenarios").glob("*.yaml")

for scenario in scenarios:
    result = subprocess.run([
        "python", "scripts/run_from_config.py",
        str(scenario),
        "--validate-only"
    ], capture_output=True)

    if result.returncode != 0:
        print(f"❌ {scenario.name} validation failed")
    else:
        print(f"✅ {scenario.name} valid")
```

### Ergebnis-Vergleich

**Mehrere Simulationen vergleichen:**
```python
# scripts/compare_results.py
import pandas as pd
import sqlite3
from pathlib import Path

results = []

for sql_file in Path("output").glob("*/eplusout.sql"):
    conn = sqlite3.connect(sql_file)

    # Heizenergie extrahieren
    heating = pd.read_sql("""
        SELECT SUM(Value) as heating_kwh
        FROM ReportVariableData
        WHERE Name LIKE '%Heating Energy%'
    """, conn).iloc[0]['heating_kwh']

    results.append({
        'scenario': sql_file.parent.name,
        'heating_kwh': heating
    })

df = pd.DataFrame(results).sort_values('heating_kwh')
print(df)
```

### CI/CD Integration

**GitHub Actions Beispiel:**
```yaml
# .github/workflows/validate_scenarios.yml
name: Validate Scenarios

on: [push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install pydantic pyyaml

      - name: Validate all scenarios
        run: |
          for scenario in scenarios/*.yaml; do
            python scripts/run_from_config.py "$scenario" --validate-only
          done
```

---

## 📚 Weitere Ressourcen

**Projekt-Dokumentation:**
- `scenarios/README.md` - Vollständiges Schema
- `0_Setup/ERSTE_SCHRITTE.md` - Grundlagen-Tutorial
- `README.md` - Projekt-Übersicht

**EnergyPlus-Dokumentation:**
- https://energyplus.net/documentation
- https://bigladdersoftware.com/epx/docs/ (EPX Docs)

**Wetterdaten:**
- https://energyplus.net/weather
- https://climate.onebuilding.org/

**Support:**
- GitHub Issues: https://github.com/LUMA-94-X/AI_BS/issues
- EnergyPlus Helpdesk: https://energyplus.helpserve.com/

---

## 📝 Quick Reference

**Minimal Workflow:**
```bash
# 1. Template kopieren
cp scenarios/efh_standard.yaml scenarios/my_building.yaml

# 2. Anpassen (Editor)
nano scenarios/my_building.yaml

# 3. Validieren
python scripts/run_from_config.py scenarios/my_building.yaml --validate-only

# 4. Simulieren
python scripts/run_from_config.py scenarios/my_building.yaml

# 5. Ergebnisse prüfen
cat output/my_building/eplusout.err
open output/my_building/eplustbl.htm
```

**Wichtige Kommandos:**
```bash
# Validation
python scripts/run_from_config.py <config.yaml> --validate-only

# Simulation
python scripts/run_from_config.py <config.yaml>

# Custom Output
python scripts/run_from_config.py <config.yaml> --output <dir>

# Verbose
python scripts/run_from_config.py <config.yaml> --verbose

# Hilfe
python scripts/run_from_config.py --help
```

---

**Erstellt:** 2025-11-13
**Version:** 1.0
**Tool:** `run_from_config.py`
**Projekt:** AI_BS - EnergyPlus Automation Framework
