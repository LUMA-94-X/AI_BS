# 🏢 EnergyPlus Gebäudesimulations-Framework

Ein Python-Framework für einfache und automatisierte Gebäudeenergiesimulationen mit EnergyPlus.

## ✨ Features

- 🏗️ **Automatische Gebäudemodellerstellung** - Keine manuelle IDF-Bearbeitung nötig
- 📋 **5-Zone-Modell aus Energieausweis** - Automatische Geometrie-Rekonstruktion (NEU!)
- ❄️ **HVAC-Systeme** - Ideal Loads und weitere Systeme
- 🚀 **Batch-Simulationen** - Parallel mehrere Varianten simulieren
- 📊 **Automatische Auswertung** - KPIs, Energiekennzahlen, Effizienzklassen
- 📈 **Interaktive Visualisierungen** - Plotly-Diagramme für Ergebnisse
- 🌐 **Web-Interface** - Streamlit-App mit Energieausweis-Integration
- 🎯 **Feature-basierte Architektur** - Klar strukturiert und erweiterbar

## 📦 Installation

### Voraussetzungen

- Python 3.10 oder neuer
- EnergyPlus 23.2 oder neuer (getestet mit 25.1) - [Download](https://github.com/NREL/EnergyPlus/releases)

### Windows Setup (Empfohlen)

**Schnellstart:**
```powershell
# Doppelklick auf:
SCHNELLSTART_WINDOWS.bat
```

**Manuelles Setup:**
```powershell
# 1. Virtual Environment erstellen und aktivieren
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Abhängigkeiten installieren (ohne Streamlit UI)
pip install eppy pandas pydantic numpy pyyaml tqdm plotly

# 3. EnergyPlus-Pfad prüfen
python -c "from core.config import get_config; print(get_config().energyplus.get_executable_path())"
```

### Linux/macOS Setup

```bash
# 1. Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# 2. Abhängigkeiten installieren
pip install eppy pandas pydantic numpy pyyaml tqdm plotly

# 3. Konfiguration prüfen
python -c "from core.config import get_config; print(get_config().energyplus.get_executable_path())"
```

**Hinweis:** Die Web-UI (Streamlit) benötigt zusätzlich Visual Studio Build Tools (Windows) oder einen C++ Compiler, da sie pyarrow voraussetzt.

## 🚀 Schnellstart

### Methode 1: Python-Script (Empfohlen)

**Einfache Simulation:**
```bash
# Windows
python beispiele\einfache_simulation.py

# Linux/macOS
python beispiele/einfache_simulation.py
```

Erstellt automatisch:
- Gebäudemodell (20m × 12m, 2 Stockwerke)
- HVAC-System (Ideal Loads)
- Simulation und Auswertung
- Interaktives Dashboard (`output/einfache_simulation/dashboard.html`)

**5-Zone-Modell aus Energieausweis (NEU!):**
```bash
python beispiele/energieausweis_5zone_test.py
```

Erstellt:
- Automatische Geometrie-Rekonstruktion aus Energieausweis-Daten
- 5-Zonen-Layout (Perimeter Nord/Ost/Süd/West + Kern)
- Orientierungsspezifische Fensterverteilung
- Multi-Floor-Support

### Methode 2: Web-Interface

```bash
# Erfordert Streamlit + pyarrow (C++ Compiler nötig)
pip install streamlit
python scripts/ui_starten.py
```

**Verfügbare Seiten:**
- 🏗️ **Geometrie** - Manuelle Eingabe von Gebäudeparametern
- 📋 **Energieausweis** - 5-Zone-Modell aus Energieausweis-Daten (NEU!)
- ❄️ **HVAC** - Heiz-/Kühlsystem-Konfiguration
- ▶️ **Simulation** - EnergyPlus-Simulation ausführen
- 📊 **Ergebnisse** - KPI-Auswertung und Visualisierung

## 📁 Projekt-Struktur

```
AI_BS/
├── features/              # Feature-Module
│   ├── geometrie/        # Gebäudegeometrie
│   │   ├── generators/   # SimpleBox + 5-Zone-Generator (NEU!)
│   │   ├── models/       # Energieausweis-Input-Modelle (NEU!)
│   │   └── utils/        # Geometrie-Solver, Perimeter-Calc (NEU!)
│   ├── hvac/             # HVAC-Systeme
│   ├── simulation/       # Simulationsausführung
│   ├── auswertung/       # Ergebnisanalyse
│   └── web_ui/           # Web-Interface
│       └── pages/        # Streamlit-Pages inkl. Energieausweis (NEU!)
├── core/                  # Kern-Funktionalität
├── beispiele/            # Beispiel-Scripts
├── scripts/              # Utility-Scripts
└── tests/                # Tests
```

## 🆕 5-Zone-Modell aus Energieausweis

### Konzept

Das neue 5-Zone-Feature ermöglicht die automatische Erstellung detaillierter Gebäudemodelle basierend auf Energieausweis-Daten:

**Eingabe (aus Energieausweis):**
- Nettogrundfläche, U-Werte (Wand/Dach/Boden/Fenster)
- Optional: Hüllflächen (Wand/Dach/Boden)
- Fensterverteilung (gesamt oder pro Orientierung)
- Geschosszahl, Gebäudetyp

**Automatische Prozesse:**
1. **Geometrie-Rekonstruktion** - Berechnet L/W/H aus Flächenangaben
2. **5-Zonen-Layout** - Perimeter N/E/S/W + Kern pro Stockwerk
3. **Adaptive Perimeter-Tiefe** - Abhängig vom Fensterflächenanteil (3-6m)
4. **Orientierungsspezifische Fenster** - Exakte Verteilung auf Himmelsrichtungen

**Ausgabe:**
- Vollständiges EnergyPlus IDF mit 5 Zonen × n Stockwerke
- ~60-90 Surfaces (Wände, Fenster, Decken, Böden)
- Inter-Zone-Verbindungen korrekt modelliert

### Python-Beispiel

```python
from features.geometrie.models.energieausweis_input import EnergieausweisInput, FensterData
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator

# Energieausweis-Daten definieren
ea_data = EnergieausweisInput(
    nettoflaeche_m2=150.0,
    wandflaeche_m2=240.0,
    dachflaeche_m2=80.0,
    anzahl_geschosse=2,
    u_wert_wand=0.28,
    u_wert_dach=0.20,
    u_wert_fenster=1.30,
    fenster=FensterData(
        nord_m2=8.0,
        sued_m2=20.0,
        ost_m2=12.0,
        west_m2=10.0
    )
)

# 5-Zone-IDF generieren
generator = FiveZoneGenerator()
idf = generator.create_from_energieausweis(
    ea_data=ea_data,
    output_path="gebaeude_5zone.idf"
)
```

### Web-UI Workflow

1. Öffne `http://localhost:8501`
2. Navigiere zu **📋 Energieausweis** (Seitenleiste)
3. Gib Energieausweis-Daten ein
4. Klick "Geometrie berechnen" → Vorschau
5. Klick "5-Zone-IDF erstellen" → IDF generiert
6. Weiter zu **HVAC** und **Simulation**

## 📖 Dokumentation

- [ERSTE_SCHRITTE.md](ERSTE_SCHRITTE.md) - Tutorial
- [GitHub Issues](https://github.com/LUMA-94-X/AI_BS/issues) - Features & Roadmap

## 📄 Lizenz

Siehe [LICENSE](LICENSE) Datei.

---

🤖 Generiert mit [Claude Code](https://claude.com/claude-code)
