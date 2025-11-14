"""Simulations-Seite für EnergyPlus-Simulation."""

import streamlit as st
import sys
from pathlib import Path
import time
from datetime import datetime

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from features.geometrie.box_generator import SimpleBoxGenerator
from features.hvac.ideal_loads import create_building_with_hvac
from features.simulation.runner import EnergyPlusRunner
from core.building_model import get_building_model_from_session
from eppy.modeleditor import IDF

st.set_page_config(
    page_title="Simulation - Gebäudesimulation",
    page_icon="▶️",
    layout="wide",
)

st.title("▶️ Simulation starten")
st.markdown("---")

# Prüfe ob Gebäudemodell ODER Geometrie vorhanden ist
building_model = get_building_model_from_session(st.session_state)
has_geometry = 'geometry' in st.session_state

if not building_model and not has_geometry:
    st.warning("⚠️ Bitte definieren Sie zuerst ein Gebäudemodell auf der **Geometrie-Seite**:\n- Tab 'Einfache Eingabe' für SimpleBox\n- Tab 'Energieausweis' für 5-Zone-Modell (empfohlen)")
    st.stop()

# Prüfe HVAC-Konfiguration
# Für 5-Zone: HVAC muss im IDF sein (has_hvac = True)
# Für SimpleBox: hvac_config reicht
if building_model:
    if building_model.source in ["energieausweis", "oib_energieausweis"] and not building_model.has_hvac:
        st.warning("⚠️ Bitte konfigurieren Sie zuerst das **HVAC-System** auf der HVAC-Seite.")
        st.stop()
    elif building_model.source == "simplebox" and 'hvac_config' not in st.session_state:
        st.warning("⚠️ Bitte konfigurieren Sie zuerst das **HVAC-System**.")
        st.stop()
elif has_geometry and 'hvac_config' not in st.session_state:
    # Legacy SimpleBox
    st.warning("⚠️ Bitte konfigurieren Sie zuerst das **HVAC-System**.")
    st.stop()

# Aktives Modell anzeigen
st.subheader("🎯 Ausgewähltes Gebäudemodell")
if building_model:
    if building_model.source in ["energieausweis", "oib_energieausweis"]:
        model_type = "OIB RL6 12.2-konforme Eingabe" if building_model.source == "oib_energieausweis" else "Energieausweis-Import"
        st.success(f"""
        **✅ 5-Zone-Modell bereit für Simulation**

        - **Quelle:** {model_type}
        - **Gebäudetyp:** {building_model.gebaeudetyp}
        - **Zonen:** {building_model.num_zones}
        - **Fläche:** {building_model.geometry_summary.get('total_floor_area', 0):.0f} m²
        - **HVAC:** {'✅ Konfiguriert' if building_model.has_hvac else '❌ Noch nicht konfiguriert'}
        - **IDF-Datei:** `{building_model.idf_path.name if building_model.idf_path else 'N/A'}`

        💡 *Um ein anderes Modell zu verwenden, gehen Sie zurück zur **Geometrie-Seite** und erstellen/laden Sie ein neues Modell.*
        """)
    else:
        st.success(f"""
        **✅ SimpleBox-Modell bereit für Simulation**

        - **Abmessungen:** {building_model.geometry_summary['length']:.1f}m × {building_model.geometry_summary['width']:.1f}m × {building_model.geometry_summary['height']:.1f}m
        - **Zonen:** {building_model.num_zones}
        - **Fläche:** {building_model.geometry_summary.get('total_floor_area', 0):.0f} m²

        💡 *Um ein anderes Modell zu verwenden, gehen Sie zurück zur **Geometrie-Seite** und erstellen/laden Sie ein neues Modell.*
        """)
elif has_geometry:
    st.success("""
    **✅ SimpleBox-Modell (Legacy) bereit für Simulation**

    💡 *Um ein anderes Modell zu verwenden, gehen Sie zurück zur **Geometrie-Seite**.*
    """)

st.markdown("---")

# Info-Box
st.info("""
**Simulation starten:** Die EnergyPlus-Simulation wird mit Ihren Parametern ausgeführt.
Dies kann je nach Gebäudegröße 3-30 Sekunden dauern.
""")

