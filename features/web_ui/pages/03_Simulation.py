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

st.set_page_config(
    page_title="Simulation - Gebäudesimulation",
    page_icon="▶️",
    layout="wide",
)

st.title("▶️ Simulation starten")
st.markdown("---")

# Prüfe ob Geometrie und HVAC konfiguriert sind
if 'geometry' not in st.session_state:
    st.warning("⚠️ Bitte definieren Sie zuerst die **Geometrie**.")
    st.stop()

if 'hvac_config' not in st.session_state:
    st.warning("⚠️ Bitte konfigurieren Sie zuerst das **HVAC-System**.")
    st.stop()

# Info-Box
st.info("""
**Simulation starten:** Die EnergyPlus-Simulation wird mit Ihren Parametern ausgeführt.
Dies kann je nach Gebäudegröße 3-30 Sekunden dauern.
""")

# Konfigurationsübersicht
st.subheader("📋 Konfigurationsübersicht")

col1, col2, col3 = st.columns(3)

geometry = st.session_state['geometry']
hvac_config = st.session_state['hvac_config']

with col1:
    st.markdown("**Geometrie**")
    st.write(f"- Länge: {geometry.length:.1f} m")
    st.write(f"- Breite: {geometry.width:.1f} m")
    st.write(f"- Höhe: {geometry.height:.1f} m")
    st.write(f"- Stockwerke: {geometry.num_floors}")
    st.write(f"- Fläche: {geometry.total_floor_area:.1f} m²")

with col2:
    st.markdown("**HVAC-System**")
    st.write(f"- Typ: {hvac_config['type']}")
    st.write(f"- Heizen: {hvac_config['heating_setpoint']:.1f}°C")
    st.write(f"- Kühlen: {hvac_config['cooling_setpoint']:.1f}°C")
    st.write(f"- Lüftung: {hvac_config['air_change_rate']:.1f}/h")

with col3:
    st.markdown("**Simulation**")
    st.write(f"- Gebäudemodell: Einfache Box")
    st.write(f"- Wetterdaten: example.epw")
    st.write(f"- Zeitraum: 1 Jahr (8760 h)")

# Wetterdatei-Auswahl
st.markdown("---")
st.subheader("🌦️ Wetterdaten")

weather_dir = Path("data/weather")
if weather_dir.exists():
    weather_files = list(weather_dir.glob("*.epw"))
    if weather_files:
        weather_file = st.selectbox(
            "Wetterdatei wählen:",
            options=[f.name for f in weather_files],
            index=0,
            help="EPW-Datei mit stündlichen Wetterdaten für ein Jahr"
        )
        weather_path = weather_dir / weather_file
    else:
        st.error("❌ Keine Wetterdateien gefunden in `data/weather/`")
        st.stop()
else:
    st.error("❌ Verzeichnis `data/weather/` nicht gefunden")
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
            # Schritt 1: IDF erstellen
            status_text.info("🏗️ Erstelle IDF-Modell...")
            progress_bar.progress(10)

            generator = SimpleBoxGenerator()
            idf_path = output_dir / "building.idf"
            output_dir.mkdir(parents=True, exist_ok=True)

            idf = generator.create_model(geometry, idf_path)

            progress_bar.progress(30)
            status_text.info("❄️ Füge HVAC-System hinzu...")

            # Schritt 2: HVAC hinzufügen
            idf = create_building_with_hvac(idf)
            idf.save(str(idf_path))

            progress_bar.progress(40)
            status_text.info("▶️ Starte EnergyPlus-Simulation...")

            # Schritt 3: Simulation ausführen
            runner = EnergyPlusRunner()
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
                st.success(f"""
                ### 🎉 Simulation erfolgreich abgeschlossen!

                **Dauer:** {elapsed_time:.1f} Sekunden

                **Ausgabedateien:**
                - IDF-Modell: `{idf_path}`
                - SQL-Datenbank: `{result.sql_file}`
                - Fehler-Log: `{error_file}`
                """)

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
       - Legen Sie sie in `data/weather/` ab

    3. **IDF-Fehler**
       - Prüfen Sie die Gebäudeparameter
       - Stellen Sie sicher, dass alle Werte im gültigen Bereich sind

    4. **Timeout**
       - Große Gebäude benötigen mehr Zeit
       - Reduzieren Sie Stockwerkzahl oder Komplexität
    """)
