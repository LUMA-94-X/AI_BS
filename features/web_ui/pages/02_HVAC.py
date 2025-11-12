"""HVAC-Seite für Heizungs-/Kühlsystem-Konfiguration."""

import streamlit as st
import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.building_model import get_building_model_from_session, save_building_model_to_session
from features.hvac.ideal_loads import create_building_with_hvac
from eppy.modeleditor import IDF

st.set_page_config(
    page_title="HVAC - Gebäudesimulation",
    page_icon="❄️",
    layout="wide",
)

st.title("❄️ HVAC-System")
st.markdown("---")

# Prüfe ob Geometrie ODER BuildingModel vorhanden ist
building_model = get_building_model_from_session(st.session_state)
has_geometry = 'geometry' in st.session_state

if not building_model and not has_geometry:
    st.warning("⚠️ Bitte definieren Sie zuerst ein Gebäudemodell auf der **Geometrie-Seite**:\n- Tab 'Einfache Eingabe' für SimpleBox\n- Tab 'Energieausweis' für 5-Zone-Modell (empfohlen)")
    st.stop()

# Kontextuelle Info: Welches Modell wird konfiguriert?
if building_model:
    if building_model.source == "energieausweis":
        st.info(f"""
        🏗️ **5-Zone-Modell aus Energieausweis**
        - Gebäudetyp: {building_model.gebaeudetyp}
        - Zonen: {building_model.num_zones}
        - Fläche: {building_model.geometry_summary.get('total_floor_area', 0):.0f} m²
        """)
    else:
        st.info(f"""
        📦 **SimpleBox-Modell**
        - Zonen: {building_model.num_zones}
        - Abmessungen: {building_model.geometry_summary['length']:.1f}m × {building_model.geometry_summary['width']:.1f}m × {building_model.geometry_summary['height']:.1f}m
        """)
elif has_geometry:
    # Legacy: Falls nur geometry vorhanden (alte Sessions)
    geom = st.session_state['geometry']
    st.info(f"""
    📦 **SimpleBox-Modell** (Legacy)
    - Abmessungen: {geom.length:.1f}m × {geom.width:.1f}m × {geom.height:.1f}m
    """)

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

    # Für 5-Zone-Modelle: HVAC direkt zum IDF hinzufügen
    if building_model and building_model.source == "energieausweis":
        st.markdown("---")
        st.subheader("🔧 HVAC zum IDF hinzufügen")

        if st.button("✅ HVAC-System jetzt konfigurieren", type="primary"):
            with st.spinner(f"Füge HVAC zu {building_model.num_zones} Zonen hinzu..."):
                try:
                    # IDF laden
                    idf_path = building_model.idf_path
                    if not idf_path.exists():
                        st.error(f"❌ IDF-Datei nicht gefunden: {idf_path}")
                        st.stop()

                    # IDF-Objekt aus Session State oder neu laden
                    if 'idf' in st.session_state:
                        idf = st.session_state['idf']
                    else:
                        from core.config import get_config
                        config = get_config()
                        from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
                        generator = FiveZoneGenerator(config)
                        idd_file = generator._get_idd_file()
                        IDF.setiddname(idd_file)
                        idf = IDF(str(idf_path))

                    # HVAC hinzufügen
                    idf = create_building_with_hvac(idf)

                    # IDF speichern
                    idf.save(str(idf_path))

                    # Session State aktualisieren
                    st.session_state['idf'] = idf

                    # BuildingModel aktualisieren (has_hvac = True)
                    building_model.has_hvac = True
                    save_building_model_to_session(st.session_state, building_model)

                    st.success(f"✅ HVAC erfolgreich zu {building_model.num_zones} Zonen hinzugefügt!")
                    st.info("➡️ Sie können nun zur **Simulation-Seite** gehen.")

                except Exception as e:
                    st.error(f"❌ Fehler beim Hinzufügen von HVAC: {e}")
                    import traceback
                    with st.expander("🐛 Fehlerdetails"):
                        st.code(traceback.format_exc())

        if building_model.has_hvac:
            st.success("✅ HVAC bereits konfiguriert! Sie können zur Simulation-Seite gehen.")

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