# Konfigurationsübersicht
st.subheader("📋 Konfigurationsübersicht")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Gebäudemodell**")
    if building_model:
        geom = building_model.geometry_summary
        if building_model.source in ["energieausweis", "oib_energieausweis"]:
            model_type = "OIB RL6 12.2" if building_model.source == "oib_energieausweis" else "Energieausweis"
            st.write(f"- Quelle: 5-Zone-Modell ({model_type})")
            st.write(f"- Typ: {building_model.gebaeudetyp}")
            st.write(f"- Zonen: {building_model.num_zones}")
            st.write(f"- Fläche: {geom.get('total_floor_area', 0):.1f} m²")
            st.write(f"- Geschosse: {geom.get('num_floors', 0)}")
        else:
            st.write(f"- Quelle: SimpleBox")
            st.write(f"- Länge: {geom['length']:.1f} m")
            st.write(f"- Breite: {geom['width']:.1f} m")
            st.write(f"- Höhe: {geom['height']:.1f} m")
            st.write(f"- Fläche: {geom.get('total_floor_area', 0):.1f} m²")
    elif has_geometry:
        geometry = st.session_state['geometry']
        st.write(f"- Quelle: SimpleBox (Legacy)")
        st.write(f"- Länge: {geometry.length:.1f} m")
        st.write(f"- Breite: {geometry.width:.1f} m")
        st.write(f"- Höhe: {geometry.height:.1f} m")
        st.write(f"- Fläche: {geometry.total_floor_area:.1f} m²")

with col2:
    st.markdown("**HVAC-System**")
    if building_model and building_model.source in ["energieausweis", "oib_energieausweis"]:
        st.write(f"- Typ: Ideal Loads")
        st.write(f"- Status: ✅ Konfiguriert")
        st.write(f"- Zonen: {building_model.num_zones}")
    else:
        hvac_config = st.session_state.get('hvac_config', {})
        st.write(f"- Typ: {hvac_config.get('type', 'N/A')}")
        st.write(f"- Heizen: {hvac_config.get('heating_setpoint', 20):.1f}°C")
        st.write(f"- Kühlen: {hvac_config.get('cooling_setpoint', 26):.1f}°C")
        st.write(f"- Lüftung: {hvac_config.get('air_change_rate', 0):.1f}/h")

with col3:
    st.markdown("**Simulation**")
    if building_model:
        model_name = "5-Zone-Modell" if building_model.source in ["energieausweis", "oib_energieausweis"] else "SimpleBox"
        st.write(f"- Modell: {model_name}")
    else:
        st.write(f"- Modell: SimpleBox")
    st.write(f"- Wetterdaten: example.epw")
    st.write(f"- Zeitraum: 1 Jahr (8760 h)")

