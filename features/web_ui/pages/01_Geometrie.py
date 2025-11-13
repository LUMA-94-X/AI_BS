"""Vereinheitlichte Geometrie-Seite mit zwei Eingabemethoden."""

import streamlit as st
import sys
import os
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from features.geometrie.box_generator import BuildingGeometry
from features.geometrie.models.energieausweis_input import (
    EnergieausweisInput,
    FensterData,
    GebaeudeTyp
)
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from features.geometrie.utils.geometry_solver import GeometrySolver
from features.geometrie.utils.perimeter_calculator import PerimeterCalculator
from features.geometrie.utils.fenster_distribution import FensterDistribution
from core.building_model import BuildingModel, save_building_model_to_session
from features.web_ui.components import (
    create_3d_building_visualization,
    create_2d_floorplan,
    create_elevation_views,
    create_3d_building_with_zones,
    display_geometry_metrics
)

st.set_page_config(
    page_title="Geometrie - Gebäudesimulation",
    page_icon="🏗️",
    layout="wide",
)

st.title("🏗️ Gebäudegeometrie")
st.markdown("---")

# Info-Box
st.info("""
**Wählen Sie eine Eingabemethode:**
- **Einfache Eingabe**: Schnelle parametrische Gebäudeerstellung (SimpleBox)
- **Energieausweis**: Detailliertes 5-Zone-Modell aus Energieausweis-Daten
- **Vorschau**: 3D-Visualisierung und Kennzahlen
""")

# ============================================================================
# TAB-NAVIGATION
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📐 Einfache Eingabe", "📋 Energieausweis", "🏢 Vorschau"])

# ============================================================================
# TAB 1: EINFACHE EINGABE (SimpleBox)
# ============================================================================

with tab1:
    st.subheader("📐 Einfache parametrische Eingabe")

    col_input, col_info = st.columns([2, 1])

    with col_input:
        # Grundabmessungen
        st.markdown("#### Abmessungen")
        length = st.slider(
            "Länge (m)",
            min_value=5.0,
            max_value=100.0,
            value=20.0,
            step=0.5,
            help="Länge des Gebäudes in Metern"
        )

        width = st.slider(
            "Breite (m)",
            min_value=5.0,
            max_value=100.0,
            value=12.0,
            step=0.5,
            help="Breite des Gebäudes in Metern"
        )

        height = st.slider(
            "Gesamthöhe (m)",
            min_value=3.0,
            max_value=100.0,
            value=6.0,
            step=0.5,
            help="Gesamthöhe des Gebäudes in Metern"
        )

        st.markdown("#### Stockwerke")
        num_floors = st.number_input(
            "Anzahl Stockwerke",
            min_value=1,
            max_value=20,
            value=2,
            step=1,
            help="Anzahl der Stockwerke"
        )

        floor_height = height / num_floors
        st.caption(f"Stockwerkshöhe: {floor_height:.2f} m")

        # Fenster
        st.markdown("#### Fenster")
        window_wall_ratio = st.slider(
            "Fensterflächenanteil",
            min_value=0.0,
            max_value=0.9,
            value=0.3,
            step=0.05,
            help="Anteil der Fensterfläche an der Wandfläche (0.0 - 0.9)"
        )
        st.caption(f"{window_wall_ratio * 100:.0f}% der Wandfläche")

        # Orientierung
        st.markdown("#### Ausrichtung")
        orientation = st.slider(
            "Orientierung (°)",
            min_value=0,
            max_value=359,
            value=0,
            step=15,
            help="Ausrichtung des Gebäudes in Grad (0° = Nord)"
        )

        orientation_text = {
            0: "Nord", 45: "Nordost", 90: "Ost", 135: "Südost",
            180: "Süd", 225: "Südwest", 270: "West", 315: "Nordwest"
        }
        nearest = min(orientation_text.keys(), key=lambda x: abs(x - orientation))
        st.caption(f"Ungefähr Richtung: {orientation_text.get(nearest, 'Zwischen Himmelsrichtungen')}")

    with col_info:
        st.markdown("#### ℹ️ Info")
        st.markdown("""
        **SimpleBox-Modell:**
        - Rechteckige Grundfläche
        - Gleichmäßige Stockwerke
        - Automatische Fensterverteilung
        - Schnelle Erstellung

        **Geeignet für:**
        - Erste Konzeptstudien
        - Parameterstudien
        - Einfache Gebäudetypen
        """)

    st.markdown("---")

    # Button zum Speichern der Geometrie
    col_btn, col_status = st.columns([1, 2])

    with col_btn:
        if st.button("💾 Geometrie speichern", type="primary", key="save_simplebox"):
            # Erstelle Geometrie-Objekt
            geometry = BuildingGeometry(
                length=length,
                width=width,
                height=height,
                num_floors=num_floors,
                window_wall_ratio=window_wall_ratio,
                orientation=orientation,
            )

            # BuildingModel erstellen mit from_simplebox()
            floor_height = height / num_floors
            building_model = BuildingModel.from_simplebox(
                length=length,
                width=width,
                height=height,
                num_floors=num_floors,
                floor_height=floor_height,
                window_wall_ratio=window_wall_ratio,
                idf_path=None  # Wird erst bei Simulation erstellt
            )

            # Session State speichern
            st.session_state['geometry'] = geometry  # Legacy-Support
            save_building_model_to_session(st.session_state, building_model)
            st.session_state['geometry_method'] = 'simplebox'
            st.session_state['geometry_valid'] = True
            st.session_state['visualization_data'] = {
                'length': length,
                'width': width,
                'height': height,
                'num_floors': num_floors,
                'window_wall_ratio': window_wall_ratio,
            }

            st.success("✅ Geometrie gespeichert!")

    with col_status:
        if st.session_state.get('geometry_method') == 'simplebox' and st.session_state.get('geometry_valid'):
            st.success("✅ SimpleBox-Geometrie aktiv - Wechseln Sie zu 'Vorschau' für 3D-Ansicht")


