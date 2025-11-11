# 🚀 Quick Start - EnergyPlus Automation

**Schnellstart-Anleitung für die Verwendung mit VS Code**

---

## ✅ Voraussetzungen

1. **Python 3.11+** installiert
2. **EnergyPlus 23.2.0** installiert
3. **VS Code** installiert
4. **Git** (optional)

---

## 📦 Ersteinrichtung

### 1. Virtual Environment aktivieren

```bash
# In VS Code Terminal (Ctrl+`)
source venv/bin/activate  # Linux/Mac
# ODER
.\venv\Scripts\activate   # Windows
```

### 2. Empfohlene VS Code Extensions installieren

VS Code wird automatisch vorschlagen, die empfohlenen Extensions zu installieren.
Oder drücke: `Ctrl+Shift+P` → "Extensions: Show Recommended Extensions"

---

## 🏃 Simulation ausführen

### Methode 1: Mit VS Code Run & Debug (F5)

1. **Öffne Run & Debug Panel**: `Ctrl+Shift+D`
2. **Wähle eine Konfiguration** aus der Dropdown-Liste:
   - 🏗️ **Simple Box Simulation** - Einfaches Gebäude ohne HVAC
   - 🔥 **Building with HVAC Template** - Gebäude mit HVAC (empfohlen!)
   - 📊 **Batch Simulation** - Mehrere Parametervariationen
   - 🧪 **Test: HVAC Single Floor** - Validierungstest

3. **Drücke F5** oder klicke auf den grünen Play-Button

### Methode 2: Mit Tasks (Ctrl+Shift+B)

1. **Drücke `Ctrl+Shift+B`** (Build Task)
2. Wähle:
   - 🔥 **Run HVAC Template Example** (Standard)
   - 🏗️ **Run Simple Box Example**
   - 🧪 **Run All Tests**
   - 🧹 **Clean Output Directory**
   - 📂 **Open Latest Output**

### Methode 3: Im Terminal

```bash
# Einfaches Gebäude
python examples/01_simple_box_simulation.py

# Mit HVAC (empfohlen!)
python examples/03_building_with_hvac_template.py

# Batch-Simulation
python examples/02_batch_simulation.py
```

---

## 📁 Projektstruktur

```
AI_BS/
├── .vscode/              # VS Code Konfiguration
│   ├── launch.json       # Debug/Run Konfigurationen
│   ├── tasks.json        # Build Tasks
│   ├── settings.json     # Python Settings
│   └── extensions.json   # Empfohlene Extensions
│
├── src/                  # Haupt-Code
│   ├── geometry/         # Geometrie-Generierung
│   │   └── simple_box.py # Box-Gebäude-Generator
│   ├── hvac/             # HVAC-Templates
│   │   └── template_manager.py
│   ├── simulation/       # Simulation Runner
│   │   └── runner.py
│   └── utils/            # Utilities
│       └── config.py
│
├── examples/             # Beispiele (STARTE HIER!)
│   ├── 01_simple_box_simulation.py
│   ├── 02_batch_simulation.py
│   └── 03_building_with_hvac_template.py  ← EMPFOHLEN
│
├── tests/                # Tests
│   ├── test_hvac_single_floor.py
│   ├── test_simple_box.py
│   └── test_config.py
│
├── output/               # Simulationsergebnisse
│   ├── building_with_hvac/
│   └── test_hvac_single/
│
├── data/
│   └── weather/          # Wetterdateien (.epw)
│
└── docs/                 # Dokumentation
    ├── GETTING_STARTED.md
    ├── ARCHITECTURE.md
    └── HVAC_TEMPLATE_SYSTEM.md
```

---

## 🎯 Empfohlener Workflow

### Für Einsteiger: Start mit Beispiel 3

```bash
# 1. Öffne VS Code
code .

# 2. Öffne examples/03_building_with_hvac_template.py

# 3. Drücke F5 (Run & Debug) und wähle:
#    "🔥 Building with HVAC Template"

# 4. Warte ~6 Sekunden

# 5. Öffne Ergebnisse:
explorer.exe output/building_with_hvac/simulation/
```

### Für eigene Simulationen

**Schritt 1: Python-Datei erstellen**

```python
# my_simulation.py
from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.hvac.template_manager import HVACTemplateManager
from src.simulation.runner import EnergyPlusRunner
from src.utils.config import get_config
from pathlib import Path

# 1. Geometrie definieren
geometry = BuildingGeometry(
    length=15.0,           # Länge in Metern
    width=12.0,            # Breite in Metern
    height=9.0,            # Gesamthöhe
    num_floors=3,          # Anzahl Geschosse
    window_wall_ratio=0.35 # 35% Fensteranteil
)

