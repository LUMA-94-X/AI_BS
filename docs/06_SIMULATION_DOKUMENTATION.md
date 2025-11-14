# 06 - Simulation & Verfügbare Daten

> **Modul:** EnergyPlus-Simulation und Output-Daten-Analyse
> **Zweck:** Vollständige Dokumentation des Simulations-Workflows und aller verfügbaren Daten
> **Zuletzt aktualisiert:** 2025-11-14

---

## Übersicht

Diese Dokumentation zeigt:
1. Wie die Simulation gestartet wird
2. Welche Output-Dateien erzeugt werden
3. **Welche Daten aktuell genutzt werden** (11 Variablen)
4. **Welche Daten verfügbar aber NICHT genutzt werden** (100+ Variablen!)
5. Ungenutztes Potential & Empfehlungen

---

## 1. Simulation starten

### 1.1 Einstiegspunkt: Web UI (03_Simulation.py)

**Button: "Simulation starten"**

```python
# Workflow-Unterscheidung:
if building_model['source'] == 'simplebox':
    # SimpleBox: IDF on-the-fly erstellen
    run_simplebox_simulation()
else:
    # 5-Zone: IDF aus Datei laden
    run_energieausweis_simulation()
```

---

### 1.2 SimpleBox-Simulation

```python
from features.geometrie.box_generator import SimpleBoxGenerator, BuildingGeometry
from features.hvac.ideal_loads import create_building_with_hvac
from features.simulation.runner import EnergyPlusRunner

# 1. Output-Verzeichnis
output_dir = Path("output") / f"simulation_{timestamp}"
output_dir.mkdir(parents=True, exist_ok=True)

# 2. BuildingGeometry erstellen
geometry = BuildingGeometry(
    length=building_model.geometry_summary['length'],
    width=building_model.geometry_summary['width'],
    height=building_model.geometry_summary['height'],
    num_floors=building_model.geometry_summary['num_floors'],
    window_wall_ratio=building_model.geometry_summary['window_wall_ratio'],
    orientation=0.0
)

# 3. IDF on-the-fly erstellen
generator = SimpleBoxGenerator()
idf = generator.create_model(
    geometry=geometry,
    idf_path=output_dir / "building.idf",
    sim_settings={
        'timestep': 4,
        'reporting_frequency': 'Hourly',
        'start_month': 1,
        'start_day': 1,
        'end_month': 12,
        'end_day': 31,
        'output_variables': [...]
    }
)

# 4. HVAC hinzufügen
hvac_config = st.session_state.get('hvac_config', {})
idf = create_building_with_hvac(
    idf,
    heating_setpoint=hvac_config['heating_setpoint'],
    cooling_setpoint=hvac_config['cooling_setpoint'],
    heating_enabled=hvac_config['heating_enabled'],
    cooling_enabled=hvac_config['cooling_enabled']
)

# 5. Speichern
idf.save()

# 6. Simulation ausführen
runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=str(output_dir / "building.idf"),
    weather_file=str(weather_path),
    output_dir=str(output_dir)
)
```

---

### 1.3 Energieausweis-Simulation

```python
# 1. IDF-Pfad aus BuildingModel
idf_path = building_model['idf_path']

# 2. Output-Verzeichnis
output_dir = Path("output") / f"simulation_{timestamp}"
output_dir.mkdir(parents=True, exist_ok=True)

# 3. IDF kopieren
shutil.copy(idf_path, output_dir / "building.idf")

# 4. Simulation ausführen (HVAC bereits im IDF!)
runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=str(output_dir / "building.idf"),
    weather_file=str(weather_path),
    output_dir=str(output_dir)
)
```

---

### 1.4 EnergyPlusRunner (runner.py)

**Hauptmethode: run_simulation()**

