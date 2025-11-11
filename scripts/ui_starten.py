"""Starter-Script für die Web-UI."""

import subprocess
import sys
from pathlib import Path

# Projekt-Root-Verzeichnis zum Python-Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

if __name__ == "__main__":
    print("🚀 Starte Web-UI...")
    print(f"📂 Arbeitsverzeichnis: {projekt_root}")

    # Starte Streamlit
    streamlit_app = projekt_root / "features" / "web_ui" / "Start.py"

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(streamlit_app),
        "--server.headless", "false"
    ])
