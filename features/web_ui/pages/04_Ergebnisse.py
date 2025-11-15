"""Ergebnisse-Seite für Auswertung der Simulation."""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from features.auswertung.kpi_rechner import KennzahlenRechner, ErweiterteKennzahlen
from features.auswertung.visualisierung import ErgebnisVisualisierer
from features.auswertung.sql_parser import EnergyPlusSQLParser


# Helper functions for dict/object compatibility
def get_source(building_model):
    """Get source from building_model (handles dict or object)."""
    if not building_model:
        return None
    if isinstance(building_model, dict):
        return building_model.get('source')
    return getattr(building_model, 'source', None)


def get_attr_safe(obj, attr, default=None):
    """Safely get attribute from dict or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


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

if not result.success:
    st.error("❌ Die Simulation war nicht erfolgreich. Bitte überprüfen Sie die Simulation.")
    st.stop()

# Geometrie-Info holen (entweder von BuildingModel oder Legacy)
from core.building_model import get_building_model_from_session

building_model = get_building_model_from_session(st.session_state)
if building_model:
    # 5-Zone oder SimpleBox via BuildingModel
    geom_summary = get_attr_safe(building_model, 'geometry_summary', {})
    total_floor_area = geom_summary.get('total_floor_area', 0)
    source = get_source(building_model)
    is_five_zone = source in ["energieausweis", "oib_energieausweis"]
elif 'geometry' in st.session_state:
    # Legacy SimpleBox
    geometry = st.session_state['geometry']
    total_floor_area = geometry.total_floor_area
    is_five_zone = False
else:
    st.error("❌ Keine Geometrie-Daten gefunden. Bitte definieren Sie zuerst ein Gebäudemodell.")
    st.stop()

if total_floor_area == 0:
    st.error("❌ Ungültige Gebäudefläche (0 m²). Bitte überprüfen Sie das Gebäudemodell.")
    st.stop()

# Lade Ergebnisse
try:
    # HVAC-Config aus session_state holen
    hvac_config = st.session_state.get('hvac_config', {})

    # Wenn building_model ein dict ist, füge hvac_config hinzu
    if building_model and isinstance(building_model, dict):
        building_model['hvac_config'] = hvac_config
        building_model_with_hvac = building_model
    # Wenn building_model ein Pydantic-Objekt ist, erstelle ein dict mit allen Daten
    elif building_model:
        # Konvertiere BuildingModel zu dict und füge hvac_config hinzu
        building_model_dict = {
            'source': getattr(building_model, 'source', None),
            'geometry_summary': getattr(building_model, 'geometry_summary', {}),
            'hvac_config': hvac_config
        }
        building_model_with_hvac = building_model_dict
    else:
        building_model_with_hvac = None

    # KPIs berechnen (mit building_model für OIB-Metadaten inkl. hvac_config)
    rechner = KennzahlenRechner(total_floor_area, building_model=building_model_with_hvac)
    kennzahlen = rechner.berechne_kennzahlen(sql_file=result.sql_file)

    # Erweiterte Kennzahlen mit Tabular Reports berechnen
    try:
        erweiterte_kennzahlen = rechner.berechne_erweiterte_kennzahlen(sql_file=result.sql_file)
        has_tabular_reports = True
    except Exception:
        erweiterte_kennzahlen = None
        has_tabular_reports = False

    # Visualisierer erstellen
    viz = ErgebnisVisualisierer()

    # =============================================================================
    # TAB-STRUKTUR
    # =============================================================================

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎯 Übersicht",
        "📊 Energetische Auswertung",
        "🌡️ Behaglichkeit",
        "💰 Wirtschaftlichkeit",
        "🏗️ Zonenauswertung",
        "📋 Input Summary"
    ])

    # =============================================================================
    # TAB 1: ÜBERSICHT
    # =============================================================================
    with tab1:
        st.subheader("🎯 Energiekennzahlen auf einen Blick")

        # KPIs anzeigen
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
            st.markdown("### 💡 Bewertung")
            bewertung_text = kennzahlen.bewertung
            if klasse in ['A+', 'A', 'B']:
                st.success(bewertung_text)
            elif klasse in ['C', 'D']:
                st.info(bewertung_text)
            else:
                st.warning(bewertung_text)

        with col_komfort:
            st.markdown("### 🌡️ Thermischer Komfort")
            komfort = kennzahlen.thermische_behaglichkeit
            if komfort == "Gut":
                st.success(f"✅ {komfort}")
            elif komfort == "Akzeptabel":
                st.info(f"ℹ️ {komfort}")
            else:
                st.warning(f"⚠️ {komfort}")

        # Dashboard mit 4 Subplots
        st.markdown("---")
        st.markdown("### 📈 Dashboard")

        with st.spinner("Erstelle Dashboard..."):
            dashboard = viz.erstelle_dashboard(kennzahlen, result.sql_file)

        st.plotly_chart(dashboard, use_container_width=True)

        # Zusammenfassung
        st.markdown("---")
        st.markdown("### 📝 Zusammenfassung")

        ergebnisse = kennzahlen.ergebnisse

        zusammenfassung = f"""
        Ihr Gebäude hat die **Effizienzklasse {klasse}** mit einem Gesamtenergiebedarf von
        **{kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a**.

        Der **Heizbedarf** macht {ergebnisse.heizbedarf_kwh / ergebnisse.gesamtenergiebedarf_kwh * 100:.0f}%
        des Gesamtbedarfs aus ({ergebnisse.heizbedarf_kwh:.0f} kWh/Jahr), während der **Kühlbedarf**
        bei {ergebnisse.kuehlbedarf_kwh / ergebnisse.gesamtenergiebedarf_kwh * 100:.0f}%
        liegt ({ergebnisse.kuehlbedarf_kwh:.0f} kWh/Jahr).

        Die durchschnittliche **Raumtemperatur** beträgt {ergebnisse.mittlere_raumtemperatur_c:.1f}°C
        (Min: {ergebnisse.min_raumtemperatur_c:.1f}°C, Max: {ergebnisse.max_raumtemperatur_c:.1f}°C).
        """

        st.info(zusammenfassung)

        # Downloads
        st.markdown("---")
        st.markdown("### 💾 Downloads")

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
            st.info("💡 Mehr Export-Optionen in den anderen Tabs")

    # =============================================================================
    # TAB 2: ENERGETISCHE AUSWERTUNG
    # =============================================================================
    with tab2:
        st.subheader("📊 Detaillierte Energieanalyse")

        # SUB-TABS für bessere Organisation
        subtab1, subtab2, subtab3, subtab4 = st.tabs([
            "📊 Grundwerte",
            "🇦🇹 Energieausweis",
            "📈 Tabular Reports (Erweitert)",
            "📐 Standards & Tipps"
        ])

        ergebnisse = kennzahlen.ergebnisse

        # ===== SUB-TAB 1: GRUNDWERTE =====
        with subtab1:
            # Jahresbilanz
            st.markdown("### ⚡ Jahresbilanz")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("#### Heizung")
                st.metric("Gesamt", f"{ergebnisse.heizbedarf_kwh:.0f} kWh")
                st.metric("Spezifisch", f"{kennzahlen.heizkennzahl_kwh_m2a:.1f} kWh/m²a")
                st.metric("Spitzenlast", f"{ergebnisse.spitzenlast_heizung_kw:.1f} kW")

            with col2:
                st.markdown("#### Kühlung")
                st.metric("Gesamt", f"{ergebnisse.kuehlbedarf_kwh:.0f} kWh")
                st.metric("Spezifisch", f"{kennzahlen.kuehlkennzahl_kwh_m2a:.1f} kWh/m²a")
                st.metric("Spitzenlast", f"{ergebnisse.spitzenlast_kuehlung_kw:.1f} kW")

            with col3:
                st.markdown("#### Gesamt")
                st.metric("Gesamtenergie", f"{ergebnisse.gesamtenergiebedarf_kwh:.0f} kWh")
                st.metric("Pro m²", f"{kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a")
                st.metric("Fläche", f"{kennzahlen.gesamtflaeche_m2:.1f} m²")

            # Monatliche Übersicht
            st.markdown("---")
            st.markdown("### 📅 Monatliche Übersicht")

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
                st.markdown("")
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

                # CSV Download
                csv = monthly_df.to_csv(index=False)
                st.download_button(
                    label="📅 Monatsdaten als CSV herunterladen",
                    data=csv,
                    file_name="monthly_summary.csv",
                    mime="text/csv",
                )

        # ===== SUB-TAB 2: ENERGIEAUSWEIS =====
        with subtab2:
            st.markdown("### 🇦🇹 Energieausweis nach OIB RL6")
            st.caption("Kennzahlen nach OIB-Richtlinie 6 (März 2015) - Abschnitt 11")

            # Zeige verwendetes Heizsystem für PEB-Berechnung
            if hvac_config:
                heating_sys = hvac_config.get('heating_system') or hvac_config.get('type', 'k.A.')
                ventilation_sys = hvac_config.get('ventilation_system', 'k.A.')

                # Nur anzeigen wenn PEB berechnet wurde
                if kennzahlen.peb_kwh_m2a is not None:
                    st.info(f"""
                    **Verwendete Systeme für Kennzahlen-Berechnung:**
                    - 🔥 **Heizsystem:** {heating_sys} → PEB & CO₂-Berechnung
                    - 🌬️ **Lüftungssystem:** {ventilation_sys}
                    """)
                else:
                    st.warning(f"""
                    ⚠️ **PEB & CO₂ nicht berechnet**
                    - Heizsystem: {heating_sys}
                    - Bitte wählen Sie ein Heizsystem auf der **HVAC-Seite** für vollständige Kennzahlen
                    """)

            # EFFIZIENZKLASSE NACH OIB RL6 TABELLE 8
            st.markdown("#### 🏆 Energieeffizienzklasse")

            col_klasse1, col_klasse2 = st.columns([1, 2])

            with col_klasse1:
                # OIB-Effizienzklasse mit Farbe
                klasse = kennzahlen.oib_effizienzklasse
                color_map = {
                    'A++': '#00b050', 'A+': '#92d050', 'A': '#c6e0b4',
                    'B': '#ffff00', 'C': '#ffc000',
                    'D': '#ff9900', 'E': '#ff6600',
                    'F': '#ff0000', 'G': '#c00000', 'k.A.': '#808080'
                }
                color = color_map.get(klasse, '#808080')

                st.markdown(f"""
                <div style='background-color: {color}; padding: 30px; border-radius: 15px; text-align: center;'>
                    <h1 style='margin: 0; color: white; font-size: 48px;'>{klasse}</h1>
                    <p style='margin: 0; color: white; font-size: 14px;'>OIB RL6 Klasse</p>
                </div>
                """, unsafe_allow_html=True)

            with col_klasse2:
                st.markdown("**Klassifizierung nach OIB RL6 Tabelle 8:**")
                peb_str = f"{kennzahlen.peb_kwh_m2a:.1f}" if kennzahlen.peb_kwh_m2a is not None else 'k.A.'
                co2_str = f"{kennzahlen.co2_kg_m2a:.1f}" if kennzahlen.co2_kg_m2a is not None else 'k.A.'
                f_gee_str = f"{kennzahlen.f_gee:.2f}" if kennzahlen.f_gee is not None else 'k.A.'

                st.markdown(f"""
                - **Primär:** HWB = {kennzahlen.hwb_kwh_m2a:.1f} kWh/m²a
                - **PEB:** {peb_str} kWh/m²a
                - **CO₂:** {co2_str} kg/m²a
                - **f<sub>GEE</sub>:** {f_gee_str}

                ℹ️ *Bei fehlenden Werten (PEB, CO₂, f<sub>GEE</sub>) erfolgt Klassifizierung ausschließlich nach HWB.*
                """, unsafe_allow_html=True)

            st.markdown("---")

            # KENNZAHLEN NACH OIB RL6 ABSCHNITT 11
            st.markdown("#### 📊 Energiekennzahlen (OIB RL6 § 11)")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    "HWB",
                    f"{kennzahlen.hwb_kwh_m2a:.1f}",
                    help="Heizwärmebedarf [kWh/m²a] - Wärmemenge für normierte Raumtemperatur (OIB RL6 § 11)"
                )
                st.caption("kWh/m²a")

            with col2:
                heb_val = f"{kennzahlen.heb_kwh_m2a:.1f}" if kennzahlen.heb_kwh_m2a is not None else "k.A."
                st.metric(
                    "HEB",
                    heb_val,
                    help="Heizenergiebedarf [kWh/m²a] - HWB + Verluste der gebäudetechnischen Systeme (OIB RL6 § 11)"
                )
                st.caption("kWh/m²a")

            with col3:
                wwwb_val = f"{kennzahlen.wwwb_kwh_m2a:.1f}" if kennzahlen.wwwb_kwh_m2a is not None else "k.A."
                st.metric(
                    "WWWB",
                    wwwb_val,
                    help="Warmwasserwärmebedarf [kWh/m²a] - Warmwasserbereitung (OIB RL6 § 11)"
                )
                st.caption("kWh/m²a")

            with col4:
                st.metric(
                    "EEB",
                    f"{kennzahlen.eeb_kwh_m2a:.1f}",
                    help="Endenergiebedarf [kWh/m²a] - HEB + Warmwasser - Erträge (OIB RL6 § 11)"
                )
                st.caption("kWh/m²a")

            with col5:
                peb_val = f"{kennzahlen.peb_kwh_m2a:.1f}" if kennzahlen.peb_kwh_m2a is not None else "k.A."
                st.metric(
                    "PEB",
                    peb_val,
                    help="Primärenergiebedarf [kWh/m²a] - EEB mit Primärenergiefaktoren (OIB RL6 § 11)"
                )
                st.caption("kWh/m²a")

            st.markdown("")
            col6, col7, col8 = st.columns(3)

            with col6:
                f_gee_val = f"{kennzahlen.f_gee:.2f}" if kennzahlen.f_gee is not None else "k.A."
                st.metric(
                    "f_GEE",
                    f_gee_val,
                    help="Gesamtenergieeffizienz-Faktor [-] - Dimensionsloses Verhältnis (OIB RL6 § 11). Anforderung 2020: ≤ 0,85"
                )
                st.caption("[-]")

            with col7:
                co2_val = f"{kennzahlen.co2_kg_m2a:.1f}" if kennzahlen.co2_kg_m2a is not None else "k.A."
                st.metric(
                    "CO₂-Emissionen",
                    co2_val,
                    help="CO₂-Emissionen [kg/m²a] - Treibhausgasemissionen"
                )
                st.caption("kg/m²a")

            with col8:
                # Kühlbedarf (nicht in OIB RL6 § 11, aber relevant)
                st.metric(
                    "Kühlbedarf",
                    f"{kennzahlen.kuehlkennzahl_kwh_m2a:.1f}",
                    help="Kühlenergiebedarf [kWh/m²a] - Aus EnergyPlus-Simulation"
                )
                st.caption("kWh/m²a")

            st.markdown("---")

            # GEBÄUDEKENNDATEN NACH OIB RL6 § 12.2
            st.markdown("#### 🏗️ Gebäudekenndaten (OIB RL6 § 12.2 Pflichtangaben)")

            col_geo1, col_geo2, col_geo3 = st.columns(3)

            with col_geo1:
                st.markdown("**Geometrische Kennwerte**")
                if kennzahlen.kompaktheit_av:
                    st.metric("Kompaktheit A/V", f"{kennzahlen.kompaktheit_av:.3f} m⁻¹",
                             help="A/V = Gebäude-Hüllfläche / Brutto-Volumen")
                else:
                    st.metric("Kompaktheit A/V", "k.A.", help="Nicht verfügbar")

                if kennzahlen.char_laenge_lc:
                    st.metric("Charakteristische Länge ℓc", f"{kennzahlen.char_laenge_lc:.2f} m",
                             help="ℓc = V / A - Maß für Kompaktheit")
                else:
                    st.metric("Charakteristische Länge ℓc", "k.A.", help="Nicht verfügbar")

                if kennzahlen.mittlerer_u_wert:
                    st.metric("Mittlerer U-Wert Ū", f"{kennzahlen.mittlerer_u_wert:.3f} W/m²K",
                             help="Flächengewichteter U-Wert der Gebäudehülle")
                else:
                    st.metric("Mittlerer U-Wert Ū", "k.A.", help="Nicht verfügbar")

            with col_geo2:
                st.markdown("**Wärmebilanz**")
                st.metric("QT - Transmissionsverluste", f"{kennzahlen.transmissionswaermeverluste_kwh:.0f} kWh/a",
                         help="Wärmeverluste durch die Gebäudehülle")
                st.metric("QV - Lüftungsverluste", f"{kennzahlen.lueftungswaermeverluste_kwh:.0f} kWh/a",
                         help="Wärmeverluste durch Infiltration und Lüftung")
                st.metric("Solare Gewinne", f"{kennzahlen.solare_waermegewinne_kwh:.0f} kWh/a",
                         help="Wärmegewinne durch Sonneneinstrahlung")

            with col_geo3:
                st.markdown("**Auslegungslasten**")
                st.metric("Heizlast", f"{kennzahlen.heizlast_w_m2:.1f} W/m²",
                         help="Spezifische Heizlast für Dimensionierung")
                st.metric("Kühllast", f"{kennzahlen.kuhllast_w_m2:.1f} W/m²",
                         help="Spezifische Kühllast für Dimensionierung")
                st.metric("Innere Wärmegewinne", f"{kennzahlen.innere_waermegewinne_kwh:.0f} kWh/a",
                         help="Wärmegewinne durch Beleuchtung, Geräte, Personen")

            st.markdown("---")

            # NIEDRIGSTENERGIEGEBÄUDE-ANFORDERUNGEN (§ 13)
            st.markdown("#### 🎯 Niedrigstenergiegebäude-Anforderungen (Ab 2020)")

            if kennzahlen.char_laenge_lc:
                lc = kennzahlen.char_laenge_lc
                hwb_grenzwert = 14 * (1 + 3.0 / lc)
                f_gee_grenzwert = 0.85

                col_nzeb1, col_nzeb2 = st.columns(2)

                with col_nzeb1:
                    hwb_erfuellt = kennzahlen.hwb_kwh_m2a <= hwb_grenzwert
                    status_hwb = "✅" if hwb_erfuellt else "❌"
                    st.markdown(f"""
                    **HWB<sub>Ref,RK</sub>-Anforderung:**
                    - Grenzwert: **{hwb_grenzwert:.1f} kWh/m²a** (14 × (1 + 3/ℓ<sub>c</sub>))
                    - Ist-Wert: **{kennzahlen.hwb_kwh_m2a:.1f} kWh/m²a**
                    - Status: {status_hwb} {"**Erfüllt**" if hwb_erfuellt else "**Nicht erfüllt**"}
                    """, unsafe_allow_html=True)

                with col_nzeb2:
                    if kennzahlen.f_gee:
                        f_gee_erfuellt = kennzahlen.f_gee <= f_gee_grenzwert
                        status_gee = "✅" if f_gee_erfuellt else "❌"
                        st.markdown(f"""
                        **f<sub>GEE</sub>-Anforderung:**
                        - Grenzwert: **≤ {f_gee_grenzwert:.2f}**
                        - Ist-Wert: **{kennzahlen.f_gee:.2f}**
                        - Status: {status_gee} {"**Erfüllt**" if f_gee_erfuellt else "**Nicht erfüllt**"}
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        **f<sub>GEE</sub>-Anforderung:**
                        - Grenzwert: **≤ 0,85**
                        - Ist-Wert: **k.A.**
                        - Status: ℹ️ Nicht berechenbar (Primärenergiefaktoren fehlen)
                        """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ Niedrigstenergiegebäude-Prüfung nicht möglich - charakteristische Länge ℓc nicht verfügbar.")

            st.info("""
            **Hinweis:** Kennzahlen mit "k.A." (keine Angabe) sind in der aktuellen Simulation nicht verfügbar,
            da dafür zusätzliche Systemkomponenten (z.B. Warmwasserbereitung) oder Konfigurationen
            (z.B. Primärenergiefaktoren, Emissionsfaktoren) erforderlich wären.

            Die **Energieeffizienzklasse** wird bei fehlenden Werten (PEB, CO₂, f_GEE) ausschließlich
            nach **HWB** (Heizwärmebedarf) gemäß OIB RL6 Tabelle 8 bestimmt.
            """)

        # ===== SUB-TAB 3: TABULAR REPORTS =====
        with subtab3:
            st.markdown("### 📈 Tabular Reports - Erweiterte Auswertung")
            st.caption("Vorgefertigte EnergyPlus Summary Reports (aus SQL-Datenbank)")

            if not has_tabular_reports or erweiterte_kennzahlen is None:
                st.warning("""
                ⚠️ **Tabular Reports nicht verfügbar**

                Die erweiterten Tabular Reports konnten nicht geladen werden.
                Dies kann passieren wenn:
                - Die SQL-Datenbank nicht vollständig ist
                - Die EnergyPlus Output:Table:SummaryReports nicht konfiguriert wurden
                """)
            else:
                # Zeige Übersicht
                st.info("""
                **Was sind Tabular Reports?**

                EnergyPlus erstellt automatisch vorgefertigte Summary Reports in der SQL-Datenbank.
                Diese Reports enthalten bereits aggregierte Metriken ohne dass Zeitreihen manuell
                summiert werden müssen - ideal für schnelle Analysen!
                """)

                end_uses = erweiterte_kennzahlen.end_uses
                site_source = erweiterte_kennzahlen.site_source_energy
                hvac_sizing = erweiterte_kennzahlen.hvac_sizing
                envelope = erweiterte_kennzahlen.envelope

                # ===== END USE BREAKDOWN =====
                if end_uses:
                    st.markdown("---")
                    st.markdown("#### 🔌 End Use Breakdown (Verbrauchsaufteilung)")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Heizung", f"{end_uses.heating_kwh:.0f} kWh",
                                 help="Heizenergiebedarf aus Tabular Reports")
                        st.caption(f"{end_uses.heating_kwh / total_floor_area:.1f} kWh/m²")

                    with col2:
                        st.metric("Kühlung", f"{end_uses.cooling_kwh:.0f} kWh",
                                 help="Kühlenergiebedarf aus Tabular Reports")
                        st.caption(f"{end_uses.cooling_kwh / total_floor_area:.1f} kWh/m²")

                    with col3:
                        st.metric("Beleuchtung", f"{end_uses.interior_lighting_kwh:.0f} kWh",
                                 help="Beleuchtungsenergie aus Tabular Reports")
                        st.caption(f"{end_uses.interior_lighting_kwh / total_floor_area:.1f} kWh/m²")

                    with col4:
                        st.metric("Geräte", f"{end_uses.interior_equipment_kwh:.0f} kWh",
                                 help="Geräteenergie aus Tabular Reports")
                        st.caption(f"{end_uses.interior_equipment_kwh / total_floor_area:.1f} kWh/m²")

                    # Weitere Kategorien (falls vorhanden)
                    if end_uses.fans_kwh > 0 or end_uses.pumps_kwh > 0:
                        st.markdown("")
                        col5, col6, col7 = st.columns(3)

                        with col5:
                            if end_uses.fans_kwh > 0:
                                st.metric("Ventilatoren", f"{end_uses.fans_kwh:.0f} kWh")
                                st.caption(f"{end_uses.fans_kwh / total_floor_area:.1f} kWh/m²")

                        with col6:
                            if end_uses.pumps_kwh > 0:
                                st.metric("Pumpen", f"{end_uses.pumps_kwh:.0f} kWh")
                                st.caption(f"{end_uses.pumps_kwh / total_floor_area:.1f} kWh/m²")

                        with col7:
                            other = end_uses.other_kwh
                            if other > 0:
                                st.metric("Sonstiges", f"{other:.0f} kWh")
                                st.caption(f"{other / total_floor_area:.1f} kWh/m²")

                    # End Use Chart
                    st.markdown("")
                    end_use_chart = viz.erstelle_detailliertes_end_use_chart(end_uses)
                    st.plotly_chart(end_use_chart, use_container_width=True)

                    # Energieträger-Aufschlüsselung
                    st.markdown("")
                    col_e1, col_e2, col_e3 = st.columns(3)

                    with col_e1:
                        st.metric("Strom gesamt", f"{end_uses.electricity_kwh:.0f} kWh",
                                 help="Gesamter Stromverbrauch")
                        st.caption(f"{end_uses.electricity_kwh / total_floor_area:.1f} kWh/m²")

                    with col_e2:
                        st.metric("Gas gesamt", f"{end_uses.natural_gas_kwh:.0f} kWh",
                                 help="Gesamter Gasverbrauch")
                        st.caption(f"{end_uses.natural_gas_kwh / total_floor_area:.1f} kWh/m²")

                    with col_e3:
                        st.metric("Gesamt", f"{end_uses.total_kwh:.0f} kWh",
                                 help="Gesamtenergieverbrauch (alle Quellen)")
                        st.caption(f"{end_uses.total_kwh / total_floor_area:.1f} kWh/m²")

                # ===== SITE VS SOURCE ENERGY =====
                if site_source:
                    st.markdown("---")
                    st.markdown("#### ⚡ Site vs. Source Energy (Primärenergie)")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Site Energy (Endenergie)**")
                        st.metric("Gesamt", f"{site_source.total_site_energy_kwh:.0f} kWh/a")
                        st.metric("Spezifisch", f"{site_source.site_energy_per_m2_kwh:.1f} kWh/m²a")

                    with col2:
                        st.markdown("**Source Energy (Primärenergie)**")
                        st.metric("Gesamt", f"{site_source.total_source_energy_kwh:.0f} kWh/a")
                        st.metric("Spezifisch", f"{site_source.source_energy_per_m2_mj / 3.6:.1f} kWh/m²a")

                    st.markdown("")
                    site_source_chart = viz.erstelle_site_source_energy_chart(site_source)
                    st.plotly_chart(site_source_chart, use_container_width=True)

                    st.info("""
                    **Site Energy** = Endenergie am Gebäude (was aus dem Netz kommt)
                    **Source Energy** = Primärenergie (inkl. Verluste bei Erzeugung & Transport)

                    Der Primärenergiefaktor berücksichtigt den Energieaufwand für
                    die Bereitstellung der Energie.
                    """)

                # ===== HVAC DESIGN LOADS =====
                if hvac_sizing:
                    st.markdown("---")
                    st.markdown("#### ❄️ HVAC Design Loads (Auslegungslasten)")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Heizung**")
                        st.metric("Heizlast", f"{hvac_sizing.heating_design_load_kw:.1f} kW")
                        st.metric("Spezifisch", f"{hvac_sizing.heating_design_load_per_area_w_m2:.1f} W/m²")
                        st.caption(f"Auslegungstag: {hvac_sizing.heating_design_day}")

                    with col2:
                        st.markdown("**Kühlung**")
                        st.metric("Kühllast", f"{hvac_sizing.cooling_design_load_kw:.1f} kW")
                        st.metric("Spezifisch", f"{hvac_sizing.cooling_design_load_per_area_w_m2:.1f} W/m²")
                        st.caption(f"Auslegungstag: {hvac_sizing.cooling_design_day}")

                    st.markdown("")
                    hvac_chart = viz.erstelle_hvac_design_loads_chart(hvac_sizing, total_floor_area)
                    st.plotly_chart(hvac_chart, use_container_width=True)

                    st.info("""
                    **Design Loads** = Auslegungslasten für die HVAC-Dimensionierung

                    Diese Werte zeigen die maximal benötigte Heiz-/Kühlleistung an den
                    extremsten Wetter-Tagen (Design Days) und dienen zur Auslegung der
                    HVAC-Anlagen.
                    """)

                # ===== ENVELOPE PERFORMANCE =====
                if envelope:
                    st.markdown("---")
                    st.markdown("#### 🏗️ Envelope Performance (Gebäudehülle)")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Wandfläche", f"{envelope.gross_wall_area_m2:.1f} m²")
                        if envelope.wall_u_value:
                            st.caption(f"U-Wert: {envelope.wall_u_value:.3f} W/m²K")

                    with col2:
                        st.metric("Fensterfläche", f"{envelope.gross_window_area_m2:.1f} m²")
                        if envelope.window_u_value:
                            st.caption(f"U-Wert: {envelope.window_u_value:.3f} W/m²K")

                    with col3:
                        st.metric("Dachfläche", f"{envelope.gross_roof_area_m2:.1f} m²")
                        if envelope.roof_u_value:
                            st.caption(f"U-Wert: {envelope.roof_u_value:.3f} W/m²K")

                    st.markdown("")
                    if envelope.window_wall_ratio > 0:
                        st.metric("Window-Wall-Ratio (WWR)",
                                 f"{envelope.window_wall_ratio:.1%}",
                                 help="Verhältnis Fensterfläche zu Gesamtfläche (Fenster + Wand)")

                # ===== ERWEITERTE ÜBERSICHT =====
                st.markdown("---")
                st.markdown("#### 📊 Erweiterte Dashboard-Ansicht")

                if st.button("🚀 Erweiterte Übersicht anzeigen", key="show_extended_dashboard"):
                    with st.spinner("Erstelle erweitertes Dashboard..."):
                        extended_dashboard = viz.erstelle_erweiterte_uebersicht(
                            erweiterte_kennzahlen,
                            result.sql_file
                        )
                    st.plotly_chart(extended_dashboard, use_container_width=True)

        # ===== SUB-TAB 4: STANDARDS & TIPPS =====
        with subtab4:
            st.markdown("### 📐 Vergleich mit Energiestandards")

            st.markdown("""
            #### Energieeffizienzklassen (vereinfacht nach EnEV)

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
            """)

            st.success(f"**Ihr Gebäude:** {kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a = Klasse **{kennzahlen.effizienzklasse}**")

            # Tipps
            st.markdown("---")
            st.markdown("### 💡 Tipps zur Verbesserung der Energieeffizienz")

            col_tip1, col_tip2 = st.columns(2)

            with col_tip1:
                st.markdown("""
                **🏗️ Gebäudehülle:**
                - Dämmung verbessern (Wand, Dach, Boden)
                - Fenster mit besserer Verglasung (niedrigerer U-Wert)
                - Wärmebrücken minimieren

                **🪟 Fenster:**
                - Optimaler Fensterflächenanteil: 20-40%
                - Südorientierung bevorzugen
                - Verschattung im Sommer berücksichtigen
                """)

            with col_tip2:
                st.markdown("""
                **❄️ HVAC-System:**
                - Effiziente Wärmepumpe statt Gasheizung
                - Wärmerückgewinnung in der Lüftung
                - Nachtabsenkung der Heizung

                **👤 Nutzung:**
                - Solltemperaturen optimieren (20°C Heizen, 26°C Kühlen)
                - Innere Lasten reduzieren
                - Natürliche Lüftung nutzen
                """)

    # =============================================================================
    # TAB 3: BEHAGLICHKEIT
    # =============================================================================
    with tab3:
        st.subheader("🌡️ Thermische Behaglichkeit")

        st.info("""
        **Interaktive Temperaturanalyse**: Navigieren Sie durch das Jahr und analysieren Sie
        den Temperaturverlauf für beliebige Zeiträume.
        """)

        # Controls für Zeitraum-Auswahl
        col1, col2 = st.columns([2, 1])

        # Verwende gespeicherten Wert falls vorhanden (von Schnell-Navigation)
        default_start_tag = st.session_state.get('temp_start_tag', 1)

        with col1:
            start_tag = st.slider(
                "Start-Tag des Jahres",
                min_value=1,
                max_value=365,
                value=default_start_tag,
                step=1,
                help="Wählen Sie den ersten Tag des anzuzeigenden Zeitraums (1 = 1. Januar)"
            )

            # Update session state wenn Slider geändert wurde
            st.session_state['temp_start_tag'] = start_tag

        with col2:
            anzahl_tage = st.select_slider(
                "Anzahl Tage",
                options=[1, 3, 7, 14, 30, 60, 90],
                value=7,
                help="Anzahl der anzuzeigenden Tage"
            )

        # Erstelle interaktive Temperaturkurve
        temp_fig = viz.erstelle_interaktive_temperaturkurve(
            sql_file=result.sql_file,
            start_tag=start_tag,
            anzahl_tage=anzahl_tage,
            titel="Raumtemperaturverlauf"
        )

        st.plotly_chart(temp_fig, use_container_width=True)

        # Schnell-Navigation
        st.markdown("**📅 Schnell-Navigation:**")
        quick_nav_cols = st.columns(6)

        with quick_nav_cols[0]:
            if st.button("Januar (Woche 1)", key="jan_w1"):
                st.session_state['temp_start_tag'] = 1
                st.rerun()

        with quick_nav_cols[1]:
            if st.button("April (Woche 1)", key="apr_w1"):
                st.session_state['temp_start_tag'] = 91
                st.rerun()

        with quick_nav_cols[2]:
            if st.button("Juli (Woche 1)", key="jul_w1"):
                st.session_state['temp_start_tag'] = 182
                st.rerun()

        with quick_nav_cols[3]:
            if st.button("Oktober (Woche 1)", key="okt_w1"):
                st.session_state['temp_start_tag'] = 274
                st.rerun()

        with quick_nav_cols[4]:
            if st.button("Heißeste Woche", key="hot_week"):
                # TODO: Finde heißeste Woche automatisch
                st.info("Feature kommt bald!")

        with quick_nav_cols[5]:
            if st.button("Kälteste Woche", key="cold_week"):
                # TODO: Finde kälteste Woche automatisch
                st.info("Feature kommt bald!")

        # Behaglichkeitsstatistiken
        st.markdown("---")
        st.markdown("### 📊 Behaglichkeitsstatistiken")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Durchschnittstemperatur",
                f"{ergebnisse.mittlere_raumtemperatur_c:.1f}°C",
                help="Durchschnittliche Raumtemperatur über das gesamte Jahr"
            )

        with col2:
            st.metric(
                "Minimale Temperatur",
                f"{ergebnisse.min_raumtemperatur_c:.1f}°C",
                help="Niedrigste gemessene Raumtemperatur"
            )

        with col3:
            st.metric(
                "Maximale Temperatur",
                f"{ergebnisse.max_raumtemperatur_c:.1f}°C",
                help="Höchste gemessene Raumtemperatur"
            )

        st.markdown("---")
        st.info("""
        **Komfortbereich**: 20-26°C (grün markiert im Diagramm)

        **Erläuterung**:
        - **< 20°C**: Heizung aktiv, um Solltemperatur zu erreichen
        - **20-26°C**: Komfortbereich, keine Heizung/Kühlung erforderlich
        - **> 26°C**: Kühlung aktiv, um Solltemperatur zu halten
        """)

        # Zukünftige Features
        with st.expander("🚀 Geplante Features (zukünftig)"):
            st.markdown("""
            - **Komfortindex**: Prozentsatz der Zeit im Komfortbereich
            - **Überhitzungsstunden**: Anzahl Stunden > 26°C
            - **PMV/PPD**: Predicted Mean Vote & Percentage Dissatisfied
            - **Heatmap**: Temperaturverteilung über Tage/Monate
            - **CO₂-Konzentration**: Luftqualitätsanalyse
            - **Luftfeuchte**: Relative Luftfeuchtigkeit
            """)

    # =============================================================================
    # TAB 4: WIRTSCHAFTLICHKEIT
    # =============================================================================
    with tab4:
        st.subheader("💰 Wirtschaftlichkeitsanalyse")

        st.info("""
        **Hinweis**: Die Wirtschaftlichkeitsanalyse wird in einer zukünftigen Version implementiert.
        """)

        # Platzhalter für Kostenrechner
        st.markdown("### 💵 Energiekosten (Platzhalter)")

        st.markdown("""
        Hier werden zukünftig folgende Features verfügbar sein:

        - **Kostenrechner**: Eingabe von Energiepreisen (Strom, Gas, Fernwärme)
        - **Jahreskosten**: Berechnung basierend auf simuliertem Verbrauch
        - **Vergleichsszenarien**: Was-wäre-wenn-Analysen
        - **Amortisationsrechnung**: ROI für Effizienzmaßnahmen
        - **Fördermittel**: Hinweise zu KfW, BAFA, etc.
        """)

        # Einfacher Kostenrechner (MVP)
        st.markdown("---")
        st.markdown("### 🧮 Einfacher Kostenrechner (Vorschau)")

        col1, col2 = st.columns(2)

        with col1:
            strompreis = st.number_input(
                "Strompreis [€/kWh]",
                min_value=0.0,
                max_value=1.0,
                value=0.30,
                step=0.01,
                help="Durchschnittlicher Strompreis in Deutschland: ~0.30 €/kWh"
            )

        with col2:
            gaspreis = st.number_input(
                "Gaspreis [€/kWh]",
                min_value=0.0,
                max_value=1.0,
                value=0.08,
                step=0.01,
                help="Durchschnittlicher Gaspreis in Deutschland: ~0.08 €/kWh"
            )

        # Einfache Kostenberechnung (Annahme: Heizung = Gas, Kühlung+Rest = Strom)
        heizkosten = ergebnisse.heizbedarf_kwh * gaspreis
        kuehlung_strom = ergebnisse.kuehlbedarf_kwh * strompreis
        beleuchtung_strom = ergebnisse.beleuchtung_kwh * strompreis
        geraete_strom = ergebnisse.geraete_kwh * strompreis

        gesamtkosten = heizkosten + kuehlung_strom + beleuchtung_strom + geraete_strom

        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Heizkosten", f"{heizkosten:.0f} €/Jahr")
            st.caption(f"{heizkosten / kennzahlen.gesamtflaeche_m2:.2f} €/m²a")

        with col2:
            st.metric("Stromkosten", f"{kuehlung_strom + beleuchtung_strom + geraete_strom:.0f} €/Jahr")
            st.caption(f"{(kuehlung_strom + beleuchtung_strom + geraete_strom) / kennzahlen.gesamtflaeche_m2:.2f} €/m²a")

        with col3:
            st.metric("Gesamtkosten", f"{gesamtkosten:.0f} €/Jahr", delta=None)
            st.caption(f"{gesamtkosten / kennzahlen.gesamtflaeche_m2:.2f} €/m²a")

        st.warning("""
        ⚠️ **Vereinfachte Berechnung**: Diese Kostenanalyse ist stark vereinfacht und dient nur zur groben Orientierung.
        Faktoren wie Grundgebühren, Steuern, und unterschiedliche Tarife werden nicht berücksichtigt.
        """)

    # =============================================================================
    # TAB 5: ZONENAUSWERTUNG
    # =============================================================================
    with tab5:
        st.subheader("🏗️ Zonenauswertung")

        if not is_five_zone:
            st.warning("""
            **SimpleBox-Modell**: Die Zonenauswertung ist nur für **5-Zone-Modelle** verfügbar.

            Erstellen Sie ein Gebäudemodell über den **Energieausweis-Tab** auf der Geometrie-Seite,
            um die Zonenauswertung nutzen zu können.
            """)

            st.info("""
            **Was ist ein 5-Zone-Modell?**

            Ein 5-Zone-Modell unterteilt das Gebäude in:
            - **4 Perimeter-Zonen** (Nord, Ost, Süd, West) an der Außenwand
            - **1 Kern-Zone** im Inneren ohne Außenwandkontakt

            Dies ermöglicht eine detailliertere Analyse der Energiebedarfe nach Orientierung
            und Sonneneinstrahlung.
            """)
        else:
            # 5-Zone-Modell: Zonale Daten extrahieren
            try:
                from features.auswertung.tabular_reports import TabularReportParser

                parser = TabularReportParser(result.sql_file)
                zonal = parser.get_zonal_comparison()

                if not zonal.zones:
                    st.warning("Keine zonalen Daten verfügbar. Simulation könnte fehlgeschlagen sein.")
                else:
                    st.success(f"✅ **{len(zonal.zones)} Zonen** erfolgreich analysiert!")

                    # Zonaler Vergleich Dashboard
                    st.markdown("### 📊 Zonaler Vergleich: Nord/Ost/Süd/West/Kern")

                    st.info("""
                    **Orientierungseffekte sichtbar machen**:
                    - **Solare Gewinne** variieren stark nach Orientierung
                    - **Temperaturen** zeigen Unterschiede zwischen Zonen
                    - **Heiz-/Kühllasten** können zonenspezifisch analysiert werden
                    """)

                    # Hauptdashboard
                    fig_zonal = viz.erstelle_zonalen_vergleich(zonal)
                    st.plotly_chart(fig_zonal, use_container_width=True)

                    # Detaillierte Zonen-Metriken
                    st.markdown("---")
                    st.markdown("### 📋 Detaillierte Zonen-Metriken")

                    # Tabelle mit allen Zonen
                    zone_data = []
                    for zone_name, zone in zonal.zones.items():
                        zone_data.append({
                            'Orientierung': zone.orientation,
                            'Ø Temp. [°C]': f"{zone.avg_temperature_c:.1f}",
                            'Min/Max [°C]': f"{zone.min_temperature_c:.1f} / {zone.max_temperature_c:.1f}",
                            'Heizung [kWh]': f"{zone.heating_kwh:.0f}",
                            'Kühlung [kWh]': f"{zone.cooling_kwh:.0f}",
                            'Solar [kWh]': f"{zone.solar_gains_kwh:.0f}",
                            'Innere Gewinne [kWh]': f"{zone.internal_gains_kwh:.0f}",
                        })

                    # Sortiere nach Orientierung
                    orientations_order = ['North', 'East', 'South', 'West', 'Core']
                    zone_data.sort(key=lambda x: orientations_order.index(x['Orientierung']) if x['Orientierung'] in orientations_order else 999)

                    import pandas as pd
                    df_zones = pd.DataFrame(zone_data)
                    st.dataframe(df_zones, use_container_width=True, hide_index=True)

                    # Erkenntnisse
                    st.markdown("---")
                    st.markdown("### 💡 Erkenntnisse aus zonaler Auswertung")

                    # Finde Zone mit höchsten solaren Gewinnen
                    perimeter_zones = [z for z in zonal.zones.values() if z.orientation != 'Core']
                    if perimeter_zones:
                        max_solar_zone = max(perimeter_zones, key=lambda z: z.solar_gains_kwh)
                        min_solar_zone = min(perimeter_zones, key=lambda z: z.solar_gains_kwh)

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric(
                                "Höchste Solare Gewinne",
                                f"{max_solar_zone.orientation}",
                                f"{max_solar_zone.solar_gains_kwh:.0f} kWh"
                            )

                        with col2:
                            st.metric(
                                "Niedrigste Solare Gewinne",
                                f"{min_solar_zone.orientation}",
                                f"{min_solar_zone.solar_gains_kwh:.0f} kWh"
                            )

                        with col3:
                            delta = max_solar_zone.solar_gains_kwh - min_solar_zone.solar_gains_kwh
                            st.metric(
                                "Unterschied",
                                f"{delta:.0f} kWh",
                                f"{delta / max_solar_zone.solar_gains_kwh * 100:.0f}%"
                            )

                    # Solare Gewinne Detail-Chart
                    st.markdown("### ☀️ Solare Gewinne nach Orientierung")
                    fig_solar = viz.erstelle_zonale_solar_gewinne_chart(zonal)
                    st.plotly_chart(fig_solar, use_container_width=True)

                    st.info("""
                    **Interpretation**:
                    - Hohe solare Gewinne reduzieren den Heizbedarf (kostenlose Wärme!)
                    - Aber: Erhöhen potentiell den Kühlbedarf im Sommer
                    - Optimale Fensterauslegung berücksichtigt Orientierung
                    """)

            except Exception as e:
                st.error(f"Fehler beim Laden der zonalen Daten: {e}")
                st.info("Tipp: Stellen Sie sicher, dass die Simulation erfolgreich war.")

    # =============================================================================
    # TAB 6: INPUT SUMMARY
    # =============================================================================
    with tab6:
        st.subheader("📋 Input Summary - All Parameters Used")

        st.markdown("""
        This tab shows all input parameters that were used for this simulation.
        Use this for documentation and to verify your simulation setup.
        """)

        # Section 1: Geometry
        st.markdown("---")
        st.markdown("### 🏗️ Geometry")

        building_model = st.session_state.get('building_model')
        if building_model:
            geom_summary = get_attr_safe(building_model, 'geometry_summary', {})
            source = get_source(building_model)
            if source in ["energieausweis", "oib_energieausweis"]:
                model_type = "OIB RL6 12.2" if source == "oib_energieausweis" else "Energieausweis"
                st.markdown(f"""
                **Source:** 5-Zone Model ({model_type})
                **Building Type:** {get_attr_safe(building_model, 'gebaeudetyp', 'N/A')}
                **Zones:** {get_attr_safe(building_model, 'num_zones', 'N/A')}
                **Floor Area:** {geom_summary.get('total_floor_area', 0):.1f} m²
                **Floors:** {geom_summary.get('num_floors', 0)}
                **Dimensions:** {geom_summary.get('length', 0):.2f}m × {geom_summary.get('width', 0):.2f}m × {geom_summary.get('height', 0):.2f}m
                """)
            else:
                st.markdown(f"""
                **Source:** SimpleBox
                **Dimensions:** {geom_summary.get('length', 0):.2f}m × {geom_summary.get('width', 0):.2f}m × {geom_summary.get('height', 0):.2f}m
                **Floor Area:** {geom_summary.get('total_floor_area', 0):.1f} m²
                **Floors:** {geom_summary.get('num_floors', 1)}
                **WWR:** {geom_summary.get('window_wall_ratio', 0.3):.1%}
                **Orientation:** {geom_summary.get('orientation', 0):.0f}°
                """)
        elif 'geometry' in st.session_state:
            geometry = st.session_state['geometry']
            st.markdown(f"""
            **Source:** SimpleBox (Legacy)
            **Dimensions:** {geometry.length:.2f}m × {geometry.width:.2f}m × {geometry.height:.2f}m
            **Floor Area:** {geometry.total_floor_area:.1f} m²
            **Floors:** {geometry.num_floors}
            **WWR:** {geometry.window_wall_ratio:.1%}
            """)
        else:
            st.warning("No geometry data available")

        # Section 2: Envelope (if available from Energieausweis)
        if building_model and get_source(building_model) in ["energieausweis", "oib_energieausweis"]:
            ea_data = get_attr_safe(building_model, 'energieausweis_data')
            if ea_data:
                st.markdown("---")
                st.markdown("### 🧱 Envelope (U-values)")
                st.markdown(f"""
                **Wall:** {ea_data.get('u_wert_wand', 'N/A')} W/m²K
                **Roof:** {ea_data.get('u_wert_dach', 'N/A')} W/m²K
                **Floor:** {ea_data.get('u_wert_boden', 'N/A')} W/m²K
                **Windows:** {ea_data.get('u_wert_fenster', 'N/A')} W/m²K
                """)

        # Section 3: HVAC
        st.markdown("---")
        st.markdown("### ❄️ HVAC System")

        hvac_config = st.session_state.get('hvac_config', {})
        if hvac_config:
            st.markdown(f"""
            **System Type:** {hvac_config.get('type', 'N/A')}
            **Heating Setpoint:** {hvac_config.get('heating_setpoint', 20):.1f}°C
            **Cooling Setpoint:** {hvac_config.get('cooling_setpoint', 26):.1f}°C
            **Air Change Rate:** {hvac_config.get('air_change_rate', 0):.2f} ACH
            **Outdoor Air:** {'Yes' if hvac_config.get('outdoor_air', False) else 'No'}
            """)
        else:
            st.info("No HVAC configuration found")

        # Section 4: Simulation Settings
        st.markdown("---")
        st.markdown("### ⚙️ Simulation Settings")

        sim_settings = st.session_state.get('sim_settings', {})
        weather_file = st.session_state.get('weather_file', 'N/A')

        timestep = sim_settings.get('timestep', 4)
        st.markdown(f"""
        **Weather File:** `{Path(weather_file).name if weather_file != 'N/A' else 'N/A'}`
        **Timestep:** {timestep}/hour ({60/timestep:.1f} min intervals)
        **Run Period:** {sim_settings.get('start_month', 1)}/{sim_settings.get('start_day', 1)} - {sim_settings.get('end_month', 12)}/{sim_settings.get('end_day', 31)}
        **Reporting Frequency:** {sim_settings.get('reporting_frequency', 'Hourly')}
        **Output Variables:** {len(sim_settings.get('output_variables', []))} variables
        """)

        # Show output variables in expander
        if sim_settings.get('output_variables'):
            with st.expander("📊 Output Variables List"):
                for var in sim_settings['output_variables']:
                    st.text(f"• {var}")

        # YAML Export Section
        st.markdown("---")
        st.markdown("### 💾 Export Configuration")

        st.markdown("""
        Export this simulation setup as a YAML configuration file.
        You can use this file to reproduce the simulation via command line:
        ```bash
        python scripts/run_from_config.py exported_config.yaml
        ```
        """)

        if st.button("📥 Export as YAML", type="primary", key="export_yaml_btn"):
            try:
                # Import builder
                import sys
                from pathlib import Path as P
                sys.path.insert(0, str(P(__file__).parent.parent.parent.parent))

                from features.web_ui.utils.config_builder import build_simulation_config_from_ui
                import yaml

                # Build config from session state (supports both SimpleBox and Energieausweis)
                config = build_simulation_config_from_ui(st.session_state)

                # Convert to YAML string
                yaml_str = yaml.dump(
                    config.model_dump(exclude_none=True),
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    indent=2
                )

                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                source = config.building.source
                filename = f"{source}_export_{timestamp}.yaml"

                # Download button
                st.download_button(
                    label="💾 Download YAML Config",
                    data=yaml_str,
                    file_name=filename,
                    mime="text/yaml",
                    key="download_yaml_btn"
                )

                st.success(f"✅ Configuration exported successfully! ({source} workflow)")

                # Preview
                with st.expander("📄 YAML Preview"):
                    st.code(yaml_str, language="yaml")

            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
                with st.expander("🐛 Error Details"):
                    st.exception(e)

except Exception as e:
    st.error(f"❌ Fehler beim Laden der Ergebnisse: {str(e)}")
    st.exception(e)
    st.stop()

# Navigation (außerhalb der Tabs)
st.markdown("---")
st.info("""
### 🔄 Neue Simulation

Möchten Sie eine neue Simulation durchführen?

1. Ändern Sie die **Geometrie** oder das **HVAC-System**
2. Starten Sie eine **neue Simulation**
3. Vergleichen Sie die Ergebnisse
""")
