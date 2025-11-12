"""Kennzahlen-Display für Gebäudegeometrie."""

import streamlit as st
from typing import Dict, Any, Optional


def display_geometry_metrics(
    geo_data: Dict[str, Any],
    show_advanced: bool = True
) -> None:
    """
    Zeigt Gebäude-Kennzahlen in einem strukturierten Format.

    Args:
        geo_data: Dictionary mit Geometrie-Daten
            Erforderlich: 'length', 'width', 'height', 'num_floors'
            Optional: 'wall_area', 'window_area', 'window_wall_ratio', 'floor_area', 'volume', 'av_ratio'
        show_advanced: Zeige erweiterte Metriken (A/V-Verhältnis, etc.)
    """
    try:
        # Basis-Dimensionen
        length = geo_data['length']
        width = geo_data['width']
        height = geo_data['height']
        num_floors = geo_data['num_floors']

        # Berechnete Werte (falls nicht übergeben)
        floor_area = geo_data.get('floor_area', length * width)
        total_floor_area = floor_area * num_floors
        volume = geo_data.get('volume', length * width * height)
        wall_area = geo_data.get('wall_area', 2 * (length + width) * height)

        # Fenster-Daten (optional)
        window_area = geo_data.get('window_area')
        window_wall_ratio = geo_data.get('window_wall_ratio')

        # A/V-Verhältnis (optional)
        av_ratio = geo_data.get('av_ratio')
        if av_ratio is None and wall_area and volume:
            surface_area = wall_area + 2 * floor_area  # Wände + Dach + Boden
            av_ratio = surface_area / volume if volume > 0 else 0

        # Stockwerkshöhe
        floor_height = height / num_floors

        # === ANZEIGE ===
        st.subheader("📊 Kennzahlen")

        # Dimensionen
        st.markdown("#### 📐 Abmessungen")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Länge", f"{length:.1f} m")
        with col2:
            st.metric("Breite", f"{width:.1f} m")
        with col3:
            st.metric("Höhe", f"{height:.1f} m")

        # Flächen & Volumen
        st.markdown("#### 🏗️ Flächen & Volumen")
        col4, col5 = st.columns(2)
        with col4:
            st.metric("Grundfläche", f"{floor_area:.0f} m²")
            st.metric("Nettogrundfläche", f"{total_floor_area:.0f} m²")
        with col5:
            st.metric("Volumen", f"{volume:.0f} m³")
            st.metric("Wandfläche", f"{wall_area:.0f} m²")

        # Geschosse
        col6, col7 = st.columns(2)
        with col6:
            st.metric("Anzahl Geschosse", f"{num_floors}")
        with col7:
            st.metric("Geschosshöhe", f"{floor_height:.2f} m")

        # Fenster (falls vorhanden)
        if window_area is not None or window_wall_ratio is not None:
            st.markdown("#### 🪟 Fenster")
            col8, col9 = st.columns(2)

            if window_wall_ratio is not None:
                calculated_window_area = wall_area * window_wall_ratio
                with col8:
                    st.metric("Fensterflächenanteil", f"{window_wall_ratio * 100:.0f}%")
                with col9:
                    st.metric("Fensterfläche", f"{calculated_window_area:.1f} m²")
            elif window_area is not None:
                with col8:
                    st.metric("Fensterfläche", f"{window_area:.1f} m²")
                with col9:
                    wwr_calc = window_area / wall_area if wall_area > 0 else 0
                    st.metric("Fensterflächenanteil", f"{wwr_calc * 100:.0f}%")

        # Erweiterte Metriken
        if show_advanced and av_ratio is not None:
            st.markdown("#### 📈 Erweiterte Kennzahlen")
            col10, col11 = st.columns(2)
            with col10:
                st.metric(
                    "A/V-Verhältnis",
                    f"{av_ratio:.2f}",
                    help="Verhältnis von Außenfläche zu Volumen - Niedrigere Werte = kompaktere Gebäude"
                )
            with col11:
                kompaktheit = "Sehr kompakt" if av_ratio < 0.5 else "Kompakt" if av_ratio < 0.8 else "Normal" if av_ratio < 1.2 else "Wenig kompakt"
                st.metric("Kompaktheit", kompaktheit)

    except KeyError as e:
        st.error(f"❌ Fehlende Daten für Kennzahlen: {e}")
    except Exception as e:
        st.error(f"❌ Fehler bei Kennzahlen-Berechnung: {e}")


def display_simple_metrics(length: float, width: float, height: float, num_floors: int) -> None:
    """
    Vereinfachte Metriken-Anzeige - praktisch für schnelle Vorschauen.

    Args:
        length: Länge in Metern
        width: Breite in Metern
        height: Höhe in Metern
        num_floors: Anzahl Stockwerke
    """
    geo_data = {
        'length': length,
        'width': width,
        'height': height,
        'num_floors': num_floors,
    }
    display_geometry_metrics(geo_data, show_advanced=False)
