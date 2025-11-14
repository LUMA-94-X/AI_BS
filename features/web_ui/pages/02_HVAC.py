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
    if building_model.source in ["energieausweis", "oib_energieausweis"]:
        model_type = "OIB RL6 12.2" if building_model.source == "oib_energieausweis" else "Energieausweis"
        st.info(f"""
        🏗️ **5-Zone-Modell aus {model_type}**
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
st.subheader("🔧 Gebäudetechnik-Systeme")

st.markdown("""
Wählen Sie die gebäudetechnischen Systeme für Ihr Gebäude. Diese bestimmen:
- **Heizsystem:** Energieträger für Heizwärme → PEB & CO₂ Berechnung
- **Lüftungssystem:** Frischluftzufuhr → Simulationsverhalten
""")

col_heiz, col_lueft = st.columns(2)

with col_heiz:
    st.markdown("### 🔥 Heizsystem")
    heating_system = st.selectbox(
        "Wärmeerzeuger:",
        options=[
            "Ideal Loads Air System",
            "Gas-Brennwertkessel",
            "Öl-Brennwertkessel",
            "Biomasse-Kessel",
            "Wärmepumpe",
            "Fernwärme",
            "Fernwärme KWK",
            "Fernwärme Heizwerk"
        ],
        index=0,
        help="Bestimmt den Energieträger für die Primärenergie-Berechnung (OIB RL6 § 9.2)",
        key="heating_system_select"
    )

with col_lueft:
    st.markdown("### 🌬️ Lüftungssystem")
    ventilation_system = st.selectbox(
        "Lüftungsart:",
        options=[
            "Ideal Loads Air System",
            "Mechanische Lüftung mit WRG",
            "Mechanische Lüftung ohne WRG",
            "Natürliche Lüftung"
        ],
        index=0,
        help="Bestimmt die Frischluftzufuhr und Wärmerückgewinnung",
        key="ventilation_system_select"
    )

st.session_state['heating_system'] = heating_system
st.session_state['ventilation_system'] = ventilation_system
# Legacy-Kompatibilität: hvac_type für bisherige Berechnungen
st.session_state['hvac_type'] = heating_system

# Hinweis zur System-Auswahl
st.info("""
ℹ️ **Hinweis zur Systemauswahl:**

**Heizsystem:**
- Bestimmt **Konversionsfaktoren** für PEB & CO₂ (OIB RL6 § 7)
- Wird für Energieausweis-Kennzahlen verwendet

**Lüftungssystem:**
- Bestimmt Frischluftzufuhr und Wärmerückgewinnung
- Beeinflusst Lüftungswärmeverluste

**Aktueller Stand:**
- ✅ **PEB/CO₂:** Verwendet gewähltes Heizsystem
- ⏳ **Simulation:** Verwendet derzeit "Ideal Loads" (realistische Systeme folgen)
""")

# Details zu den gewählten Systemen
st.markdown("---")
st.subheader("📋 System-Details")

col_heiz_detail, col_lueft_detail = st.columns(2)

with col_heiz_detail:
    st.markdown("### 🔥 Heizsystem")
    # Zeige Konversionsfaktoren aus OIB RL6 für gewähltes Heizsystem
    try:
        from data.oib_konversionsfaktoren import get_konversionsfaktor_fuer_hvac
        faktor = get_konversionsfaktor_fuer_hvac(heating_system)

        st.markdown(f"""
        **{heating_system}**

        **Konversionsfaktoren (OIB RL6 § 7):**
        - **Energieträger:** {faktor.energietraeger}
        - **f_PE:** {faktor.f_pe:.2f}
          - Nicht-erneuerbar: {faktor.f_pe_n_ern:.2f}
          - Erneuerbar: {faktor.f_pe_ern:.2f}
        - **CO₂:** {faktor.f_co2} g/kWh
        """)
    except ImportError:
        st.warning("⚠️ Konversionsfaktoren nicht verfügbar")

with col_lueft_detail:
    st.markdown("### 🌬️ Lüftungssystem")
    st.markdown(f"""
    **{ventilation_system}**

    **Eigenschaften:**
    """)

    if ventilation_system == "Ideal Loads Air System":
        st.markdown("""
        - ✅ Perfekte Temperaturregelung
        - ✅ Unbegrenzte Kapazität
        - ⚠️ Keine realistische Geräte-Modellierung
        """)
    elif "WRG" in ventilation_system:
        st.markdown("""
        - ✅ Wärmerückgewinnung (ca. 75-85%)
        - ✅ Reduzierte Lüftungsverluste
        - ✅ Energieeffizient
        """)
    elif "ohne WRG" in ventilation_system:
        st.markdown("""
        - ⚠️ Keine Wärmerückgewinnung
        - ⚠️ Höhere Lüftungsverluste
        - ✅ Einfache Technik
        """)
    else:
        st.markdown("""
        - ✅ Keine Lüftungstechnik nötig
        - ⚠️ Abhängig von Nutzerverhalten
        - ⚠️ Unkontrollierte Verluste
        """)

# Parameter (für alle Systeme)
st.markdown("---")
st.subheader("⚙️ System-Parameter")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔥 Heizung")
    heating_enabled = st.checkbox(
        "Heizung aktivieren",
        value=True,
        help="Aktiviert/deaktiviert die Heizung komplett"
    )

    if heating_enabled:
        st.markdown("**Status:** ✅ AKTIVIERT")
        heating_setpoint = st.slider(
            "Solltemperatur (°C)",
            min_value=15.0,
            max_value=25.0,
            value=20.0,
            step=0.5,
            help="Zieltemperatur für die Heizung"
        )

        heating_limit = st.selectbox(
            "Leistungs-Limit",
            options=["Unbegrenzt", "Begrenzt"],
            index=0,
            help="Begrenzung der maximalen Heizleistung"
        )
    else:
        st.markdown("**Status:** ❌ DEAKTIVIERT")
        st.caption("Heizung ist ausgeschaltet - keine Wärmeabgabe")
        heating_setpoint = 20.0  # Fallback
        heating_limit = "Unbegrenzt"

with col2:
    st.markdown("### ❄️ Kühlung")
    cooling_enabled = st.checkbox(
        "Kühlung aktivieren",
        value=True,
        help="Aktiviert/deaktiviert die Kühlung komplett"
    )

    if cooling_enabled:
        st.markdown("**Status:** ✅ AKTIVIERT")
        cooling_setpoint = st.slider(
            "Solltemperatur (°C)",
            min_value=20.0,
            max_value=30.0,
            value=26.0,
            step=0.5,
            help="Zieltemperatur für die Kühlung"
        )

        cooling_limit = st.selectbox(
            "Leistungs-Limit",
            options=["Unbegrenzt", "Begrenzt"],
            index=0,
            help="Begrenzung der maximalen Kühlleistung"
        )
    else:
        st.markdown("**Status:** ❌ DEAKTIVIERT")
        st.caption("Kühlung ist ausgeschaltet - keine Kälteabgabe")
        cooling_setpoint = 26.0  # Fallback
        cooling_limit = "Unbegrenzt"

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
    'type': heating_system,  # Verwendet Heizsystem für PEB-Berechnung
    'heating_system': heating_system,
    'ventilation_system': ventilation_system,
    'heating_enabled': heating_enabled,
    'cooling_enabled': cooling_enabled,
    'heating_setpoint': heating_setpoint,
    'cooling_setpoint': cooling_setpoint,
    'heating_limit': heating_limit,
    'cooling_limit': cooling_limit,
    'outdoor_air': outdoor_air,
    'air_change_rate': air_change_rate,
}

# Für 5-Zone-Modelle: HVAC direkt zum IDF hinzufügen
if building_model and building_model.source in ["energieausweis", "oib_energieausweis"]:
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

                    # HVAC hinzufügen mit User-Setpoints und Enable/Disable Flags
                    hvac_config = st.session_state.get('hvac_config', {})
                    idf = create_building_with_hvac(
                        idf,
                        heating_setpoint=hvac_config.get('heating_setpoint', 20.0),
                        cooling_setpoint=hvac_config.get('cooling_setpoint', 26.0),
                        heating_enabled=hvac_config.get('heating_enabled', True),
                        cooling_enabled=hvac_config.get('cooling_enabled', True)
                    )

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
st.subheader("📊 Konfigurationsübersicht")

hvac_cfg = st.session_state.get('hvac_config', {})

# Hole Systemtypen aus session_state (sicherer als lokale Variablen)
configured_heating = hvac_cfg.get('heating_system') or hvac_cfg.get('type', 'Nicht konfiguriert')
configured_ventilation = hvac_cfg.get('ventilation_system', 'Nicht konfiguriert')

# System-Status
status_text = []
if hvac_cfg.get('heating_enabled', True):
    status_text.append(f"🔥 Heizung: **AKTIV** (Sollwert: {hvac_cfg.get('heating_setpoint', 20):.1f}°C)")
else:
    status_text.append(f"🔥 Heizung: **DEAKTIVIERT**")

if hvac_cfg.get('cooling_enabled', True):
    status_text.append(f"❄️ Kühlung: **AKTIV** (Sollwert: {hvac_cfg.get('cooling_setpoint', 26):.1f}°C)")
else:
    status_text.append(f"❄️ Kühlung: **DEAKTIVIERT**")

status_text.append(f"💨 Luftwechsel: **{hvac_cfg.get('air_change_rate', 0.5):.1f} 1/h**")

st.success(f"""
**Heizsystem:** {configured_heating}
**Lüftungssystem:** {configured_ventilation}

{chr(10).join(status_text)}
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