# ============================================================================
# TAB 2: ENERGIEAUSWEIS (5-Zone-Modell)
# ============================================================================

with tab2:
    st.subheader("📋 Energieausweis-basierte Generierung")

    col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

    # ========== SPALTE 1: GEBÄUDEDATEN ==========
    with col1:
        st.markdown("#### 🏢 Gebäudedaten")

        gebaeudetyp = st.selectbox(
            "Gebäudetyp",
            options=[typ.value for typ in GebaeudeTyp],
            index=1,  # MFH default
            help="Einfamilienhaus, Mehrfamilienhaus oder Nichtwohngebäude"
        )

        bruttoflaeche = st.number_input(
            "Bruttogrundfläche (m²) *",
            min_value=20.0,
            max_value=50000.0,
            value=165.0,
            step=10.0,
            help="Brutto-Grundfläche inkl. Wände (Pflichtfeld)"
        )

        st.markdown("#### 📐 Hüllflächen (optional)")
        st.caption("Falls bekannt - verbessert die Geometrie-Rekonstruktion")

        use_envelope_data = st.checkbox("Hüllflächen-Daten eingeben", value=False)

        if use_envelope_data:
            wandflaeche = st.number_input("Außenwandfläche (m²)", min_value=0.0, max_value=10000.0, value=240.0, step=10.0)
            dachflaeche = st.number_input("Dachfläche (m²)", min_value=0.0, max_value=5000.0, value=80.0, step=5.0)
            bodenflaeche = st.number_input("Bodenfläche (m²)", min_value=0.0, max_value=5000.0, value=80.0, step=5.0)
        else:
            wandflaeche = None
            dachflaeche = None
            bodenflaeche = None

        st.markdown("#### 🏗️ Geschosse")
        anzahl_geschosse = st.number_input("Anzahl Geschosse", min_value=1, max_value=20, value=2, step=1)
        geschosshoehe = st.slider("Geschosshöhe (m)", min_value=2.3, max_value=4.5, value=3.0, step=0.1)

        aspect_ratio = st.slider(
            "Länge/Breite-Verhältnis (Hint)",
            min_value=1.0,
            max_value=3.0,
            value=1.5,
            step=0.1,
            help="1.0=quadratisch, 3.0=langgestreckt"
        )

    # ========== SPALTE 2: HÜLLFLÄCHEN ==========
    with col2:
        st.markdown("#### 🧱 Hüllflächen")

        st.markdown("**U-Werte (W/m²K) ***")

        u_wand = st.number_input("U-Wert Außenwand", min_value=0.1, max_value=3.0, value=0.35, step=0.05)
        u_dach = st.number_input("U-Wert Dach", min_value=0.1, max_value=2.0, value=0.25, step=0.05)
        u_boden = st.number_input("U-Wert Bodenplatte", min_value=0.1, max_value=2.0, value=0.40, step=0.05)
        u_fenster = st.number_input("U-Wert Fenster", min_value=0.5, max_value=6.0, value=1.3, step=0.1)
        g_wert = st.slider("g-Wert Fenster (SHGC)", min_value=0.1, max_value=0.9, value=0.6, step=0.05)

        st.markdown("#### 🪟 Fenster")

        fenster_mode = st.radio(
            "Eingabeart",
            options=["Gesamt-WWR", "Exakte Flächen pro Orientierung"],
            index=0
        )

        if fenster_mode == "Gesamt-WWR":
            wwr_gesamt = st.slider("Fensterflächenanteil (WWR)", min_value=0.05, max_value=0.95, value=0.30, step=0.05)
            st.caption(f"{wwr_gesamt*100:.0f}% der Wandfläche")
            fenster_data = FensterData(window_wall_ratio=wwr_gesamt)
        else:
            st.caption("Fensterflächen in m²:")
            f_nord = st.number_input("Nord", min_value=0.0, max_value=500.0, value=10.0, step=1.0)
            f_ost = st.number_input("Ost", min_value=0.0, max_value=500.0, value=15.0, step=1.0)
            f_sued = st.number_input("Süd", min_value=0.0, max_value=500.0, value=25.0, step=1.0)
            f_west = st.number_input("West", min_value=0.0, max_value=500.0, value=12.0, step=1.0)
            fenster_data = FensterData(nord_m2=f_nord, ost_m2=f_ost, sued_m2=f_sued, west_m2=f_west)
            st.caption(f"Gesamt: {f_nord + f_ost + f_sued + f_west:.1f} m²")

        st.markdown("#### 💨 Lüftung")
        luftwechsel = st.slider("Luftwechselrate (1/h)", min_value=0.0, max_value=3.0, value=0.5, step=0.1)

        st.markdown("#### 📊 Energieausweis-Kennwerte")
        st.caption("Optional - können automatisch berechnet werden")

        use_kennwerte_input = st.checkbox("Kennwerte manuell eingeben", value=False, key="use_kennwerte")

        if use_kennwerte_input:
            brutto_volumen_input = st.number_input(
                "Brutto-Volumen (m³)",
                min_value=30.0,
                max_value=500000.0,
                value=500.0,
                step=10.0,
                help="Brutto-Volumen inkl. Wände"
            )
            kompaktheit_input = st.number_input(
                "Kompaktheit A/V (m²/m³)",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1,
                help="Verhältnis Hüllfläche zu Volumen"
            )
            char_laenge_input = st.number_input(
                "Charakteristische Länge (m)",
                min_value=0.5,
                max_value=50.0,
                value=1.0,
                step=0.1,
                help="lc = V/A"
            )
            mittlerer_u_wert_input = st.number_input(
                "Mittlerer U-Wert (W/m²K)",
                min_value=0.1,
                max_value=3.0,
                value=0.5,
                step=0.05,
                help="Flächengewichteter mittlerer U-Wert"
            )
        else:
            brutto_volumen_input = None
            kompaktheit_input = None
            char_laenge_input = None
            mittlerer_u_wert_input = None

        bauweise = st.selectbox(
            "Bauweise",
            options=["Massiv", "Leicht"],
            index=0,
            help="Bauweise des Gebäudes"
        )

    # ========== SPALTE 3: VORSCHAU & GENERIERUNG ==========
    with col3:
        st.markdown("#### 🔍 Geometrie-Rekonstruktion")

        try:
            from features.geometrie.models.energieausweis_input import Bauweise

            ea_input = EnergieausweisInput(
                bruttoflaeche_m2=bruttoflaeche,
                wandflaeche_m2=wandflaeche,
                dachflaeche_m2=dachflaeche,
                bodenflaeche_m2=bodenflaeche,
                anzahl_geschosse=anzahl_geschosse,
                geschosshoehe_m=geschosshoehe,
                u_wert_wand=u_wand,
                u_wert_dach=u_dach,
                u_wert_boden=u_boden,
                u_wert_fenster=u_fenster,
                g_wert_fenster=g_wert,
                brutto_volumen_m3=brutto_volumen_input,
                kompaktheit=kompaktheit_input,
                charakteristische_laenge_m=char_laenge_input,
                mittlerer_u_wert=mittlerer_u_wert_input,
                bauweise=Bauweise(bauweise),
                fenster=fenster_data,
                luftwechselrate_h=luftwechsel,
                gebaeudetyp=GebaeudeTyp(gebaeudetyp),
                aspect_ratio_hint=aspect_ratio
            )

            if st.button("🔍 Geometrie berechnen", type="primary", key="calc_geometry"):
                with st.spinner("Berechne Geometrie..."):
                    solver = GeometrySolver()
                    solution = solver.solve(ea_input)

                    st.session_state['ea_input'] = ea_input
                    st.session_state['geo_solution'] = solution

            # Zeige Lösung falls vorhanden
            if 'geo_solution' in st.session_state:
                solution = st.session_state['geo_solution']

                st.success(f"✅ Geometrie berechnet ({solution.method.value})")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Länge", f"{solution.length:.1f} m")
                with col_b:
                    st.metric("Breite", f"{solution.width:.1f} m")
                with col_c:
                    st.metric("Höhe", f"{solution.height:.1f} m")

                col_d, col_e = st.columns(2)
                with col_d:
                    st.metric("Grundfläche", f"{solution.floor_area:.0f} m²")
                with col_e:
                    st.metric("Volumen", f"{solution.volume:.0f} m³")

                confidence_color = "🟢" if solution.confidence > 0.8 else "🟡" if solution.confidence > 0.6 else "🔴"
                st.info(f"{confidence_color} **Konfidenz:** {solution.confidence*100:.0f}%")

                if solution.warnings:
                    with st.expander("⚠️ Warnungen"):
                        for warning in solution.warnings:
                            st.warning(warning)

                st.markdown("---")

                # IDF-Generierung
                st.markdown("#### 🏗️ 5-Zone-Modell erstellen")

                if st.button("🚀 5-Zone-IDF erstellen", type="primary", key="create_5zone"):
                    with st.spinner("Erstelle 5-Zone-Modell..."):
                        try:
                            generator = FiveZoneGenerator()
                            output_dir = Path(__file__).parent.parent.parent.parent / "output" / "energieausweis"
                            output_dir.mkdir(parents=True, exist_ok=True)
                            output_path = output_dir / "gebaeude_5zone.idf"

                            idf = generator.create_from_energieausweis(
                                ea_data=ea_input,
                                output_path=output_path
                            )

                            zones = idf.idfobjects["ZONE"]
                            surfaces = idf.idfobjects["BUILDINGSURFACE:DETAILED"]
                            windows = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]

                            st.success(f"✅ IDF erstellt: `{output_path.name}`")

                            # Session State
                            st.session_state['idf'] = idf
                            st.session_state['idf_path'] = output_path
                            st.session_state['geometry_source'] = 'energieausweis'
                            st.session_state['geometry_method'] = 'energieausweis'
                            st.session_state['geometry_valid'] = True

                            # BuildingModel erstellen
                            geo_solution = st.session_state.get('geo_solution')
                            if geo_solution:
                                building_model = BuildingModel.from_energieausweis(
                                    geo_solution=geo_solution,
                                    ea_data=ea_input,
                                    idf_path=output_path,
                                    num_zones=len(zones)
                                )
                                save_building_model_to_session(st.session_state, building_model)

                                # Erstelle Zonen-Layout für ALLE Geschosse (für Visualisierung)
                                perimeter_calc = PerimeterCalculator()
                                wwr = ea_input.fenster.window_wall_ratio or 0.3

                                # Berechne Fenster-Verteilung (für realistische Fassaden-Visualisierung)
                                fenster_dist = FensterDistribution()

                                # Wandflächen berechnen
                                wall_areas = fenster_dist.estimate_wall_areas_from_geometry(
                                    building_length=geo_solution.length,
                                    building_width=geo_solution.width,
                                    building_height=geo_solution.height
                                )

                                # WWR pro Orientierung berechnen
                                orientation_wwr = fenster_dist.calculate_orientation_wwr(
                                    fenster_data=ea_input.fenster,
                                    wall_areas=wall_areas,
                                    gebaeudetyp=ea_input.gebaeudetyp
                                )

                                # Fensterflächen berechnen (in m²)
                                window_areas = fenster_dist.calculate_window_areas(
                                    orientation_wwr=orientation_wwr,
                                    wall_areas=wall_areas
                                )

                                # Multi-Floor Layouts erstellen
                                all_floor_layouts = perimeter_calc.create_multi_floor_layout(
                                    building_length=geo_solution.length,
                                    building_width=geo_solution.width,
                                    floor_height=geo_solution.floor_height,
                                    num_floors=geo_solution.num_floors,
                                    wwr=wwr
                                )

                                # Konvertiere alle Zonen aller Geschosse zu Dict
                                all_zones_dict = []
                                for floor_num, floor_layout in all_floor_layouts.items():
                                    for zone_name, zone_geom in floor_layout.all_zones.items():
                                        all_zones_dict.append({
                                            'floor': floor_num,
                                            'zone_name': zone_name,
                                            'name': zone_geom.name,
                                            'x_origin': zone_geom.x_origin,
                                            'y_origin': zone_geom.y_origin,
                                            'z_origin': zone_geom.z_origin,
                                            'length': zone_geom.length,
                                            'width': zone_geom.width,
                                            'height': zone_geom.height,
                                            'floor_area': zone_geom.floor_area,
                                        })

                                # Erstes Geschoss separat für 2D-Grundriss
                                zone_layout_first_floor_dict = {}
                                for zone_name, zone_geom in all_floor_layouts[0].all_zones.items():
                                    zone_layout_first_floor_dict[zone_name] = {
                                        'name': zone_geom.name,
                                        'x_origin': zone_geom.x_origin,
                                        'y_origin': zone_geom.y_origin,
                                        'z_origin': zone_geom.z_origin,
                                        'length': zone_geom.length,
                                        'width': zone_geom.width,
                                        'height': zone_geom.height,
                                        'floor_area': zone_geom.floor_area,
                                    }

                                # Visualisierungs-Daten speichern
                                st.session_state['visualization_data'] = {
                                    'length': geo_solution.length,
                                    'width': geo_solution.width,
                                    'height': geo_solution.height,
                                    'num_floors': geo_solution.num_floors,
                                    'floor_area': geo_solution.floor_area,
                                    'volume': geo_solution.volume,
                                    'av_ratio': geo_solution.av_ratio,
                                    'zone_layout': zone_layout_first_floor_dict,  # Erstes Geschoss für 2D-Grundriss
                                    'all_zones': all_zones_dict,  # ALLE Zonen aller Geschosse für 3D
                                    'window_wall_ratio': wwr,
                                    # NEU: Fenster-Daten für realistische Fassaden-Visualisierung
                                    'window_data': {
                                        'wall_areas': wall_areas,  # {"north": 60.0, "east": 36.0, ...}
                                        'orientation_wwr': {  # WWR pro Orientierung
                                            'north': orientation_wwr.north,
                                            'east': orientation_wwr.east,
                                            'south': orientation_wwr.south,
                                            'west': orientation_wwr.west,
                                        },
                                        'window_areas': window_areas,  # {"north": 12.0, "east": 8.0, ...} in m²
                                    }
                                }

                            col_s1, col_s2, col_s3 = st.columns(3)
                            with col_s1:
                                st.metric("Zonen", len(zones))
                            with col_s2:
                                st.metric("Surfaces", len(surfaces))
                            with col_s3:
                                st.metric("Fenster", len(windows))

                            st.info("✅ Wechseln Sie zu 'Vorschau' für die 3D-Ansicht oder zu **HVAC** für das nächste Setup.")

                        except Exception as e:
                            st.error(f"❌ Fehler: {e}")
                            import traceback
                            with st.expander("🐛 Details"):
                                st.code(traceback.format_exc())

            else:
                st.info("👆 Klicken Sie auf 'Geometrie berechnen' um zu starten.")

        except Exception as e:
            st.error(f"❌ Validierungsfehler: {e}")