# Advanced Simulation Settings
st.markdown("---")
with st.expander("⚙️ Advanced Simulation Settings", expanded=False):
    st.markdown("""
    **Expert Options**: Customize simulation timestep and output parameters.
    Leave defaults for standard annual energy simulation.
    """)

    col_sim1, col_sim2 = st.columns(2)

    with col_sim1:
        st.markdown("#### Timestep")
        timestep = st.select_slider(
            "Timesteps per hour",
            options=[1, 2, 4, 6, 10, 12, 15, 20, 30, 60],
            value=4,
            help="Higher = more accurate but slower. 4 is standard (15 min intervals)."
        )
        st.caption(f"1 timestep = {60/timestep:.1f} minutes")

    with col_sim2:
        st.markdown("#### Reporting")
        reporting_freq = st.selectbox(
            "Output Frequency",
            options=["Timestep", "Hourly", "Daily", "Monthly"],
            index=1,  # Hourly default
            help="How often to save results"
        )

    # Run Period
    st.markdown("#### Simulation Period")
    col_per1, col_per2 = st.columns(2)

    with col_per1:
        start_month = st.selectbox("Start Month", options=list(range(1, 13)), index=0, format_func=lambda x: f"{x:02d}")
        start_day = st.number_input("Start Day", min_value=1, max_value=31, value=1)

    with col_per2:
        end_month = st.selectbox("End Month", options=list(range(1, 13)), index=11, format_func=lambda x: f"{x:02d}")
        end_day = st.number_input("End Day", min_value=1, max_value=31, value=31)

    # Output Variables
    st.markdown("#### Output Variables")
    output_presets = st.selectbox(
        "Output Preset",
        options=["Standard (Energy + Temperature)", "Extended (+ Surfaces)", "Minimal", "Custom"],
        index=0
    )

    if output_presets == "Custom":
        custom_vars = st.text_area(
            "Output Variables (one per line)",
            value="Zone Mean Air Temperature\nZone Air System Sensible Heating Energy\nZone Air System Sensible Cooling Energy",
            height=150,
            help="Enter EnergyPlus output variable names, one per line"
        )
        output_variables = [v.strip() for v in custom_vars.split('\n') if v.strip()]
    else:
        # Predefined lists
        presets = {
            "Standard (Energy + Temperature)": [
                "Zone Mean Air Temperature",
                "Zone Air System Sensible Heating Energy",
                "Zone Air System Sensible Cooling Energy",
                "Site Outdoor Air Drybulb Temperature",
            ],
            "Extended (+ Surfaces)": [
                "Zone Mean Air Temperature",
                "Zone Air System Sensible Heating Energy",
                "Zone Air System Sensible Cooling Energy",
                "Site Outdoor Air Drybulb Temperature",
                "Surface Inside Face Temperature",
                "Surface Outside Face Temperature",
                "Zone Lights Electric Energy",
                "Zone Electric Equipment Electric Energy",
            ],
            "Minimal": [
                "Zone Mean Air Temperature",
                "Zone Air System Sensible Heating Energy",
                "Zone Air System Sensible Cooling Energy",
            ]
        }
        output_variables = presets.get(output_presets, presets["Standard (Energy + Temperature)"])

    st.caption(f"Selected: {len(output_variables)} variables")

    # Store in session state
    st.session_state['sim_settings'] = {
        'timestep': timestep,
        'reporting_frequency': reporting_freq,
        'start_month': start_month,
        'start_day': start_day,
        'end_month': end_month,
        'end_day': end_day,
        'output_variables': output_variables
    }

# Wetterdatei-Auswahl
st.markdown("---")
st.subheader("🌦️ Wetterdaten")

weather_dir = Path("resources/energyplus/weather")
if weather_dir.exists():
    weather_files = list(weather_dir.glob("**/*.epw"))  # Recursive search in subdirectories
    if weather_files:
        weather_file = st.selectbox(
            "Wetterdatei wählen:",
            options=[f.name for f in weather_files],
            index=0,
            help="EPW-Datei mit stündlichen Wetterdaten für ein Jahr"
        )
        # Find the selected file
        weather_path = [f for f in weather_files if f.name == weather_file][0]

        # Store in session state for later export
        st.session_state['weather_file'] = str(weather_path)
    else:
        st.error("❌ Keine Wetterdateien gefunden in `resources/energyplus/weather/`")
        st.stop()
else:
    st.error("❌ Verzeichnis `resources/energyplus/weather/` nicht gefunden")
    st.stop()

# Ausgabeverzeichnis
output_name = st.text_input(
    "Ausgabeverzeichnis:",
    value=f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    help="Name für das Ausgabeverzeichnis (wird in output/ erstellt)"
)

output_dir = Path("output") / output_name

# Simulation starten
st.markdown("---")
st.subheader("🚀 Simulation")

