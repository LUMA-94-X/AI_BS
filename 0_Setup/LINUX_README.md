# 🐧 Linux/macOS Installation

Spezielle Anweisungen für Linux und macOS Benutzer.

## ✅ Getestet auf:
- Ubuntu 22.04 (WSL2)
- Python 3.10.12

## 🚀 Schnellstart

```bash
# Setup-Script ausführen
./setup_linux.sh

# Oder manuell:
python3 -m venv venv
source venv/bin/activate
pip install eppy pandas pydantic numpy pyyaml tqdm plotly
```

## 📦 EnergyPlus Installation

### Ubuntu/Debian
```bash
# Download von https://energyplus.net
# Oder:
wget https://github.com/NREL/EnergyPlus/releases/download/v23.2.0/EnergyPlus-23.2.0-7636e6b3e9-Linux-Ubuntu22.04-x86_64.tar.gz

# Entpacken
tar -xzf EnergyPlus-*.tar.gz

# Installieren
sudo mv EnergyPlus-23-2-0-7636e6b3e9-Linux-Ubuntu22.04-x86_64 /usr/local/EnergyPlus-23-2-0

# Konfigurieren
# Bearbeite config/default_config.yaml:
energyplus:
  installation_path: "/usr/local/EnergyPlus-23-2-0"
```

### macOS
```bash
# Download von https://energyplus.net
# Oder mit Homebrew:
brew install energyplus

# Konfigurieren
# Bearbeite config/default_config.yaml:
energyplus:
  installation_path: "/Applications/EnergyPlus-23-2-0"
```

## 🧪 Testergebnisse

**✅ Alle Imports funktionieren:**
- geometrie.box_generator
- hvac.ideal_loads
- simulation.runner
- auswertung.kpi_rechner
- core.config

**✅ Python-Kompatibilität:** 3.10+

**⚠️ Hinweise:**
- Config lädt Windows-Pfad aus `config/default_config.yaml`
- EnergyPlus muss separat installiert werden
- Config-Pfad anpassen oder `installation_path: ""` für Auto-Detection

## 🔧 Konfiguration anpassen

```bash
# Option 1: Config-Datei bearbeiten
nano config/default_config.yaml

# Ändere:
energyplus:
  installation_path: "/usr/local/EnergyPlus-23-2-0"  # Dein Pfad
  version: "23.2"

# Option 2: Per Python
python3 -c "
from core.config import get_config, set_config
config = get_config()
config.energyplus.installation_path = '/usr/local/EnergyPlus-23-2-0'
config.to_yaml('config/default_config.yaml')
"
```

## 📝 Simulation ausführen

```bash
# Aktiviere venv
source venv/bin/activate

# Beispiel-Simulation
python beispiele/einfache_simulation.py

# Dashboard im Browser öffnen
xdg-open output/einfache_simulation/dashboard.html
```

## 🌐 Web-UI (Optional)

```bash
# Streamlit installieren
pip install streamlit

# UI starten
python scripts/ui_starten.py

# Öffnet http://localhost:8501
```

## ❓ Troubleshooting

### EnergyPlus nicht gefunden
```bash
# Prüfe Installation
ls -la /usr/local/EnergyPlus-*/

# Teste Config
python3 -c "
from core.config import get_config
config = get_config()
print(config.energyplus.get_executable_path())
"
```

### Import-Fehler
```bash
# Prüfe, ob venv aktiviert ist
which python  # Sollte venv/bin/python zeigen

# Reinstalliere Dependencies
pip install --force-reinstall eppy pandas pydantic numpy pyyaml tqdm plotly
```

### Permissions-Fehler
```bash
# Script ausführbar machen
chmod +x setup_linux.sh

# Oder ohne Script:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🐛 Bekannte Probleme

1. **WSL-Pfade:** Windows-Pfade (C:/) funktionieren nicht in WSL
   - Lösung: Linux-Pfade verwenden (`/usr/local/...`)

2. **Auto-Detection:** Funktioniert nur für Standard-Pfade
   - Lösung: `installation_path` in Config setzen

## 📞 Support

Bei Problemen:
- Prüfe Logs: `cat energyplus_automation.log`
- Prüfe EnergyPlus-Fehler: `cat output/*/eplusout.err`
- Erstelle Issue: https://github.com/LUMA-94-X/AI_BS/issues

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