```python
class EnergyPlusRunner:
    def run_simulation(
        self,
        idf_path: Path,
        weather_file: Path,
        output_dir: Path,
        output_prefix: str = "eplus"
    ) -> SimulationResult:

        # 1. Prüfen: HVACTemplate-Objekte vorhanden?
        if self._needs_expand_objects(idf_path):
            # ExpandObjects ausführen
            expanded_idf = self._run_expand_objects(idf_path, output_dir)
            idf_path = expanded_idf

        # 2. WSL-Pfad-Konvertierung (Linux → Windows)
        if platform.system() == "Linux" and "microsoft" in platform.release().lower():
            idf_win = self._convert_wsl_to_windows_path(idf_path)
            epw_win = self._convert_wsl_to_windows_path(weather_file)
            out_win = self._convert_wsl_to_windows_path(output_dir)
        else:
            idf_win = idf_path
            epw_win = weather_file
            out_win = output_dir

        # 3. EnergyPlus-Executable holen
        from core.config import get_config
        config = get_config()
        energyplus_exe = config.energyplus.get_executable_path()

        # 4. EnergyPlus ausführen
        cmd = [
            str(energyplus_exe),
            "--weather", str(epw_win),
            "--output-directory", str(out_win),
            "--output-prefix", output_prefix,
            str(idf_win)
        ]

        start_time = time.time()

        result = subprocess.run(
            cmd,
            cwd=str(output_dir),  # WSL path!
            capture_output=True,
            text=True,
            timeout=config.simulation.timeout
        )

        execution_time = time.time() - start_time

        # 5. Ergebnis prüfen
        err_file = output_dir / f"{output_prefix}out.err"
        success = self._check_simulation_success(err_file)

        if success:
            return SimulationResult(
                success=True,
                idf_path=idf_path,
                output_dir=output_dir,
                execution_time=execution_time,
                sql_file=output_dir / f"{output_prefix}out.sql",
                csv_files=list(output_dir.glob(f"{output_prefix}*.csv"))
            )
        else:
            error_message = self._extract_error_message(err_file)
            return SimulationResult(
                success=False,
                error_message=error_message,
                execution_time=execution_time
            )
```

---

### 1.5 ExpandObjects

**Zweck:** Konvertiert HVACTEMPLATE-Objekte in vollständige HVAC-Objekte.

```python
def _needs_expand_objects(self, idf_path: Path) -> bool:
    """Prüft ob HVACTemplate-Objekte im IDF vorhanden"""
    with open(idf_path) as f:
        content = f.read()
    return "HVACTEMPLATE:" in content.upper()

def _run_expand_objects(self, idf_path: Path, output_dir: Path) -> Path:
    """
    Führt ExpandObjects.exe aus.

    CRITICAL:
    - Kopiert IDF als 'in.idf'
    - Kopiert 'Energy+.idd' ins Working Directory
    - Führt ExpandObjects.exe aus
    - Gibt 'expanded.idf' zurück
    """
    # 1. Dateien vorbereiten
    shutil.copy(idf_path, output_dir / "in.idf")

    # 2. Energy+.idd kopieren (CRITICAL!)
    idd_source = config.energyplus.installation_path / "Energy+.idd"
    shutil.copy(idd_source, output_dir / "Energy+.idd")

    # 3. ExpandObjects ausführen
    expand_exe = config.energyplus.installation_path / "ExpandObjects.exe"

    subprocess.run(
        [str(expand_exe)],
        cwd=str(output_dir),
        timeout=60
    )

    # 4. expanded.idf zurückgeben
    expanded_idf = output_dir / "expanded.idf"
    if not expanded_idf.exists():
        raise RuntimeError("ExpandObjects failed!")

    return expanded_idf
```

---

## 2. Output-Dateien

### 2.1 Übersicht

**Nach erfolgreicher Simulation:**

```
output/simulation_20251114_150000/
├── building.idf          # Original IDF (242 KB)
├── in.idf                # Kopie für ExpandObjects
├── expanded.idf          # Expandiertes IDF (309 KB) ← Wurde simuliert!
├── eplusout.sql          # ★★★ HAUPTDATENQUELLE (42 MB)
├── eplusout.err          # Fehler-/Warnungslog (45 KB)
├── eplustbl.csv          # Summary-Tabellen (156 KB)
├── eplustbl.htm          # HTML-Report
├── sqlite.err            # SQL-Log
└── eplusout.eso          # ASCII-Output (optional)
```

---

### 2.2 eplusout.sql (HAUPTDATENQUELLE)