if st.button("▶️ Simulation starten", type="primary", use_container_width=True):
    # Progress-Container
    progress_container = st.container()

    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            idf_path = output_dir / "building.idf"

            # Unterschiedliche IDF-Behandlung je nach Quelle
            if building_model and building_model.source in ["energieausweis", "oib_energieausweis"]:
                # 5-Zone-Modell: IDF aus Datei laden (bereits mit HVAC)
                model_type = "OIB RL6 12.2" if building_model.source == "oib_energieausweis" else "Energieausweis"
                status_text.info(f"🏗️ Lade 5-Zone-IDF ({model_type})...")
                progress_bar.progress(10)

                source_idf_path = building_model.idf_path
                if not source_idf_path.exists():
                    st.error(f"❌ IDF-Datei nicht gefunden: {source_idf_path}")
                    st.stop()

                # IDF aus Session State oder neu laden
                if 'idf' in st.session_state:
                    idf = st.session_state['idf']
                    status_text.info("✓ IDF aus Session State geladen")
                else:
                    from core.config import get_config
                    config = get_config()
                    from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
                    generator = FiveZoneGenerator(config)
                    idd_file = generator._get_idd_file()
                    IDF.setiddname(idd_file)
                    idf = IDF(str(source_idf_path))
                    status_text.info("✓ IDF von Datei geladen")

                # Kopiere IDF in Output-Verzeichnis
                try:
                    import shutil
                    # Einfach Datei kopieren statt eppy save (robuster)
                    shutil.copy(str(source_idf_path), str(idf_path))
                    status_text.info(f"✓ IDF kopiert nach: {idf_path.name}")

                    # Prüfe ob Datei existiert
                    if not idf_path.exists():
                        st.error(f"❌ IDF-Kopie fehlgeschlagen: {idf_path} existiert nicht!")
                        st.stop()
                except Exception as e:
                    st.error(f"❌ Fehler beim Kopieren der IDF-Datei: {e}")
                    import traceback
                    with st.expander("🐛 Fehlerdetails"):
                        st.code(traceback.format_exc())
                    st.stop()

                progress_bar.progress(40)
                status_text.info(f"✅ 5-Zone-IDF bereit ({building_model.num_zones} Zonen)")

            else:
                # SimpleBox: IDF on-the-fly erstellen
                status_text.info("🏗️ Erstelle SimpleBox-IDF...")
                progress_bar.progress(10)

                geometry = st.session_state.get('geometry')
                if not geometry:
                    st.error("❌ Keine Geometrie gefunden")
                    st.stop()

                # Get simulation settings from session state
                sim_settings = st.session_state.get('sim_settings', {})

                generator = SimpleBoxGenerator()
                idf = generator.create_model(geometry, idf_path, sim_settings=sim_settings)

                progress_bar.progress(30)
                status_text.info("❄️ Füge HVAC-System hinzu...")

                # HVAC hinzufügen mit User-Setpoints
                hvac_config = st.session_state.get('hvac_config', {})
                idf = create_building_with_hvac(
                    idf,
                    heating_setpoint=hvac_config.get('heating_setpoint', 20.0),
                    cooling_setpoint=hvac_config.get('cooling_setpoint', 26.0)
                )
                idf.save(str(idf_path))

                progress_bar.progress(40)

            # Ab hier gemeinsam für beide Workflows
            status_text.info("▶️ Bereite Simulation vor...")

            # Schritt 3: Simulation ausführen
            runner = EnergyPlusRunner()

            # Debug: Prüfe ob ExpandObjects vorhanden
            if runner.expand_objects_exe.exists():
                status_text.info(f"✓ ExpandObjects gefunden: {runner.expand_objects_exe.name}")
            else:
                status_text.warning(f"⚠️ ExpandObjects nicht gefunden")

            # Debug: Prüfe ob HVACTemplate im IDF
            if runner._needs_expand_objects(idf_path):
                status_text.info("⚙️ HVACTemplate-Objekte gefunden - ExpandObjects wird ausgeführt...")

            start_time = time.time()

            result = runner.run_simulation(
                idf_path=str(idf_path),
                weather_file=str(weather_path),
                output_dir=str(output_dir)
            )

            elapsed_time = time.time() - start_time

            progress_bar.progress(100)

            # Ergebnis prüfen
            if result.success:
                status_text.success(f"✅ Simulation erfolgreich! ({elapsed_time:.1f}s)")

                # Speichere Ergebnisse im Session State
                st.session_state['simulation_result'] = result
                st.session_state['simulation_output_dir'] = output_dir

                # Erfolgs-Meldung
                st.balloons()
                error_file = result.output_dir / "eplusout.err"

                # Prüfe auf verdächtig kurze Simulationszeit
                if elapsed_time < 5.0:
                    st.warning(f"""
                    ⚠️ **Achtung:** Die Simulation war sehr schnell ({elapsed_time:.1f}s).
                    Eine vollständige Jahressimulation dauert normalerweise 10-30 Sekunden.

                    Bitte prüfen Sie die Ergebnis-Logs im Expander unten.
                    """)

                st.success(f"""
                ### 🎉 Simulation erfolgreich abgeschlossen!

                **Dauer:** {elapsed_time:.1f} Sekunden

                **Ausgabedateien:**
                - IDF-Modell: `{idf_path}`
                - SQL-Datenbank: `{result.sql_file}`
                - Fehler-Log: `{error_file}`
                """)

                # Zeige err file Info
                if error_file.exists():
                    err_size = error_file.stat().st_size
                    if err_size == 0:
                        st.warning("""
                        ⚠️ **Ungewöhnlich:** Die Fehler-Datei ist leer (0 Bytes).
                        EnergyPlus sollte normalerweise immer etwas ins Error-Log schreiben.
                        Dies kann auf ein Problem bei der Ausführung hinweisen.
                        """)

                # Zeige Log-Dateien als Expander
                with st.expander("📄 Simulation Logs (Error File)"):
                    if error_file.exists() and error_file.stat().st_size > 0:
                        with open(error_file, 'r', encoding='utf-8', errors='ignore') as f:
                            err_content = f.read()
                            st.code(err_content, language="text")
                    elif error_file.exists():
                        st.warning("Error-Datei ist leer (0 Bytes)")
                    else:
                        st.error("Error-Datei nicht gefunden")

                # Navigation
                st.markdown("---")
                st.markdown("### ➡️ Nächster Schritt")
                st.info("Gehen Sie zur **Ergebnisse-Seite** im Menü links, um die Simulation auszuwerten.")

            else:
                status_text.error("❌ Simulation fehlgeschlagen!")
                error_file = result.output_dir / "eplusout.err"
                st.error(f"""
                ### ❌ Simulation fehlgeschlagen

                **Fehler:** {result.error_message}

                **Ausgabe-Verzeichnis:** `{output_dir}`

                Prüfen Sie die Fehler-Datei: `{error_file}`
                """)

                # Zeige erste Zeilen der Fehler-Datei
                if error_file.exists():
                    with st.expander("📄 Fehler-Log (erste 50 Zeilen)"):
                        with open(error_file, 'r', encoding='utf-8', errors='ignore') as f:
                            error_lines = f.readlines()[:50]
                            st.code(''.join(error_lines))

        except Exception as e:
            progress_bar.progress(0)
            status_text.error(f"❌ Fehler: {str(e)}")
            st.exception(e)