# ============================================================================
# TAB 3: VORSCHAU (3D-Visualisierung + Metriken)
# ============================================================================

with tab3:
    st.subheader("🏢 Gebäudevorschau")

    if not st.session_state.get('geometry_valid', False):
        st.info("""
        🏗️ **Keine Geometrie definiert**

        Bitte erstellen Sie zuerst eine Geometrie:
        - **Tab "Einfache Eingabe"**: Schnelle parametrische Erstellung
        - **Tab "Energieausweis"**: Detaillierte 5-Zone-Rekonstruktion
        """)
    else:
        method = st.session_state.get('geometry_method', 'unknown')
        viz_data = st.session_state.get('visualization_data', {})

        # Header mit Methode
        method_emoji = "📐" if method == 'simplebox' else "📋"
        method_name = "Einfache Eingabe (SimpleBox)" if method == 'simplebox' else "Energieausweis (5-Zone)"

        st.success(f"{method_emoji} **Aktive Methode:** {method_name}")

        st.markdown("---")

        # Button zum Aktualisieren der Vorschau
        if st.button("🔄 Vorschau aktualisieren", type="primary"):
            st.rerun()

        # Sub-Tabs für verschiedene Visualisierungen
        viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
            "🎯 3D-Ansicht",
            "📐 Grundriss 2D",
            "🏛️ Fassaden",
            "📊 Kennzahlen"
        ])

        # ===== 3D-ANSICHT =====
        with viz_tab1:
            try:
                all_zones = viz_data.get('all_zones')  # ALLE Zonen aller Geschosse

                if all_zones:
                    # 5-Zone-Modell: 3D mit Zonen-Farben (ALLE Geschosse)
                    fig = create_3d_building_with_zones(
                        length=viz_data['length'],
                        width=viz_data['width'],
                        height=viz_data['height'],
                        num_floors=viz_data['num_floors'],
                        zone_layout=all_zones,  # Übergebe ALLE Zonen
                        title=f"3D-Ansicht mit Zonen: {method_name}"
                    )
                else:
                    # SimpleBox: Einfache 3D-Ansicht
                    fig = create_3d_building_visualization(
                        length=viz_data['length'],
                        width=viz_data['width'],
                        height=viz_data['height'],
                        num_floors=viz_data['num_floors'],
                        title=f"3D-Ansicht: {method_name}"
                    )

                st.plotly_chart(fig, use_container_width=True)
                st.caption("💡 **Tipp:** Sie können die 3D-Ansicht mit der Maus drehen, zoomen und verschieben.")

                # Legende für 5-Zone
                if all_zones:
                    st.markdown("#### 🎨 Zonen-Legende")
                    col_leg1, col_leg2, col_leg3, col_leg4, col_leg5 = st.columns(5)
                    with col_leg1:
                        st.markdown("🔴 **Nord**: Perimeter Nord")
                    with col_leg2:
                        st.markdown("🔵 **Ost**: Perimeter Ost")
                    with col_leg3:
                        st.markdown("🟢 **Süd**: Perimeter Süd")
                    with col_leg4:
                        st.markdown("🟡 **West**: Perimeter West")
                    with col_leg5:
                        st.markdown("⚪ **Kern**: Core Zone")

                    # Zeige Anzahl Zonen insgesamt
                    st.caption(f"Gesamt: {len(all_zones)} Zonen über {viz_data['num_floors']} Geschosse ({len(all_zones) // viz_data['num_floors']} Zonen pro Geschoss)")

            except KeyError as e:
                st.error(f"❌ Fehlende Visualisierungsdaten: {e}")
            except Exception as e:
                st.error(f"❌ Fehler bei 3D-Visualisierung: {e}")
                import traceback
                with st.expander("🐛 Debug-Info"):
                    st.code(traceback.format_exc())

        # ===== GRUNDRISS 2D =====
        with viz_tab2:
            try:
                zone_layout = viz_data.get('zone_layout')

                fig = create_2d_floorplan(
                    length=viz_data['length'],
                    width=viz_data['width'],
                    zone_layout=zone_layout,
                    title=f"Grundriss (Geschoss 1): {method_name}"
                )

                st.plotly_chart(fig, use_container_width=True)

                if zone_layout:
                    st.info("""
                    📋 **5-Zone-Modell**:
                    - **Nord/Süd-Zonen**: Gesamte Gebäudebreite (inkl. Ecken)
                    - **Ost/West-Zonen**: Zwischen Nord- und Süd-Zone
                    - **Kern-Zone**: Zentral, keine Außenwände
                    """)
                else:
                    st.info("📦 **SimpleBox**: Einfache rechteckige Grundfläche ohne Zonen-Unterteilung")

            except KeyError as e:
                st.error(f"❌ Fehlende Visualisierungsdaten: {e}")
            except Exception as e:
                st.error(f"❌ Fehler bei Grundriss-Visualisierung: {e}")

        # ===== FASSADEN =====
        with viz_tab3:
            try:
                # Hole Fenster-Daten (falls 5-Zone-Modell, sonst Fallback)
                window_data = viz_data.get('window_data', {
                    'window_wall_ratio': viz_data.get('window_wall_ratio', 0.3)
                })

                fig = create_elevation_views(
                    length=viz_data['length'],
                    width=viz_data['width'],
                    height=viz_data['height'],
                    num_floors=viz_data['num_floors'],
                    window_data=window_data,
                    title=f"Fassaden-Ansichten: {method_name}"
                )

                st.plotly_chart(fig, use_container_width=True)

                # Zeige Fenster-Statistiken falls verfügbar
                if 'window_data' in viz_data and 'window_areas' in viz_data['window_data']:
                    window_areas = viz_data['window_data']['window_areas']
                    orientation_wwr = viz_data['window_data']['orientation_wwr']

                    st.markdown("### 📊 Fenster-Statistik")

                    col_n, col_e, col_s, col_w = st.columns(4)
                    with col_n:
                        st.metric("Nord", f"{window_areas['north']:.1f} m²", f"WWR: {orientation_wwr['north']*100:.1f}%")
                    with col_e:
                        st.metric("Ost", f"{window_areas['east']:.1f} m²", f"WWR: {orientation_wwr['east']*100:.1f}%")
                    with col_s:
                        st.metric("Süd", f"{window_areas['south']:.1f} m²", f"WWR: {orientation_wwr['south']*100:.1f}%")
                    with col_w:
                        st.metric("West", f"{window_areas['west']:.1f} m²", f"WWR: {orientation_wwr['west']*100:.1f}%")

                    total_window_area = sum(window_areas.values())
                    total_wall_area = sum(viz_data['window_data']['wall_areas'].values())
                    avg_wwr = total_window_area / total_wall_area if total_wall_area > 0 else 0

                    st.metric("Gesamt-Fensterfläche", f"{total_window_area:.1f} m²", f"Ø WWR: {avg_wwr*100:.1f}%")

                    st.info("""
                    🪟 **Realistische Fenster-Darstellung**:
                    - Fenstergrößen basieren auf **echten Fensterflächen** aus Energieausweis
                    - Typische Fenstergröße: 1.2m × 1.5m (1.8m²)
                    - Anzahl Fenster berechnet aus Fensterfläche / typische Größe
                    - Brüstungshöhe: 0.9m (Standard)
                    - **WWR variiert pro Orientierung** (Nord/Ost/Süd/West)
                    """)
                else:
                    st.info("""
                    🪟 **Vereinfachte Fenster-Darstellung**:
                    - Vereinfachte Darstellung mit Standard-Fenstern
                    - Für detaillierte Fenster: Verwenden Sie das 5-Zone-Modell mit Energieausweis-Daten
                    - **Grau**: Außenwände | **Blau**: Fenster
                    """)

            except KeyError as e:
                st.error(f"❌ Fehlende Visualisierungsdaten: {e}")
            except Exception as e:
                st.error(f"❌ Fehler bei Fassaden-Visualisierung: {e}")
                import traceback
                with st.expander("🐛 Debug-Info"):
                    st.code(traceback.format_exc())

        # ===== KENNZAHLEN =====
        with viz_tab4:
            display_geometry_metrics(viz_data, show_advanced=True)

            # Zonen-Statistiken für 5-Zone-Modell
            if viz_data.get('zone_layout'):
                st.markdown("---")
                st.markdown("### 📈 Zonen-Statistiken")

                zone_layout = viz_data['zone_layout']

                # Tabelle mit Zonendaten (ohne pandas/pyarrow)
                # Header
                st.markdown("| Zone | Fläche [m²] | Länge [m] | Breite [m] | Höhe [m] |")
                st.markdown("|------|-------------|-----------|------------|----------|")

                # Zeilen
                for zone_name, zone_info in zone_layout.items():
                    st.markdown(
                        f"| {zone_name.capitalize()} | "
                        f"{zone_info['floor_area']:.1f} | "
                        f"{zone_info['length']:.1f} | "
                        f"{zone_info['width']:.1f} | "
                        f"{zone_info['height']:.1f} |"
                    )

                # Gesamt-Fläche
                total_zone_area = sum(z['floor_area'] for z in zone_layout.values())
                st.metric("Gesamt-Zonenfläche (Geschoss 1)", f"{total_zone_area:.1f} m²")

        st.markdown("---")

        # Navigation
        st.markdown("### ➡️ Nächster Schritt")

        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("🔧 Weiter zu HVAC", type="primary", use_container_width=True):
                st.switch_page("pages/02_HVAC.py")
        with col_nav2:
            if st.button("🔙 Geometrie ändern", use_container_width=True):
                # Zurück zu Tab 1 oder 2 (Streamlit limitation - nur rerun möglich)
                st.info("Wechseln Sie zu Tab 1 oder 2 um die Geometrie zu ändern")


# ============================================================================
# FOOTER: HILFE & BEISPIELE
# ============================================================================

st.markdown("---")

with st.expander("💡 Beispieldaten"):
    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
        st.markdown("**SimpleBox: Bürogebäude**")
        st.code("""
Länge: 30 m
Breite: 15 m
Höhe: 12 m
Stockwerke: 4
Fensterflächenanteil: 40%
Orientierung: 0° (Nord)
        """)

    with col_ex2:
        st.markdown("**Energieausweis: EFH Neubau**")
        st.code("""
Nettofläche: 150 m²
Wandfläche: 240 m²
Geschosse: 2
U-Wand: 0.28 W/m²K
U-Dach: 0.20 W/m²K
U-Fenster: 1.30 W/m²K
Fenster Süd: 20 m²
        """)

# Debug-Info (nur wenn im Development-Mode)
if st.checkbox("🐛 Debug-Info anzeigen", value=False):
    with st.expander("Session State"):
        st.json({
            'geometry_method': st.session_state.get('geometry_method'),
            'geometry_valid': st.session_state.get('geometry_valid'),
            'has_building_model': 'building_model' in st.session_state,
            'has_visualization_data': 'visualization_data' in st.session_state,
        })

st.caption("🤖 Powered by Claude Code")