**SQLite3-Datenbank mit 36 Tabellen:**

#### Wichtigste Tabellen

| Tabelle | Zweck | Aktuell genutzt? |
|---------|-------|------------------|
| `ReportData` | Zeitreihen-Daten (8760+ Stunden) | ✓ JA |
| `ReportDataDictionary` | Variablenliste mit IDs | ✓ JA |
| `Time` | Zeitstempel | ✓ JA |
| `Zones` | Zoneninformationen | ✗ NEIN |
| `Surfaces` | Surface-Geometrie | ✗ NEIN |
| `Materials` | Materialien | ✗ NEIN |
| `Constructions` | Konstruktionen | ✗ NEIN |
| `ZoneSizes` | Auslegungsgrößen | ✗ NEIN |
| `TabularData` | Summary-Reports | ✗ NEIN |

**SQL-Schema (vereinfacht):**

```sql
-- Variablen-Dictionary
CREATE TABLE ReportDataDictionary (
    ReportDataDictionaryIndex INTEGER PRIMARY KEY,
    Name TEXT,                      -- z.B. "Zone Mean Air Temperature"
    KeyValue TEXT,                  -- z.B. "Perimeter_North_F1"
    ReportingFrequency TEXT,        -- "Hourly", "Timestep", etc.
    Units TEXT                      -- z.B. "C"
);

-- Zeitreihen-Daten
CREATE TABLE ReportData (
    ReportDataIndex INTEGER PRIMARY KEY,
    TimeIndex INTEGER,
    ReportDataDictionaryIndex INTEGER,
    Value REAL
);

-- Zeit
CREATE TABLE Time (
    TimeIndex INTEGER PRIMARY KEY,
    Month INTEGER,
    Day INTEGER,
    Hour INTEGER,
    Minute INTEGER,
    DayOfYear INTEGER
);

-- Zonen
CREATE TABLE Zones (
    ZoneIndex INTEGER PRIMARY KEY,
    ZoneName TEXT,
    FloorArea REAL,
    Volume REAL
);
```

---

### 2.3 eplusout.err

**Fehler- und Warnungslog:**

```
   EnergyPlus Starting
   EnergyPlus, Version 23.2.0
   Processing Data Dictionary
   Processing Input File
   Initializing Simulation
   Reporting Surfaces
   Beginning Primary Simulation
   Initializing New Environment Parameters
   Warming up {1}
   Warming up {2}
   ...
   Starting Simulation at 01/01 for RUNPERIOD ANNUAL
   Updating Shadowing Calculations, Start Date=01/21
   Continuing Simulation at 01/21 for RUNPERIOD ANNUAL
   ...
   Writing final SQL reports
   EnergyPlus Run Time=00hr 00min 12.34sec
   EnergyPlus Completed Successfully-- 0 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 13sec
```

**Erfolgs-Check:**

```python
def _check_simulation_success(self, err_file: Path) -> bool:
    with open(err_file) as f:
        content = f.read()

    # Fatal Errors?
    if "** Fatal **" in content:
        return False

    # Success-Message?
    if "EnergyPlus Completed Successfully" in content:
        return True

    # Fallback: SQL-Datei vorhanden?
    sql_file = err_file.parent / "eplusout.sql"
    return sql_file.exists() and sql_file.stat().st_size > 1024
```

---

## 3. Aktuell genutzte Output-Variablen

**Aus sql_parser.py:**

### 3.1 Energie-Variablen (8)

| Variable | Einheit | Zweck | SQL-Aggregation |
|----------|---------|-------|-----------------|
| `Zone Air System Sensible Heating Energy` | J | Heizenergiebedarf | SUM |
| `Zone Air System Sensible Cooling Energy` | J | Kühlenergiebedarf | SUM |
| `Zone Lights Electric Energy` | J | Beleuchtungsenergie | SUM |
| `Zone Electric Equipment Electric Energy` | J | Geräteenergie | SUM |
| `Surface Average Face Conduction Heat Transfer Energy` | J | Transmissionsverluste | SUM (negative) |
| `Zone Infiltration Sensible Heat Gain Energy` | J | Infiltrationsverluste | SUM (negative) |
| `Zone Windows Total Heat Gain Energy` | J | Solare Gewinne | SUM |
| `Zone Lights Total Heating Energy` | J | Innere Lasten (Beleuchtung) | SUM |
| `Zone Electric Equipment Total Heating Energy` | J | Innere Lasten (Geräte) | SUM |
| `Zone People Total Heating Energy` | J | Innere Lasten (Personen) | SUM |