# Zeige vorherige Simulation falls vorhanden
if 'simulation_result' in st.session_state:
    st.markdown("---")
    st.subheader("📂 Letzte Simulation")

    result = st.session_state['simulation_result']
    output_dir = st.session_state['simulation_output_dir']

    col1, col2 = st.columns(2)

    with col1:
        if result.success:
            st.success("✅ Erfolgreich")
        else:
            st.error("❌ Fehlgeschlagen")

    with col2:
        st.write(f"**Ausgabe:** `{output_dir}`")

    # Links zu Ergebnissen
    if result.success:
        st.markdown("**Ergebnis-Dateien:**")
        if result.sql_file:
            st.write(f"- SQL-Datenbank: `{result.sql_file}`")
        error_file = result.output_dir / "eplusout.err"
        if error_file.exists():
            st.write(f"- Fehler-Log: `{error_file}`")

        st.info("👉 Gehen Sie zur **Ergebnisse-Seite** für detaillierte Auswertungen.")

# Hilfe
with st.expander("❓ Hilfe: Simulation schlägt fehl"):
    st.markdown("""
    **Häufige Probleme:**

    1. **EnergyPlus nicht gefunden**
       - Prüfen Sie, ob EnergyPlus installiert ist
       - Passen Sie `config/default_config.yaml` an

    2. **Wetterdatei fehlt**
       - Laden Sie eine EPW-Datei von https://energyplus.net/weather
       - Legen Sie sie in `resources/energyplus/weather/` ab

    3. **IDF-Fehler**
       - Prüfen Sie die Gebäudeparameter
       - Stellen Sie sicher, dass alle Werte im gültigen Bereich sind

    4. **Timeout**
       - Große Gebäude benötigen mehr Zeit
       - Reduzieren Sie Stockwerkzahl oder Komplexität
    """)
