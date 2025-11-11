"""Ergebnisse-Seite für Auswertung der Simulation."""

import streamlit as st
import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from features.auswertung.kpi_rechner import KennzahlenRechner
from features.auswertung.visualisierung import ErgebnisVisualisierer
from features.auswertung.sql_parser import EnergyPlusSQLParser

st.set_page_config(
    page_title="Ergebnisse - Gebäudesimulation",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Simulationsergebnisse")
st.markdown("---")

# Prüfe ob Simulation vorhanden ist
if 'simulation_result' not in st.session_state:
    st.warning("⚠️ Bitte führen Sie zuerst eine **Simulation** durch.")
    st.stop()

result = st.session_state['simulation_result']
geometry = st.session_state['geometry']

if not result.success:
    st.error("❌ Die Simulation war nicht erfolgreich. Bitte überprüfen Sie die Simulation.")
    st.stop()

# Lade Ergebnisse
try:
    # KPIs berechnen
    rechner = KennzahlenRechner(geometry.total_floor_area)
    kennzahlen = rechner.berechne_kennzahlen(sql_file=result.sql_file)

    # KPIs anzeigen
    st.subheader("🎯 Energiekennzahlen")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Effizienzklasse mit Farbe
        klasse = kennzahlen.effizienzklasse
        color_map = {
            'A+': 'green', 'A': 'green', 'B': 'lightgreen',
            'C': 'yellow', 'D': 'orange', 'E': 'orange',
            'F': 'red', 'G': 'red', 'H': 'darkred'
        }
        color = color_map.get(klasse, 'gray')

        st.markdown(f"""
        <div style='background-color: {color}; padding: 20px; border-radius: 10px; text-align: center;'>
            <h1 style='margin: 0; color: white;'>{klasse}</h1>
            <p style='margin: 0; color: white;'>Effizienzklasse</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.metric(
            "Energiekennzahl",
            f"{kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a",
            help="Gesamter Energiebedarf pro Quadratmeter und Jahr"
        )

    with col3:
        st.metric(
            "Heizbedarf",
            f"{kennzahlen.heizkennzahl_kwh_m2a:.1f} kWh/m²a",
            help="Spezifischer Heizwärmebedarf"
        )

    with col4:
        st.metric(
            "Kühlbedarf",
            f"{kennzahlen.kuehlkennzahl_kwh_m2a:.1f} kWh/m²a",
            help="Spezifischer Kühlbedarf"
        )

    # Bewertung
    st.markdown("---")
    col_bewertung, col_komfort = st.columns(2)

    with col_bewertung:
        st.subheader("💡 Bewertung")
        bewertung_text = kennzahlen.bewertung
        if klasse in ['A+', 'A', 'B']:
            st.success(bewertung_text)
        elif klasse in ['C', 'D']:
            st.info(bewertung_text)
        else:
            st.warning(bewertung_text)

    with col_komfort:
        st.subheader("🌡️ Thermischer Komfort")
        komfort = kennzahlen.thermische_behaglichkeit
        if komfort == "Gut":
            st.success(f"✅ {komfort}")
        elif komfort == "Akzeptabel":
            st.info(f"ℹ️ {komfort}")
        else:
            st.warning(f"⚠️ {komfort}")

    # Detaillierte Energiebilanz
    st.markdown("---")
    st.subheader("⚡ Detaillierte Energiebilanz")

    col1, col2, col3 = st.columns(3)

    ergebnisse = kennzahlen.ergebnisse

    with col1:
        st.markdown("**Heizung**")
        st.metric("Gesamt", f"{ergebnisse.heizbedarf_kwh:.0f} kWh")
        st.metric("Spezifisch", f"{kennzahlen.heizkennzahl_kwh_m2a:.1f} kWh/m²a")
        st.metric("Spitzenlast", f"{ergebnisse.spitzenlast_heizung_kw:.1f} kW")

    with col2:
        st.markdown("**Kühlung**")
        st.metric("Gesamt", f"{ergebnisse.kuehlbedarf_kwh:.0f} kWh")
        st.metric("Spezifisch", f"{kennzahlen.kuehlkennzahl_kwh_m2a:.1f} kWh/m²a")
        st.metric("Spitzenlast", f"{ergebnisse.spitzenlast_kuehlung_kw:.1f} kW")

    with col3:
        st.markdown("**Gesamt**")
        st.metric("Gesamtenergie", f"{ergebnisse.gesamtenergiebedarf_kwh:.0f} kWh")
        st.metric("Pro m²", f"{kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a")
        st.metric("Fläche", f"{kennzahlen.gesamtflaeche_m2:.1f} m²")

    # Visualisierungen
    st.markdown("---")
    st.subheader("📈 Interaktive Visualisierungen")

    viz = ErgebnisVisualisierer()

    # Dashboard erstellen
    with st.spinner("Erstelle Visualisierungen..."):
        dashboard = viz.erstelle_dashboard(kennzahlen, result.sql_file)

    # Dashboard anzeigen
    st.plotly_chart(dashboard, use_container_width=True)

    # Monatliche Übersicht
    st.markdown("---")
    st.subheader("📅 Monatliche Übersicht")

    parser = EnergyPlusSQLParser(result.sql_file)
    monthly_df = parser.get_monthly_summary()

    if not monthly_df.empty:
        # Erstelle HTML-Tabelle (ohne pyarrow)
        html = "<table style='width:100%; border-collapse: collapse;'>"
        html += "<thead><tr style='background-color: #f0f2f6;'>"
        for col in monthly_df.columns:
            html += f"<th style='padding: 8px; border: 1px solid #ddd;'>{col}</th>"
        html += "</tr></thead><tbody>"

        for idx, row in monthly_df.iterrows():
            html += "<tr>"
            for col in monthly_df.columns:
                val = row[col]
                if col != 'Monat' and isinstance(val, (int, float)):
                    html += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{val:.1f}</td>"
                else:
                    html += f"<td style='padding: 8px; border: 1px solid #ddd;'>{val}</td>"
            html += "</tr>"
        html += "</tbody></table>"

        st.markdown(html, unsafe_allow_html=True)

        # Balkendiagramm
        import plotly.express as px
        fig = px.bar(
            monthly_df,
            x='Monat',
            y=['Heizung_kWh', 'Kuehlung_kWh', 'Beleuchtung_kWh', 'Geraete_kWh'],
            title='Monatlicher Energieverbrauch',
            labels={'value': 'Energie (kWh)', 'variable': 'Kategorie'},
            barmode='stack',
        )
        st.plotly_chart(fig, use_container_width=True)

    # Downloads
    st.markdown("---")
    st.subheader("💾 Downloads")

    col1, col2, col3 = st.columns(3)

    with col1:
        # IDF-Datei Download
        output_dir = st.session_state['simulation_output_dir']
        idf_file = output_dir / "building.idf"
        if idf_file.exists():
            with open(idf_file, 'r') as f:
                idf_content = f.read()
            st.download_button(
                label="📄 IDF-Modell herunterladen",
                data=idf_content,
                file_name="building.idf",
                mime="text/plain",
            )

    with col2:
        # Dashboard als HTML
        if dashboard:
            dashboard_html = dashboard.to_html()
            st.download_button(
                label="📊 Dashboard (HTML) herunterladen",
                data=dashboard_html,
                file_name="dashboard.html",
                mime="text/html",
            )

    with col3:
        # Monatsdaten als CSV
        if not monthly_df.empty:
            csv = monthly_df.to_csv(index=False)
            st.download_button(
                label="📅 Monatsdaten (CSV) herunterladen",
                data=csv,
                file_name="monthly_summary.csv",
                mime="text/csv",
            )

    # Vergleich mit Standards
    st.markdown("---")
    with st.expander("📐 Vergleich mit Energiestandards"):
        st.markdown("""
        ### Energieeffizienzklassen (vereinfacht nach EnEV)

        | Klasse | Energiekennzahl | Bewertung |
        |--------|----------------|-----------|
        | A+ | < 30 kWh/m²a | Exzellent (z.B. Passivhaus) |
        | A | 30-50 kWh/m²a | Sehr gut (KfW 40) |
        | B | 50-75 kWh/m²a | Gut (KfW 55) |
        | C | 75-100 kWh/m²a | Befriedigend (EnEV-Standard) |
        | D | 100-130 kWh/m²a | Ausreichend |
        | E | 130-160 kWh/m²a | Mangelhaft |
        | F | 160-200 kWh/m²a | Schlecht |
        | G | 200-250 kWh/m²a | Sehr schlecht |
        | H | > 250 kWh/m²a | Unsaniert |

        **Ihr Gebäude:** {:.1f} kWh/m²a = Klasse **{}**
        """.format(kennzahlen.energiekennzahl_kwh_m2a, kennzahlen.effizienzklasse))

except Exception as e:
    st.error(f"❌ Fehler beim Laden der Ergebnisse: {str(e)}")
    st.exception(e)
    st.stop()

# Navigation
st.markdown("---")
st.info("""
### 🔄 Neue Simulation

Möchten Sie eine neue Simulation durchführen?

1. Ändern Sie die **Geometrie** oder das **HVAC-System**
2. Starten Sie eine **neue Simulation**
3. Vergleichen Sie die Ergebnisse
""")

# Tipps
with st.expander("💡 Tipps zur Verbesserung der Energieeffizienz"):
    st.markdown("""
    ### Maßnahmen zur Energieeinsparung:

    **Gebäudehülle:**
    - Dämmung verbessern (Wand, Dach, Boden)
    - Fenster mit besserer Verglasung (U-Wert)
    - Wärmebrücken minimieren

    **Fenster:**
    - Optimaler Fensterflächenanteil: 20-40%
    - Südorientierung bevorzugen
    - Verschattung im Sommer berücksichtigen

    **HVAC-System:**
    - Effiziente Wärmepumpe statt Gasheizung
    - Wärmerückgewinnung in der Lüftung
    - Nachtabsenkung der Heizung

    **Nutzung:**
    - Solltemperaturen optimieren (20°C Heizen, 26°C Kühlen)
    - Innere Lasten reduzieren
    - Natürliche Lüftung nutzen
    """)