**Konversion:** `kWh = J / 3_600_000`

---

### 3.2 Leistungs-Variablen (2)

| Variable | Einheit | Zweck | SQL-Aggregation |
|----------|---------|-------|-----------------|
| `Zone Ideal Loads Zone Total Heating Rate` | W | Heizlast (Spitzenlast) | MAX |
| `Zone Ideal Loads Zone Total Cooling Rate` | W | Kühllast (Spitzenlast) | MAX |

**Konversion:** `kW = W / 1000`

---

### 3.3 Temperatur-Variablen (1)

| Variable | Einheit | Zweck | SQL-Aggregation |
|----------|---------|-------|-----------------|
| `Zone Mean Air Temperature` | °C | Raumtemperatur | AVG, MIN, MAX |

---

**TOTAL: 11 Variablen genutzt (~5% der verfügbaren!)**

---

## 4. Verfügbare aber NICHT genutzte Variablen

**EnergyPlus kann hunderte Variablen ausgeben!**

### 4.1 Oberflächentemperaturen

```
Surface Inside Face Temperature              [°C]
Surface Outside Face Temperature             [°C]
Surface Inside Face Solar Radiation Heat Gain Rate [W/m²]
Surface Window Heat Gain Rate                [W]
Surface Window Heat Loss Rate                [W]
Surface Average Face Conduction Heat Gain Rate [W]
```

**Nutzen:**
- Wärmebrücken-Identifikation
- Kondensationsrisiko
- Thermischer Komfort (operative Temperatur)

---

### 4.2 Lüftung & Luftqualität

```
Zone Ventilation Air Change Rate             [ach]
Zone Ventilation Mass Flow Rate              [kg/s]
Zone Air CO2 Concentration                   [ppm]
Zone Air Relative Humidity                   [%]
Zone Outdoor Air Drybulb Temperature         [°C]
Zone Mechanical Ventilation Mass Flow Rate   [kg/s]
```

**Nutzen:**
- Luftqualitäts-Überwachung
- Feuchte-Probleme erkennen
- Lüftungs-Optimierung

---

### 4.3 HVAC-System-Details

```
Zone Ideal Loads Supply Air Sensible Heating Energy [J]
Zone Ideal Loads Supply Air Sensible Cooling Energy [J]
Zone Ideal Loads Supply Air Temperature          [°C]
Zone Ideal Loads Supply Air Mass Flow Rate       [kg/s]
Zone Thermostat Heating Setpoint Temperature     [°C]
Zone Thermostat Cooling Setpoint Temperature     [°C]
Zone Thermostat Control Type                     [-]
```

**Nutzen:**
- HVAC-System-Analyse
- Setpoint-Validierung
- Luftmengen-Optimierung

---

### 4.4 Komfort-Metriken

```
Zone Thermal Comfort Fanger Model PMV            [-]
Zone Thermal Comfort Fanger Model PPD            [%]
Zone Thermal Comfort ASHRAE 55 Simple Model Summer Clothes Not Comfortable Time [hr]
Zone Thermal Comfort Pierce Model Standard Effective Temperature [°C]
Zone Mean Radiant Temperature                    [°C]
Zone Thermal Comfort Mean Radiant Temperature    [°C]
```

**Nutzen:**
- **PMV/PPD** - Objektive Komfort-Bewertung
- ASHRAE 55 Compliance
- Strahlungstemperatur für operative Temperatur

---

### 4.5 Solarstrahlung

```
Site Direct Solar Radiation Rate per Area        [W/m²]
Site Diffuse Solar Radiation Rate per Area       [W/m²]
Site Solar Altitude Angle                        [deg]
Site Solar Azimuth Angle                         [deg]
Surface Outside Face Incident Solar Radiation Rate per Area [W/m²]
Zone Windows Total Transmitted Solar Radiation Energy [J]
```

