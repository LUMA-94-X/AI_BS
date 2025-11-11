"""HVAC-Seite für Heizungs-/Kühlsystem-Konfiguration."""

import streamlit as st
import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

st.set_page_config(
    page_title="HVAC - Gebäudesimulation",
    page_icon="❄️",
    layout="wide",
)

st.title("❄️ HVAC-System")
st.markdown("---")

# Prüfe ob Geometrie vorhanden ist
if 'geometry' not in st.session_state:
    st.warning("⚠️ Bitte definieren Sie zuerst die Geometrie auf der **Geometrie-Seite**.")
    st.stop()

# Info-Box
st.info("""
**HVAC** = Heating, Ventilation, and Air Conditioning (Heizung, Lüftung, Klimatisierung)

Wählen Sie das Heizungs- und Kühlsystem für Ihr Gebäude.
""")

# System-Auswahl
st.subheader("🔧 System-Typ")

hvac_type = st.radio(
    "Wählen Sie das HVAC-System:",
    options=["Ideal Loads Air System"],
    index=0,
    help="Ideal Loads ist ein vereinfachtes System, das für erste Analysen ideal ist."
)

st.session_state['hvac_type'] = hvac_type

# Details zum gewählten System
st.markdown("---")
st.subheader("📋 System-Details")

if hvac_type == "Ideal Loads Air System":
    st.markdown("""
    ### Ideal Loads Air System

    Ein **vereinfachtes HVAC-System**, das perfekt für initiale Energieanalysen geeignet ist.

    **Eigenschaften:**
    - ✅ Unbegrenzte Heiz-/Kühlkapazität
    - ✅ Perfekte Temperaturregelung
    - ✅ Keine Berücksichtigung von Geräteeffizienz
    - ✅ Schnelle Simulation

    **Vorteile:**
    - Ideal für Gebäudeentwurf und Variantenvergleiche
    - Zeigt theoretischen minimalen Energiebedarf
    - Keine komplexe HVAC-Konfiguration nötig

    **Nachteile:**
    - Nicht realistisch für finale Energieberechnungen
    - Keine Simulation von echten Geräten (Wärmepumpen, Kessel, etc.)
    """)

    # Parameter
    st.markdown("---")
    st.subheader("⚙️ Parameter")

    col1, col2 = st.columns(2)

    with col1:
        heating_setpoint = st.slider(
            "Heiz-Solltemperatur (°C)",
            min_value=15.0,
            max_value=25.0,
            value=20.0,
            step=0.5,
            help="Zieltemperatur für die Heizung"
        )

        heating_limit = st.selectbox(
            "Heizleistungs-Limit",
            options=["Unbegrenzt", "Begrenzt"],
            index=0,
            help="Begrenzung der maximalen Heizleistung"
        )

    with col2:
        cooling_setpoint = st.slider(
            "Kühl-Solltemperatur (°C)",
            min_value=20.0,
            max_value=30.0,
            value=26.0,
            step=0.5,
            help="Zieltemperatur für die Kühlung"
        )

        cooling_limit = st.selectbox(
            "Kühlleistungs-Limit",
            options=["Unbegrenzt", "Begrenzt"],
            index=0,
            help="Begrenzung der maximalen Kühlleistung"
        )

    # Luftwechsel
    st.markdown("#### Lüftung")

    outdoor_air = st.checkbox(
        "Außenluft berücksichtigen",
        value=True,
        help="Frischluft-Zufuhr für Lüftung"
    )

    if outdoor_air:
        air_change_rate = st.slider(
            "Luftwechselrate (1/h)",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.1,
            help="Anzahl kompletter Luftwechsel pro Stunde"
        )
        st.caption(f"Pro Stunde wird die Raumluft {air_change_rate:.1f}x komplett ausgetauscht")
    else:
        air_change_rate = 0.0

    # Speichere HVAC-Konfiguration
    st.session_state['hvac_config'] = {
        'type': hvac_type,
        'heating_setpoint': heating_setpoint,
        'cooling_setpoint': cooling_setpoint,
        'heating_limit': heating_limit,
        'cooling_limit': cooling_limit,
        'outdoor_air': outdoor_air,
        'air_change_rate': air_change_rate,
    }

# Zusammenfassung
st.markdown("---")
st.subheader("📊 Konfiguration")

col1, col2 = st.columns(2)

with col1:
    st.success(f"""
    **Ausgewähltes System:**
    {hvac_type}
    """)

with col2:
    st.info(f"""
    **Solltemperaturen:**
    - Heizen: {st.session_state['hvac_config']['heating_setpoint']:.1f}°C
    - Kühlen: {st.session_state['hvac_config']['cooling_setpoint']:.1f}°C
    - Luftwechsel: {st.session_state['hvac_config']['air_change_rate']:.1f}/h
    """)

# Navigation
st.markdown("---")
st.markdown("### ➡️ Nächster Schritt")
st.markdown("Gehen Sie zur **Simulation-Seite** im Menü links, um die Simulation zu starten.")

# Debug: Zeige Konfiguration
with st.expander("🔍 Vollständige HVAC-Konfiguration (JSON)"):
    import json
    st.json(st.session_state['hvac_config'])

# Info über zukünftige Systeme
with st.expander("🚀 Geplante HVAC-Systeme (zukünftig)"):
    st.markdown("""
    In zukünftigen Versionen werden folgende HVAC-Systeme unterstützt:

    - **Wärmepumpe** (Air-to-Air, Air-to-Water)
    - **Gas-/Ölkessel**
    - **Fernwärme**
    - **Lüftungsanlagen** mit Wärmerückgewinnung
    - **Split-Klimaanlagen**
    - **Fußbodenheizung / Radiatoren**
    """)
