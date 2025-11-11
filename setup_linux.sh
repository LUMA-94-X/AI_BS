#!/bin/bash
# AI_BS Setup für Linux/macOS

set -e  # Exit on error

echo ""
echo "========================================"
echo "  Setup für AI_BS auf Linux/macOS"
echo "========================================"
echo ""

# Prüfe ob Python installiert ist
if ! command -v python3 &> /dev/null; then
    echo "[FEHLER] Python 3 ist nicht installiert!"
    echo ""
    echo "Bitte installiere Python 3.10 oder neuer:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    exit 1
fi

echo "[1/4] Python gefunden:"
python3 --version
echo ""

# Lösche altes venv falls vorhanden
if [ -d "venv" ]; then
    echo "[2/4] Lösche altes Virtual Environment..."
    rm -rf venv
fi

# Erstelle neues venv
echo "[3/4] Erstelle Virtual Environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[FEHLER] Konnte Virtual Environment nicht erstellen!"
    exit 1
fi

# Installiere Dependencies
echo "[4/4] Installiere Abhängigkeiten..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install eppy pandas pydantic numpy pyyaml tqdm plotly

echo ""
echo "========================================"
echo "  Setup erfolgreich abgeschlossen!"
echo "========================================"
echo ""
echo "Nächste Schritte:"
echo "  1. Aktiviere das Environment: source venv/bin/activate"
echo "  2. Installiere EnergyPlus: https://energyplus.net"
echo "  3. Starte Beispiel: python beispiele/einfache_simulation.py"
echo ""
echo "Optional - Web-UI (benötigt Streamlit):"
echo "  pip install streamlit"
echo "  python scripts/ui_starten.py"
echo ""
