# 🚀 Erste Schritte

Eine Schritt-für-Schritt-Anleitung für deine erste Gebäudesimulation.

## ✅ Voraussetzungen prüfen

### 1. Python-Version

```bash
python --version  # Sollte >= 3.10 sein
```

### 2. EnergyPlus Installation

```bash
# Windows
dir "C:\EnergyPlusV23-2-0\energyplus.exe"

# Linux/Mac
ls /usr/local/EnergyPlus-23-2-0/energyplus
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

## 🎯 Methode 1: Web-Interface (Empfohlen für Einsteiger)

### Schritt 1: Web-App starten

```bash
python scripts/ui_starten.py
```

Die App öffnet sich automatisch im Browser unter `http://localhost:8501`

### Schritt 2: Parameter einstellen

Im Browser:
1. Navigiere zu "Geometrie"
2. Stelle die Parameter ein:
   - Länge: 20m
   - Breite: 12m
   - Höhe: 6m
   - Stockwerke: 2
   - Fensterflächenanteil: 0.3 (30%)

### Schritt 3: HVAC-System wählen

1. Navigiere zu "HVAC"
2. Wähle "Ideal Loads" (empfohlen für erste Versuche)

### Schritt 4: Simulation starten

1. Navigiere zu "Simulation"
2. Klicke auf "Simulation starten"
3. Warte ~10 Sekunden

### Schritt 5: Ergebnisse ansehen

1. Navigiere zu "Ergebnisse"
2. Erkunde die interaktiven Diagramme:
   - Energiebilanz
   - Monatliche Übersicht
   - Temperaturverlauf
   - KPIs und Effizienzklasse

## 💻 Methode 2: Python-Script

### Schritt 1: Beispiel-Script ausführen

```bash
python beispiele/einfache_simulation.py
```

Das Script:
- Erstellt ein Gebäude (20m x 12m, 2 Stockwerke)
- Fügt HVAC-System hinzu
- Führt Simulation aus
- Berechnet Kennzahlen
- Erstellt Dashboard

### Schritt 2: Ergebnisse öffnen

```bash
# Dashboard im Browser öffnen
firefox output/einfache_simulation/dashboard.html
# oder
open output/einfache_simulation/dashboard.html  # macOS
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

## 🐛 Problemlösung

### EnergyPlus nicht gefunden

```python
# Konfiguration manuell setzen
from core.config import get_config, set_config

config = get_config()
config.energyplus.installation_path = "C:/EnergyPlusV23-2-0"  # Dein Pfad
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