**Nutzen:**
- Verschattungs-Analyse
- Fenster-Optimierung
- Solare Gewinne pro Orientierung

---

### 4.6 Detaillierte Energieflüsse

```
Zone Windows Total Transmitted Solar Radiation Energy [J]
Zone Opaque Surface Inside Face Conduction          [W]
Zone Ventilation Sensible Heat Loss Energy          [J]
Zone Infiltration Sensible Heat Loss Energy         [J]
Zone Air Heat Balance Internal Convective Heat Gain Rate [W]
Zone Air Heat Balance Surface Convection Rate       [W]
```

**Nutzen:**
- Detaillierte Wärmebilanz
- Optimierungspotential identifizieren

---

### 4.7 Zonale Luft-Details

```
Zone Air Temperature                             [°C]
Zone Air Humidity Ratio                          [kgWater/kgDryAir]
Zone Air Pressure                                [Pa]
Zone Air Density                                 [kg/m³]
Zone Air Heat Capacity Multiplier                [-]
Zone Air Heat Balance System Air Transfer Rate   [W]
```

**Nutzen:**
- Druckdifferenzen (Stack-Effekt)
- Feuchte-Transport
- Inter-Zone Air Flow

---

### 4.8 Tabular Reports (TabularData-Tabelle)

**Vorgefertigte Reports in SQL verfügbar!**

```sql
SELECT * FROM TabularData
WHERE ReportName = 'AnnualBuildingUtilityPerformanceSummary';
```

**Reports:**
- Annual Building Utility Performance Summary
- HVAC Sizing Summary
- Component Sizing Summary
- Envelope Summary
- End Use Energy Consumption
- Peak Demand (monatlich)
- Sensible Heat Gain Summary
- Adaptive Comfort Summary

**Nutzen:**
- **Kein Parsing nötig!** - Bereits aggregiert
- Monatliche Spitzenlasten
- End-Use Breakdown (Heizung/Kühlung/Beleuchtung/etc.)
- HVAC Sizing (Auslegungsgrößen)

---

## 5. Ungenutztes Potential

### 5.1 Kritische Lücken

❌ **Keine zonale Auswertung**
- 5-Zonen-Modell → Alle Zonen aggregiert
- Keine Nord/Ost/Süd/West/Kern-Unterscheidung
- **Lösung:** `WHERE KeyValue = 'Perimeter_North_F1'` in SQL

❌ **Keine Komfort-Metriken**
- PMV/PPD nicht genutzt
- **Lösung:** `Zone Thermal Comfort Fanger Model PMV` aktivieren

❌ **Keine Luftqualität**
- CO₂-Konzentration nicht überwacht
- **Lösung:** `Zone Air CO2 Concentration` aktivieren

❌ **Keine Oberflächentemperaturen**
- Wärmebrücken nicht erkennbar
- **Lösung:** `Surface Inside Face Temperature` aktivieren

❌ **Keine Tabular Reports**
- Vorgefertigte Reports nicht genutzt
- **Lösung:** `TabularData`-Tabelle parsen

---

### 5.2 Empfehlungen

#### Kurzfristig (Quick Wins)

**1. Tabular Reports nutzen:**

```python
def get_annual_summary(sql_file: Path) -> pd.DataFrame:
    conn = sqlite3.connect(sql_file)
    query = """
    SELECT ReportName, TableName, RowName, ColumnName, Value, Units
    FROM TabularData
    WHERE ReportName = 'AnnualBuildingUtilityPerformanceSummary'
    """
    return pd.read_sql_query(query, conn)
```

**2. Zonale Auswertung:**

```python
def get_zone_comparison(sql_file: Path) -> pd.DataFrame:
    conn = sqlite3.connect(sql_file)
    query = """
    SELECT
        rdd.KeyValue AS Zone,
        SUM(CASE WHEN rdd.Name = 'Zone Air System Sensible Heating Energy'
            THEN rd.Value ELSE 0 END) / 3600000.0 AS Heating_kWh,
        AVG(CASE WHEN rdd.Name = 'Zone Mean Air Temperature'
            THEN rd.Value ELSE NULL END) AS Avg_Temp_C
    FROM ReportData rd
    JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
    GROUP BY rdd.KeyValue
    """
    return pd.read_sql_query(query, conn)
```

