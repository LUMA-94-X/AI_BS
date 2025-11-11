"""Energieausweis-basierte Geometrie-Generierung."""

import streamlit as st
import sys
import os
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from features.geometrie.models.energieausweis_input import (
    EnergieausweisInput,
    FensterData,
    GebaeudeTyp
)
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from features.geometrie.utils.geometry_solver import (
    GeometrySolver,
    print_solution_summary
)
from core.building_model import BuildingModel, save_building_model_to_session

st.set_page_config(
    page_title="Energieausweis - 5-Zone-Modell",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Gebäude aus Energieausweis-Daten")
st.markdown("---")

# Info-Box
st.info("""
**5-Zone-Modell (Perimeter N/E/S/W + Kern)**
Erstellen Sie ein detailliertes Gebäudemodell basierend auf Energieausweis-Angaben.
Die Geometrie wird automatisch rekonstruiert.
""")

# ============================================================================
# DREI SPALTEN: GEBÄUDEDATEN | HÜLLFLÄCHEN | VORSCHAU
# ============================================================================

col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

# ============================================================================
# SPALTE 1: GEBÄUDEDATEN
# ============================================================================

with col1:
    st.subheader("🏢 Gebäudedaten")

    # Gebäudetyp
    gebaeudetyp = st.selectbox(
        "Gebäudetyp",
        options=[typ.value for typ in GebaeudeTyp],
        index=1,  # MFH default
        help="Einfamilienhaus, Mehrfamilienhaus oder Nichtwohngebäude"
    )

    # Nettofläche (PFLICHT)
    nettoflaeche = st.number_input(
        "Nettogrundfläche (m²) *",
        min_value=20.0,
        max_value=50000.0,
        value=150.0,
        step=10.0,
        help="Konditionierte Nutzfläche (Pflichtfeld)"
    )

    # Optional: Hüllflächen für bessere Geometrie-Rekonstruktion
    st.markdown("#### 📐 Hüllflächen (optional)")
    st.caption("Falls bekannt - verbessert die Geometrie-Rekonstruktion")

    use_envelope_data = st.checkbox("Hüllflächen-Daten eingeben", value=False)

    if use_envelope_data:
        wandflaeche = st.number_input(
            "Außenwandfläche (m²)",
            min_value=0.0,
            max_value=10000.0,
            value=240.0,
            step=10.0
        )
        dachflaeche = st.number_input(
            "Dachfläche (m²)",
            min_value=0.0,
            max_value=5000.0,
            value=80.0,
            step=5.0
        )
        bodenflaeche = st.number_input(
            "Bodenfläche (m²)",
            min_value=0.0,
            max_value=5000.0,
            value=80.0,
            step=5.0
        )
    else:
        wandflaeche = None
        dachflaeche = None
        bodenflaeche = None

    st.markdown("#### 🏗️ Geschosse")
    anzahl_geschosse = st.number_input(
        "Anzahl Geschosse",
        min_value=1,
        max_value=20,
        value=2,
        step=1
    )

    geschosshoehe = st.slider(
        "Geschosshöhe (m)",
        min_value=2.3,
        max_value=4.5,
        value=3.0,
        step=0.1,
        help="Typisch: 2.5-3.0m für Wohnen, 3.0-4.0m für Büro"
    )

    # Aspect Ratio Hint
    aspect_ratio = st.slider(
        "Länge/Breite-Verhältnis (Hint)",
        min_value=1.0,
        max_value=3.0,
        value=1.5,
        step=0.1,
        help="Hinweis für Geometrie-Rekonstruktion: 1.0=quadratisch, 3.0=langgestreckt"
    )

# ============================================================================
# SPALTE 2: HÜLLFLÄCHEN-EIGENSCHAFTEN
# ============================================================================

with col2:
    st.subheader("🧱 Hüllflächen")

    st.markdown("#### U-Werte (W/m²K) *")

    u_wand = st.number_input(
        "U-Wert Außenwand",
        min_value=0.1,
        max_value=3.0,
        value=0.35,
        step=0.05,
        help="Typisch: 0.2-0.4 für Neubau, 0.5-1.5 für Altbau"
    )

    u_dach = st.number_input(
        "U-Wert Dach",
        min_value=0.1,
        max_value=2.0,
        value=0.25,
        step=0.05,
        help="Typisch: 0.15-0.3 für gedämmte Dächer"
    )

    u_boden = st.number_input(
        "U-Wert Bodenplatte",
        min_value=0.1,
        max_value=2.0,
        value=0.40,
        step=0.05,
        help="Typisch: 0.3-0.5"
    )

    u_fenster = st.number_input(
        "U-Wert Fenster",
        min_value=0.5,
        max_value=6.0,
        value=1.3,
        step=0.1,
        help="Typisch: 1.0-1.5 für Isolierverglasung, 2.5-3.0 für Einfachverglasung"
    )

    g_wert = st.slider(
        "g-Wert Fenster (SHGC)",
        min_value=0.1,
        max_value=0.9,
        value=0.6,
        step=0.05,
        help="Solar Heat Gain Coefficient - Typisch: 0.5-0.7"
    )

    st.markdown("#### 🪟 Fenster")

    fenster_mode = st.radio(
        "Eingabeart",
        options=["Gesamt-WWR", "Exakte Flächen pro Orientierung"],
        index=0,
        help="Exakte Flächen sind genauer, wenn im Energieausweis angegeben"
    )

    if fenster_mode == "Gesamt-WWR":
        wwr_gesamt = st.slider(
            "Fensterflächenanteil (WWR)",
            min_value=0.05,
            max_value=0.95,
            value=0.30,
            step=0.05,
            help="Window-to-Wall Ratio"
        )
        st.caption(f"{wwr_gesamt*100:.0f}% der Wandfläche")

        fenster_data = FensterData(window_wall_ratio=wwr_gesamt)

    else:
        st.caption("Fensterflächen in m²:")
        f_nord = st.number_input("Nord", min_value=0.0, max_value=500.0, value=10.0, step=1.0)
        f_ost = st.number_input("Ost", min_value=0.0, max_value=500.0, value=15.0, step=1.0)
        f_sued = st.number_input("Süd", min_value=0.0, max_value=500.0, value=25.0, step=1.0)
        f_west = st.number_input("West", min_value=0.0, max_value=500.0, value=12.0, step=1.0)

        fenster_data = FensterData(
            nord_m2=f_nord,
            ost_m2=f_ost,
            sued_m2=f_sued,
            west_m2=f_west
        )

        total_fenster = f_nord + f_ost + f_sued + f_west
        st.caption(f"Gesamt: {total_fenster:.1f} m²")

    st.markdown("#### 💨 Lüftung")
    luftwechsel = st.slider(
        "Luftwechselrate (1/h)",
        min_value=0.0,
        max_value=3.0,
        value=0.5,
        step=0.1,
        help="Typisch: 0.3-0.6 für Wohngebäude"
    )

# ============================================================================
# SPALTE 3: VORSCHAU & GENERIERUNG
# ============================================================================

with col3:
    st.subheader("🔍 Geometrie-Vorschau")

    # Validierung vor Solver-Aufruf
    validation_ok = True
    validation_errors = []

    if nettoflaeche < 20:
        validation_errors.append("Nettofläche zu klein (min. 20 m²)")
        validation_ok = False

    if use_envelope_data:
        if wandflaeche and dachflaeche and abs(dachflaeche - bodenflaeche) > dachflaeche * 0.5:
            validation_errors.append("Dach- und Bodenfläche weichen stark ab")

    # Erstelle EnergieausweisInput
    try:
        ea_input = EnergieausweisInput(
            nettoflaeche_m2=nettoflaeche,
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
            fenster=fenster_data,
            luftwechselrate_h=luftwechsel,
            gebaeudetyp=GebaeudeTyp(gebaeudetyp),
            aspect_ratio_hint=aspect_ratio
        )

        # Geometrie-Solver
        if st.button("🔍 Geometrie berechnen", type="primary"):
            with st.spinner("Berechne Geometrie..."):
                solver = GeometrySolver()
                solution = solver.solve(ea_input)

                # Speichere in Session State
                st.session_state['ea_input'] = ea_input
                st.session_state['geo_solution'] = solution

        # Zeige Lösung falls vorhanden
        if 'geo_solution' in st.session_state:
            solution = st.session_state['geo_solution']

            st.success(f"✅ Geometrie berechnet ({solution.method.value})")

            # Abmessungen
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Länge", f"{solution.length:.1f} m")
            with col_b:
                st.metric("Breite", f"{solution.width:.1f} m")
            with col_c:
                st.metric("Höhe", f"{solution.height:.1f} m")

            # Weitere Kennzahlen
            col_d, col_e = st.columns(2)
            with col_d:
                st.metric("Grundfläche", f"{solution.floor_area:.0f} m²")
                st.metric("Geschosshöhe", f"{solution.floor_height:.2f} m")
            with col_e:
                st.metric("Volumen", f"{solution.volume:.0f} m³")
                st.metric("A/V-Verhältnis", f"{solution.av_ratio:.2f}")

            # Konfidenz & Methode
            confidence_color = "🟢" if solution.confidence > 0.8 else "🟡" if solution.confidence > 0.6 else "🔴"
            st.info(f"{confidence_color} **Konfidenz:** {solution.confidence*100:.0f}% | **Methode:** {solution.method.value}")

            # Warnungen
            if solution.warnings:
                with st.expander("⚠️ Warnungen", expanded=True):
                    for warning in solution.warnings:
                        st.warning(warning)

            st.markdown("---")

            # IDF-Generierung
            st.subheader("🏗️ 5-Zone-IDF Generierung")

            if st.button("🚀 5-Zone-IDF erstellen", type="primary"):
                with st.spinner("Erstelle 5-Zone-Modell..."):
                    try:
                        # Debug-Info
                        from core.config import get_config
                        import os
                        config = get_config()

                        with st.expander("🔍 Debug-Info", expanded=False):
                            st.code(f"""
Installation Path (config): {config.energyplus.installation_path}
Working Directory: {os.getcwd()}
Python Executable: {sys.executable}
Platform: {os.name}
                            """)

                        generator = FiveZoneGenerator()

                        output_dir = Path(__file__).parent.parent.parent.parent / "output" / "energieausweis"
                        output_dir.mkdir(parents=True, exist_ok=True)
                        output_path = output_dir / "gebaeude_5zone.idf"

                        idf = generator.create_from_energieausweis(
                            ea_data=ea_input,
                            output_path=output_path
                        )

                        # Statistiken
                        zones = idf.idfobjects["ZONE"]
                        surfaces = idf.idfobjects["BUILDINGSURFACE:DETAILED"]
                        windows = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]

                        st.success(f"✅ IDF erstellt: `{output_path.name}`")

                        # Session State für nachfolgende Pages
                        st.session_state['idf'] = idf
                        st.session_state['idf_path'] = output_path
                        st.session_state['geometry_source'] = 'energieausweis'

                        # BuildingModel erstellen und speichern
                        geo_solution = st.session_state.get('geo_solution')
                        if geo_solution:
                            building_model = BuildingModel.from_energieausweis(
                                geo_solution=geo_solution,
                                ea_data=ea_input,
                                idf_path=output_path,
                                num_zones=len(zones)
                            )
                            save_building_model_to_session(st.session_state, building_model)

                        # Statistiken anzeigen
                        col_s1, col_s2, col_s3 = st.columns(3)
                        with col_s1:
                            st.metric("Zonen", len(zones))
                        with col_s2:
                            st.metric("Surfaces", len(surfaces))
                        with col_s3:
                            st.metric("Fenster", len(windows))

                        # Zonen-Liste
                        with st.expander("📋 Zonen-Liste"):
                            for i, zone in enumerate(zones, 1):
                                st.text(f"{i}. {zone.Name}")

                        st.info("➡️ Gehen Sie zur **HVAC-Seite**, um das Heiz-/Kühlsystem hinzuzufügen.")

                    except Exception as e:
                        st.error(f"❌ Fehler beim Erstellen: {e}")
                        import traceback
                        with st.expander("🐛 Fehlerdetails"):
                            st.code(traceback.format_exc())

        else:
            st.info("👆 Klicken Sie auf 'Geometrie berechnen', um die Gebäudeabmessungen zu ermitteln.")

    except Exception as e:
        st.error(f"❌ Validierungsfehler: {e}")
        validation_ok = False

# ============================================================================
# FOOTER: BEISPIELE & HILFE
# ============================================================================

st.markdown("---")

with st.expander("💡 Beispieldaten"):
    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
        st.markdown("**Einfamilienhaus (EFH) Neubau 2010**")
        st.code("""
Nettofläche: 150 m²
Wandfläche: 240 m²
Dachfläche: 80 m²
Geschosse: 2
U-Wand: 0.28 W/m²K
U-Dach: 0.20 W/m²K
U-Fenster: 1.30 W/m²K
Fenster Nord: 8 m²
Fenster Süd: 20 m²
        """)

    with col_ex2:
        st.markdown("**Mehrfamilienhaus (MFH) saniert 1980**")
        st.code("""
Nettofläche: 800 m²
Wandfläche: 950 m²
Dachfläche: 280 m²
Geschosse: 3
U-Wand: 0.35 W/m²K
U-Dach: 0.25 W/m²K
U-Fenster: 1.50 W/m²K
WWR: 30%
        """)

st.caption("* Pflichtfelder | 🤖 Powered by Claude Code")
