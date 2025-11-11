"""
🏗️ EnergyPlus Gebäude-Simulator - Web-Oberfläche

Einfache grafische Oberfläche zur Erstellung und Simulation von Gebäuden.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.hvac.template_manager import HVACTemplateManager
from src.simulation.runner import EnergyPlusRunner
from src.utils.config import get_config

# Page config
st.set_page_config(
    page_title="EnergyPlus Simulator",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="main-header">🏗️ EnergyPlus Gebäude-Simulator</p>', unsafe_allow_html=True)
st.markdown("---")

# Initialize session state
if 'simulation_done' not in st.session_state:
    st.session_state.simulation_done = False
if 'result' not in st.session_state:
    st.session_state.result = None
if 'idf_path' not in st.session_state:
    st.session_state.idf_path = None

# Sidebar - Building Parameters
st.sidebar.header("📐 Gebäude-Parameter")

# Geometry parameters
st.sidebar.subheader("Abmessungen")
length = st.sidebar.slider("Länge (m)", 5.0, 50.0, 15.0, 0.5)
width = st.sidebar.slider("Breite (m)", 5.0, 50.0, 12.0, 0.5)
height = st.sidebar.slider("Höhe (m)", 3.0, 30.0, 9.0, 0.5)

st.sidebar.subheader("Stockwerke")
num_floors = st.sidebar.slider("Anzahl Geschosse", 1, 10, 3, 1)

st.sidebar.subheader("Fenster")
wwr = st.sidebar.slider("Fensteranteil (%)", 10, 90, 35, 5) / 100.0

st.sidebar.subheader("Orientierung")
orientation = st.sidebar.slider("Ausrichtung (°)", 0, 360, 0, 15)

# HVAC System
st.sidebar.markdown("---")
st.sidebar.header("🔥 HVAC-System")
hvac_type = st.sidebar.selectbox(
    "System-Typ",
    ["ideal_loads"],
    format_func=lambda x: "Ideal Loads (unbegrenzte Kapazität)" if x == "ideal_loads" else x
)

# Weather file
st.sidebar.markdown("---")
st.sidebar.header("🌤️ Wetterdatei")

weather_files = list(Path("data/weather").glob("*.epw"))
if weather_files:
    weather_file = st.sidebar.selectbox(
        "Wähle Wetterdatei",
        weather_files,
        format_func=lambda x: x.name
    )
else:
    st.sidebar.warning("⚠️ Keine Wetterdatei gefunden!")
    st.sidebar.info("Bitte .epw Datei in `data/weather/` ablegen")
    weather_file = None

# Main area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Gebäude-Übersicht")

    # Calculate derived values
    floor_height = height / num_floors
    floor_area = length * width
    total_area = floor_area * num_floors

    # Display building info
    st.metric("Grundfläche", f"{floor_area:.1f} m²")
    st.metric("Gesamtfläche", f"{total_area:.1f} m²")
    st.metric("Geschosshöhe", f"{floor_height:.2f} m")

    # Building visualization (simple 3D representation)
    st.subheader("3D-Vorschau")

    # Create simple 3D box visualization
    fig = go.Figure()

    # Add building outline
    for floor in range(num_floors):
        z_base = floor * floor_height
        z_top = (floor + 1) * floor_height

        # Floor outline
        fig.add_trace(go.Scatter3d(
            x=[0, length, length, 0, 0],
            y=[0, 0, width, width, 0],
            z=[z_base] * 5,
            mode='lines',
            line=dict(color='blue', width=2),
            showlegend=False
        ))

        # Ceiling outline
        fig.add_trace(go.Scatter3d(
            x=[0, length, length, 0, 0],
            y=[0, 0, width, width, 0],
            z=[z_top] * 5,
            mode='lines',
            line=dict(color='blue', width=2),
            showlegend=False
        ))

    # Vertical edges
    for x, y in [(0, 0), (length, 0), (length, width), (0, width)]:
        fig.add_trace(go.Scatter3d(
            x=[x, x],
            y=[y, y],
            z=[0, height],
            mode='lines',
            line=dict(color='blue', width=2),
            showlegend=False
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="Länge (m)",
            yaxis_title="Breite (m)",
            zaxis_title="Höhe (m)",
            aspectmode='data'
        ),
        height=400,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.header("⚙️ Simulation")

    # Summary
    st.subheader("Zusammenfassung")
    st.write(f"**Gebäude**: {length}m × {width}m × {height}m")
    st.write(f"**Geschosse**: {num_floors}")
    st.write(f"**Fensteranteil**: {int(wwr*100)}%")
    st.write(f"**Orientierung**: {orientation}°")
    st.write(f"**HVAC**: {hvac_type}")

    # Simulation button
    st.markdown("---")

    if weather_file is None:
        st.error("❌ Keine Wetterdatei verfügbar!")
        simulate_btn = False
    else:
        simulate_btn = st.button("▶️ Simulation starten", type="primary", use_container_width=True)

    if simulate_btn:
        with st.spinner("🔧 Erstelle Gebäudemodell..."):
            # Create geometry
            geometry = BuildingGeometry(
                length=length,
                width=width,
                height=height,
                num_floors=num_floors,
                window_wall_ratio=wwr,
                orientation=orientation
            )

            # Generate IDF
            config = get_config()
            generator = SimpleBoxGenerator(config)
            idf = generator.create_model(geometry)

            # Add HVAC
            hvac_manager = HVACTemplateManager()
            idf = hvac_manager.apply_template_simple(idf, hvac_type)

            # Save IDF
            output_dir = Path("output/web_ui")
            output_dir.mkdir(parents=True, exist_ok=True)
            idf_path = output_dir / "building.idf"
            idf.saveas(str(idf_path), encoding='utf-8')

            st.session_state.idf_path = idf_path

            st.success("✅ Gebäudemodell erstellt!")

        with st.spinner("⚡ Führe EnergyPlus Simulation durch... (~10 Sekunden)"):
            # Run simulation
            runner = EnergyPlusRunner(config)
            result = runner.run_simulation(
                idf_path=idf_path,
                weather_file=weather_file,
                output_dir=output_dir / "simulation",
                output_prefix="building"
            )

            st.session_state.result = result
            st.session_state.simulation_done = True

        if result.success:
            st.success(f"✅ Simulation erfolgreich! ({result.execution_time:.1f}s)")
        else:
            st.error(f"❌ Simulation fehlgeschlagen: {result.error_message}")

# Results section
if st.session_state.simulation_done and st.session_state.result:
    st.markdown("---")
    st.header("📈 Ergebnisse")

    result = st.session_state.result

    if result.success:
        # Tabs for different result views
        tab1, tab2, tab3 = st.tabs(["📊 Übersicht", "📁 Dateien", "📥 Downloads"])

        with tab1:
            st.subheader("Simulationsergebnisse")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Laufzeit", f"{result.execution_time:.2f}s")

            with col2:
                # Count output files
                csv_files = list(result.output_dir.glob("*.csv"))
                st.metric("CSV-Dateien", len(csv_files))

            with col3:
                if result.sql_file and result.sql_file.exists():
                    st.metric("SQL-Datenbank", "✅ Vorhanden")
                else:
                    st.metric("SQL-Datenbank", "❌ Fehlt")

            # Try to load and display some results
            st.subheader("Zone Sizing Ergebnisse")

            zsz_file = result.output_dir / "buildingzsz.csv"
            if zsz_file.exists():
                df = pd.read_csv(zsz_file)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Keine Zone Sizing Daten verfügbar")

        with tab2:
            st.subheader("Ausgabedateien")

            output_files = list(result.output_dir.glob("*"))

            for file in output_files:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(file.name)
                with col2:
                    st.text(f"{file.stat().st_size / 1024:.1f} KB")
                with col3:
                    if st.button("Öffnen", key=f"open_{file.name}"):
                        import webbrowser
                        webbrowser.open(str(file.absolute()))

        with tab3:
            st.subheader("Downloads")

            # IDF file
            if st.session_state.idf_path and st.session_state.idf_path.exists():
                with open(st.session_state.idf_path, 'rb') as f:
                    st.download_button(
                        label="📥 IDF-Datei herunterladen",
                        data=f,
                        file_name="building.idf",
                        mime="text/plain"
                    )

            # HTML report
            html_files = list(result.output_dir.glob("*.htm*"))
            if html_files:
                for html_file in html_files:
                    with open(html_file, 'rb') as f:
                        st.download_button(
                            label=f"📥 {html_file.name}",
                            data=f,
                            file_name=html_file.name,
                            mime="text/html",
                            key=f"download_{html_file.name}"
                        )

            # CSV files
            csv_files = list(result.output_dir.glob("*.csv"))
            if csv_files:
                st.markdown("**CSV-Dateien:**")
                for csv_file in csv_files:
                    with open(csv_file, 'rb') as f:
                        st.download_button(
                            label=f"📥 {csv_file.name}",
                            data=f,
                            file_name=csv_file.name,
                            mime="text/csv",
                            key=f"download_{csv_file.name}"
                        )

    else:
        st.error("❌ Simulation fehlgeschlagen!")
        st.text(result.error_message)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9rem;'>
    🏗️ EnergyPlus Gebäude-Simulator | Made with Streamlit
</div>
""", unsafe_allow_html=True)
