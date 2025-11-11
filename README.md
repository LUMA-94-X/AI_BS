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
- EnergyPlus 23.2 ([Download](https://energyplus.net))

### Setup

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Konfiguration prüfen
python -c "from core.config import get_config; print(get_config().energyplus.get_executable_path())"
```

## 🚀 Schnellstart

### Web-Interface starten

```bash
python scripts/ui_starten.py
```

### Simulation per Python

```bash
python beispiele/einfache_simulation.py
```

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
