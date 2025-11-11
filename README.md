# 🏢 EnergyPlus Gebäudesimulations-Framework

Ein Python-Framework für einfache und automatisierte Gebäudeenergiesimulationen mit EnergyPlus.

## ✨ Features

- 🏗️ **Automatische Gebäudemodellerstellung** - Keine manuelle IDF-Bearbeitung nötig
- ❄️ **HVAC-Systeme** - Ideal Loads und weitere Systeme
- 🚀 **Batch-Simulationen** - Parallel mehrere Varianten simulieren
- 📊 **Automatische Auswertung** - KPIs, Energiekennzahlen, Effizienzklassen
- 📈 **Interaktive Visualisierungen** - Plotly-Diagramme für Ergebnisse
- 🌐 **Web-Interface** - Streamlit-App für einfache Bedienung
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

### Simulation per Python (Empfohlen)

```bash
# Windows
python beispiele\einfache_simulation.py

# Linux/macOS
python beispiele/einfache_simulation.py
```

Das Beispiel erstellt automatisch:
- Ein Gebäudemodell (20m × 12m, 2 Stockwerke)
- HVAC-System (Ideal Loads)
- Simulation und Auswertung
- Interaktives Dashboard (`output/einfache_simulation/dashboard.html`)

### Web-Interface (In Entwicklung)

```bash
# Erfordert Streamlit + pyarrow (C++ Compiler nötig)
pip install streamlit
python scripts/ui_starten.py
```

**Status:** Nur Startseite verfügbar, weitere Seiten in Entwicklung.

## 📁 Projekt-Struktur

```
AI_BS/
├── features/              # Feature-Module
│   ├── geometrie/        # Gebäudegeometrie
│   ├── hvac/             # HVAC-Systeme
│   ├── simulation/       # Simulationsausführung
│   ├── auswertung/       # Ergebnisanalyse (NEU!)
│   └── web_ui/           # Web-Interface
├── core/                  # Kern-Funktionalität
├── beispiele/            # Beispiel-Scripts
├── scripts/              # Utility-Scripts
└── tests/                # Tests
```

## 📖 Dokumentation

- [ERSTE_SCHRITTE.md](ERSTE_SCHRITTE.md) - Tutorial

## 📄 Lizenz

Siehe [LICENSE](LICENSE) Datei.

---

🤖 Generiert mit [Claude Code](https://claude.com/claude-code)