**3. Output-Variablen erweitern:**

```python
# In sim_settings
output_variables_extended = [
    # Aktuell (11)
    "Zone Mean Air Temperature",
    "Zone Air System Sensible Heating Energy",
    # ...

    # NEU: Komfort
    "Zone Thermal Comfort Fanger Model PMV",
    "Zone Thermal Comfort Fanger Model PPD",
    "Zone Air Relative Humidity",

    # NEU: Luftqualität
    "Zone Air CO2 Concentration",
    "Zone Ventilation Air Change Rate",

    # NEU: Oberflächentemperaturen
    "Surface Inside Face Temperature",
    "Surface Outside Face Temperature",

    # NEU: Solar
    "Surface Outside Face Incident Solar Radiation Rate per Area",
]
```

---

#### Mittelfristig

**4. Heatmaps erstellen:**

```python
def create_zone_temperature_heatmap(sql_file: Path, day: int):
    """
    Zeigt Temperatur-Verteilung über Zonen für einen Tag.
    Nord/Ost/Süd/West/Kern als Heatmap.
    """
    # SQL: Get hourly temps for all zones for specific day
    # Plotly Heatmap: X=Hour, Y=Zone, Color=Temperature
```

**5. PMV/PPD-Analyse:**

```python
def analyze_thermal_comfort(sql_file: Path):
    """
    Berechnet % der Zeit mit gutem Komfort (PMV -0.5 bis +0.5).
    ASHRAE 55 Compliance.
    """
```

**6. Wärmebrücken-Identifikation:**

```python
def find_thermal_bridges(sql_file: Path):
    """
    Findet Surfaces mit auffälligen Temperatur-Gradienten.
    Outside vs. Inside Face Temperature.
    """
```

---

#### Langfristig

**7. Machine Learning für Optimierung:**

```python
# Alle verfügbaren Variablen nutzen für:
# - Anomalie-Erkennung
# - Vorhersage-Modelle
# - Automatische Optimierung
```

**8. Real-Time Monitoring Dashboard:**

```python
# Streamlit Live-Update während Simulation
# - Progress bar
# - Live-Temperatur-Kurven
# - Live-Energie-Balken
```

---

## 6. Zusammenfassung

### Aktueller Stand

| Kategorie | Verfügbar | Genutzt | % |
|-----------|-----------|---------|---|
| Output-Variablen | 200+ | 11 | **5%** |
| Tabellen in SQL | 36 | 3 | **8%** |
| Komfort-Metriken | 10+ | 0 | **0%** |
| Zonale Daten | Alle Zonen | Aggregiert | **~ 0%** |

### Größtes ungenutztes Potential

1. **Tabular Reports** - Vorgefertigte Auswertungen (KEIN Parsing nötig!)
2. **Zonale Unterschiede** - Nord vs. Süd Energiebedarf
3. **PMV/PPD** - Objektive Komfort-Bewertung
4. **Oberflächentemperaturen** - Wärmebrücken & Kondensation
5. **Luftqualität** - CO₂ & Feuchte

### Empfohlene Nächste Schritte

**Priorität 1 (Quick Wins):**
1. Tabular Reports parsen → Instant zusätzliche Metriken
2. Zonale Auswertung aktivieren → Nord/Süd-Vergleich
3. PMV/PPD aktivieren → Objektiver Komfort

**Priorität 2 (Mittelfristig):**
4. Oberflächentemperaturen → Wärmebrücken
5. Luftqualität → CO₂ & Feuchte
6. Heatmaps → Visuelle Zonen-Analyse

**Priorität 3 (Langfristig):**
7. Alle 200+ Variablen → Machine Learning
8. Real-Time Monitoring → Live-Dashboard

---

**Aktuell genutztes Daten-Potential: ~5%**

**Verfügbares aber ungenutztes Potential: ~95%!**

---

**Letzte Änderung:** 2025-11-14
**Changelog:** Initial creation - Simulation & verfügbare Daten vollständig dokumentiert
