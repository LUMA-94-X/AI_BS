"""Hauptseite der EnergyPlus Gebäudesimulation Web-App."""

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Gebäudesimulation",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Haupt-Titel
st.title("🏢 EnergyPlus Gebäudesimulation")
st.markdown("---")

# Willkommensnachricht
st.markdown("""
## Willkommen!

Diese Anwendung ermöglicht es Ihnen, Gebäudeenergiesimulationen durchzuführen und auszuwerten.

### 📋 So funktioniert's:

1. **🏗️ Geometrie** - Definieren Sie die Gebäudegeometrie (Maße, Stockwerke, Fenster)
2. **❄️ HVAC** - Wählen Sie das Heizungs-/Kühlsystem
3. **▶️ Simulation** - Starten Sie die Simulation
4. **📊 Ergebnisse** - Analysieren Sie die Ergebnisse mit interaktiven Diagrammen

### 🎯 Features:

- ✅ Einfache Eingabe über Schieberegler
- ✅ 3D-Visualisierung des Gebäudes
- ✅ Automatische Berechnung von Kennzahlen
- ✅ Energieeffizienzklassen nach EnEV
- ✅ Interaktive Diagramme und Auswertungen
- ✅ Export der Ergebnisse

### 🚀 Jetzt starten!

Verwenden Sie das **Menü links**, um zwischen den Seiten zu navigieren.

""")

# Spalten für Info-Boxen
col1, col2, col3 = st.columns(3)

with col1:
    st.info("""
    **⚡ Schnell**

    Simulation in wenigen Sekunden
    """)

with col2:
    st.success("""
    **📊 Detailliert**

    Umfassende Auswertungen und KPIs
    """)

with col3:
    st.warning("""
    **🎓 Einfach**

    Keine EnergyPlus-Kenntnisse nötig
    """)

st.markdown("---")

# Systeminfo
with st.expander("ℹ️ Systeminfos"):
    try:
        from core.config import get_config
        config = get_config()
        ep_exe = config.energyplus.get_executable_path()

        if ep_exe.exists():
            st.success(f"✅ EnergyPlus gefunden: `{ep_exe}`")
        else:
            st.error(f"❌ EnergyPlus nicht gefunden: `{ep_exe}`")

    except Exception as e:
        st.error(f"Fehler beim Laden der Konfiguration: {e}")

# Footer
st.markdown("---")
st.caption("🤖 Erstellt mit Claude Code | EnergyPlus Building Simulation Framework")