# 2. IDF erstellen
config = get_config()
generator = SimpleBoxGenerator(config)
idf = generator.create_model(geometry)

# 3. HVAC hinzufügen
hvac_manager = HVACTemplateManager()
idf = hvac_manager.apply_template_simple(idf, "ideal_loads")

# 4. Speichern
output_dir = Path("output/my_simulation")
output_dir.mkdir(parents=True, exist_ok=True)
idf_path = output_dir / "building.idf"
idf.saveas(str(idf_path), encoding='utf-8')

# 5. Simulieren
runner = EnergyPlusRunner(config)
result = runner.run_simulation(
    idf_path=idf_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=output_dir / "simulation"
)

# 6. Ergebnisse prüfen
if result.success:
    print(f"✅ Erfolgreich! Ergebnisse: {result.output_dir}")
else:
    print(f"❌ Fehler: {result.error_message}")
```

**Schritt 2: In VS Code ausführen**

1. Öffne `my_simulation.py` in VS Code
2. Drücke `F5`
3. Wähle "🐍 Current Python File"

**ODER direkt im Terminal:**

```bash
python my_simulation.py
```

---

## 🔧 Debugging

### Breakpoints setzen

1. Klicke links neben die Zeilennummer (roter Punkt erscheint)
2. Drücke `F5` zum Debuggen
3. Code stoppt am Breakpoint
4. Verwende Debug-Controls:
   - `F10` - Nächste Zeile
   - `F11` - In Funktion springen
   - `Shift+F11` - Aus Funktion springen
   - `F5` - Weiter ausführen

### Variablen inspizieren

- **Watch Panel**: Füge Variablennamen hinzu
- **Variables Panel**: Zeigt alle lokalen/globalen Variablen
- **Debug Console**: Führe Python-Code aus während Debugging

---

## 📊 Ergebnisse anschauen

### HTML-Reports (empfohlen)

```bash
# Windows
explorer.exe output/building_with_hvac/simulation/buildingTable.htm

# Linux
xdg-open output/building_with_hvac/simulation/buildingTable.htm
```

### CSV-Dateien

```python
import pandas as pd

# Zone-Sizing Ergebnisse
df = pd.read_csv("output/building_with_hvac/simulation/buildingzsz.csv")
print(df.head())
```

### SQL-Datenbank (für fortgeschrittene Analysen)

```python
import sqlite3

conn = sqlite3.connect("output/building_with_hvac/simulation/buildingout.sql")
# SQL-Abfragen...
```

---

## ⚡ Shortcuts (VS Code)

| Shortcut | Aktion |
|----------|--------|
| `F5` | Run/Debug |
| `Ctrl+Shift+B` | Build Task |
| `Ctrl+Shift+D` | Run & Debug Panel öffnen |
| `Ctrl+\`` | Terminal öffnen/schließen |
| `Ctrl+Shift+P` | Command Palette |
| `Ctrl+P` | Datei schnell öffnen |
| `F9` | Breakpoint setzen/entfernen |

---

## 🆘 Hilfe

### Simulation schlägt fehl?

1. **Prüfe Error-Log**:
   ```bash
   cat output/[DEIN_OUTPUT]/simulation/*out.err | grep -E "(Fatal|Severe)" -A 3
   ```

2. **Häufige Probleme**:
   - **Keine Wetterdatei**: Lade eine .epw Datei herunter von https://energyplus.net/weather
   - **EnergyPlus nicht gefunden**: Setze Pfad in `src/utils/config.py`
   - **IDD-Fehler**: Stelle sicher, dass EnergyPlus 23.2.0 installiert ist

3. **Siehe Dokumentation**:
   - `HVAC_SYSTEM_FIXES.md` - HVAC-Fehler
   - `HVAC_TEMPLATE_SYSTEM.md` - HVAC-System Übersicht
   - `docs/GETTING_STARTED.md` - Detaillierte Anleitung

---

## 🎓 Nächste Schritte

1. **Führe die Beispiele aus** (`examples/`)
2. **Lies die Dokumentation** (`docs/`)
3. **Erstelle eigene Simulationen**
4. **Experimentiere mit Parametern**:
   - Verschiedene Geometrien
   - Verschiedene WWR (Window-Wall-Ratio)
   - Verschiedene Materialien
   - Verschiedene HVAC-Systeme

---

## 📚 Weitere Ressourcen

- **EnergyPlus Dokumentation**: https://energyplus.net/documentation
- **eppy Dokumentation**: https://eppy.readthedocs.io/
- **Wetterdateien**: https://energyplus.net/weather
- **Projekt-Dokumentation**: `docs/` Verzeichnis

---

**Happy Simulating! 🚀**
