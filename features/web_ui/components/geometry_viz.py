"""3D-Visualisierung für Gebäudegeometrie."""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional, List, Tuple


def create_3d_building_visualization(
    length: float,
    width: float,
    height: float,
    num_floors: int,
    title: str = "Gebäude 3D-Ansicht"
) -> go.Figure:
    """
    Erstellt eine 3D-Plotly-Visualisierung eines Gebäudes.

    Args:
        length: Länge des Gebäudes in Metern
        width: Breite des Gebäudes in Metern
        height: Gesamthöhe des Gebäudes in Metern
        num_floors: Anzahl der Stockwerke
        title: Titel für die Visualisierung

    Returns:
        Plotly Figure-Objekt
    """
    # Stockwerkshöhe berechnen
    floor_height = height / num_floors

    # Definiere die 8 Eckpunkte des Gebäudes
    vertices = [
        [0, 0, 0],           # 0: unten-vorne-links
        [length, 0, 0],      # 1: unten-vorne-rechts
        [length, width, 0],  # 2: unten-hinten-rechts
        [0, width, 0],       # 3: unten-hinten-links
        [0, 0, height],      # 4: oben-vorne-links
        [length, 0, height], # 5: oben-vorne-rechts
        [length, width, height], # 6: oben-hinten-rechts
        [0, width, height],  # 7: oben-hinten-links
    ]

    # Definiere die 6 Flächen (als Dreiecke)
    faces = [
        # Boden (2 Dreiecke)
        [0, 1, 2], [0, 2, 3],
        # Decke (2 Dreiecke)
        [4, 6, 5], [4, 7, 6],
        # Vorderseite (2 Dreiecke)
        [0, 5, 1], [0, 4, 5],
        # Rückseite (2 Dreiecke)
        [2, 7, 3], [2, 6, 7],
        # Linke Seite (2 Dreiecke)
        [0, 3, 7], [0, 7, 4],
        # Rechte Seite (2 Dreiecke)
        [1, 5, 6], [1, 6, 2],
    ]

    # Extrahiere x, y, z Koordinaten
    x, y, z = zip(*vertices)
    i, j, k = zip(*faces)

    # Erstelle 3D Mesh
    fig = go.Figure(data=[
        go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            color='lightblue',
            opacity=0.7,
            name='Gebäude',
            showscale=False,
        )
    ])

    # Füge Stockwerk-Linien hinzu
    for floor in range(1, num_floors):
        floor_z = floor * floor_height
        fig.add_trace(go.Scatter3d(
            x=[0, length, length, 0, 0],
            y=[0, 0, width, width, 0],
            z=[floor_z, floor_z, floor_z, floor_z, floor_z],
            mode='lines',
            line=dict(color='red', width=3),
            name=f'Stockwerk {floor}',
            showlegend=False,
        ))

    # Layout anpassen
    fig.update_layout(
        scene=dict(
            xaxis_title='Länge (m)',
            yaxis_title='Breite (m)',
            zaxis_title='Höhe (m)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        title=title,
    )

    return fig


def render_building_preview(
    geo_data: Optional[Dict[str, Any]] = None,
    session_state_key: str = 'visualization_data'
) -> None:
    """
    Rendert eine Gebäudevorschau basierend auf Session State oder übergebenen Daten.

    Args:
        geo_data: Optional - Dict mit 'length', 'width', 'height', 'num_floors'
        session_state_key: Key im Session State für Geometrie-Daten
    """
    # Hole Daten aus Session State oder Parameter
    data = geo_data or st.session_state.get(session_state_key)

    if not data:
        st.info("🏗️ Keine Geometrie-Daten verfügbar. Bitte erst Geometrie definieren.")
        return

    # Extrahiere Werte
    try:
        length = data['length']
        width = data['width']
        height = data['height']
        num_floors = data['num_floors']

        # Erstelle Visualisierung
        fig = create_3d_building_visualization(
            length=length,
            width=width,
            height=height,
            num_floors=num_floors
        )

        # Zeige in Streamlit
        st.plotly_chart(fig, use_container_width=True)

        # Hilfe-Text
        st.caption("💡 **Tipp:** Sie können die 3D-Ansicht mit der Maus drehen, zoomen und verschieben.")

    except KeyError as e:
        st.error(f"❌ Fehlende Geometrie-Daten: {e}")
    except Exception as e:
        st.error(f"❌ Fehler bei Visualisierung: {e}")


# ============================================================================
# ERWEITERTE VISUALISIERUNGEN (2D-Grundriss, Fassaden, Zonen)
# ============================================================================

def create_2d_floorplan(
    length: float,
    width: float,
    zone_layout: Optional[Dict[str, Any]] = None,
    title: str = "Grundriss (2D von oben)"
) -> go.Figure:
    """
    Erstellt einen 2D-Grundriss mit optionaler Zonen-Darstellung.

    Args:
        length: Gebäudelänge (X-Achse) in Metern
        width: Gebäudebreite (Y-Achse) in Metern
        zone_layout: Optional - Dictionary mit Zonendaten für 5-Zone-Modell
        title: Titel der Visualisierung

    Returns:
        Plotly Figure-Objekt
    """
    fig = go.Figure()

    # Farben für Zonen
    zone_colors = {
        'north': 'rgba(255, 100, 100, 0.6)',  # Rot
        'south': 'rgba(100, 255, 100, 0.6)',  # Grün
        'east': 'rgba(100, 100, 255, 0.6)',   # Blau
        'west': 'rgba(255, 255, 100, 0.6)',   # Gelb
        'core': 'rgba(200, 200, 200, 0.6)',   # Grau
    }

    if zone_layout:
        # 5-Zone-Modell: Zeichne Zonen
        for zone_name, zone_data in zone_layout.items():
            x0 = zone_data['x_origin']
            y0 = zone_data['y_origin']
            zone_length = zone_data['length']
            zone_width = zone_data['width']

            # Rechteck für Zone
            fig.add_trace(go.Scatter(
                x=[x0, x0 + zone_length, x0 + zone_length, x0, x0],
                y=[y0, y0, y0 + zone_width, y0 + zone_width, y0],
                fill='toself',
                fillcolor=zone_colors.get(zone_name, 'rgba(150, 150, 150, 0.5)'),
                line=dict(color='black', width=2),
                name=zone_name.capitalize(),
                hovertemplate=f"<b>{zone_name.capitalize()}</b><br>" +
                             f"Fläche: {zone_data.get('floor_area', zone_length * zone_width):.1f} m²<br>" +
                             f"Dimensionen: {zone_length:.1f}m × {zone_width:.1f}m<extra></extra>"
            ))
    else:
        # SimpleBox: Nur Außenkontur
        fig.add_trace(go.Scatter(
            x=[0, length, length, 0, 0],
            y=[0, 0, width, width, 0],
            fill='toself',
            fillcolor='rgba(173, 216, 230, 0.5)',
            line=dict(color='black', width=3),
            name='Gebäude',
            hovertemplate=f"<b>Gebäude</b><br>" +
                         f"Fläche: {length * width:.1f} m²<br>" +
                         f"Dimensionen: {length:.1f}m × {width:.1f}m<extra></extra>"
        ))

    # Orientierungs-Pfeile
    arrow_length = max(length, width) * 0.15

    # Nord-Pfeil
    fig.add_annotation(
        x=length/2, y=width + arrow_length * 0.3,
        ax=length/2, ay=width + arrow_length,
        xref="x", yref="y",
        axref="x", ayref="y",
        showarrow=True,
        arrowhead=2,
        arrowsize=2,
        arrowwidth=3,
        arrowcolor="red",
    )
    fig.add_annotation(
        x=length/2, y=width + arrow_length * 1.2,
        text="<b>N</b>",
        showarrow=False,
        font=dict(size=16, color="red"),
    )

    # Layout
    fig.update_layout(
        title=title,
        xaxis_title='Länge (Ost) [m]',
        yaxis_title='Breite (Nord) [m]',
        xaxis=dict(scaleanchor="y", scaleratio=1),
        yaxis=dict(scaleanchor="x", scaleratio=1),
        height=600,
        showlegend=True,
        hovermode='closest',
    )

    return fig


def create_elevation_views(
    length: float,
    width: float,
    height: float,
    num_floors: int,
    window_data: Optional[Dict[str, Any]] = None,
    title: str = "Fassaden-Ansichten"
) -> go.Figure:
    """
    Erstellt realistische Fassaden-Ansichten (Nord/Ost/Süd/West) mit Fenstern.

    Args:
        length: Gebäudelänge in Metern
        width: Gebäudebreite in Metern
        height: Gesamthöhe in Metern
        num_floors: Anzahl Stockwerke
        window_data: Optional - Dict mit:
            - 'wall_areas': Dict[str, float] - Wandflächen pro Orientierung
            - 'window_areas': Dict[str, float] - Fensterflächen pro Orientierung (m²)
            - 'orientation_wwr': Dict[str, float] - WWR pro Orientierung
        title: Titel der Visualisierung

    Returns:
        Plotly Figure mit 4 Subplots (N/O/S/W)
    """
    floor_height = height / num_floors

    # Erstelle 2x2 Subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Nord-Fassade', 'Ost-Fassade', 'Süd-Fassade', 'West-Fassade'),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )

    # Typische Fenster-Dimensionen (Standard-Fenster)
    TYPICAL_WINDOW_WIDTH = 1.2  # m
    TYPICAL_WINDOW_HEIGHT = 1.5  # m
    WINDOW_SILL_HEIGHT = 0.9  # m (Brüstungshöhe)
    MIN_WINDOW_SPACING = 0.6  # m (Mindestabstand zwischen Fenstern)

    # Extrahiere Fenster-Daten falls vorhanden
    has_window_data = (window_data and 'window_areas' in window_data and 'wall_areas' in window_data)

    # Nord & Süd: Länge x Höhe
    # Ost & West: Breite x Höhe
    elevations = [
        {'name': 'Nord', 'key': 'north', 'facade_width': length, 'row': 1, 'col': 1},
        {'name': 'Ost', 'key': 'east', 'facade_width': width, 'row': 1, 'col': 2},
        {'name': 'Süd', 'key': 'south', 'facade_width': length, 'row': 2, 'col': 1},
        {'name': 'West', 'key': 'west', 'facade_width': width, 'row': 2, 'col': 2},
    ]

    for elev in elevations:
        facade_width = elev['facade_width']
        row = elev['row']
        col = elev['col']
        orientation_key = elev['key']

        # === AUSSENWAND ===
        fig.add_trace(go.Scatter(
            x=[0, facade_width, facade_width, 0, 0],
            y=[0, 0, height, height, 0],
            fill='toself',
            fillcolor='rgba(200, 200, 200, 0.7)',
            line=dict(color='black', width=2),
            name=f'{elev["name"]}-Wand',
            showlegend=False,
            hoverinfo='skip'
        ), row=row, col=col)

        # === STOCKWERK-LINIEN ===
        for floor in range(1, num_floors):
            floor_z = floor * floor_height
            fig.add_trace(go.Scatter(
                x=[0, facade_width],
                y=[floor_z, floor_z],
                mode='lines',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False,
                hoverinfo='skip'
            ), row=row, col=col)

        # === FENSTER BERECHNEN ===
        if has_window_data:
            # Realistische Fenster-Berechnung basierend auf tatsächlichen Daten
            total_window_area = window_data['window_areas'].get(orientation_key, 0.0)
            wall_area = window_data['wall_areas'].get(orientation_key, facade_width * height)
            orientation_wwr = window_data.get('orientation_wwr', {}).get(orientation_key, 0.0)

            if total_window_area > 0:
                # Fensterfläche pro Geschoss
                window_area_per_floor = total_window_area / num_floors

                # Berechne Anzahl Fenster pro Geschoss
                typical_window_area = TYPICAL_WINDOW_WIDTH * TYPICAL_WINDOW_HEIGHT  # 1.8 m²
                num_windows_per_floor = max(1, round(window_area_per_floor / typical_window_area))

                # Passe Fensterbreite an, um tatsächliche Fläche zu erreichen
                # Fensterhöhe bleibt konstant, Breite wird angepasst
                available_height_for_window = min(TYPICAL_WINDOW_HEIGHT, floor_height - WINDOW_SILL_HEIGHT - 0.3)
                window_height = available_height_for_window

                # Gesamtbreite aller Fenster
                total_windows_width = window_area_per_floor / window_height
                window_width = total_windows_width / num_windows_per_floor

                # Prüfe ob Fenster in Fassade passen
                total_width_needed = num_windows_per_floor * window_width + (num_windows_per_floor - 1) * MIN_WINDOW_SPACING
                if total_width_needed > facade_width * 0.95:  # Max 95% der Fassadenbreite
                    # Reduziere Anzahl Fenster
                    num_windows_per_floor = max(1, int((facade_width * 0.95) / (window_width + MIN_WINDOW_SPACING)))
                    window_width = window_area_per_floor / (window_height * num_windows_per_floor)

                # Berechne gleichmäßigen Abstand
                total_window_width = num_windows_per_floor * window_width
                spacing = (facade_width - total_window_width) / (num_windows_per_floor + 1)

                # Zeichne Fenster pro Geschoss
                for floor in range(num_floors):
                    floor_base_z = floor * floor_height
                    window_base_z = floor_base_z + WINDOW_SILL_HEIGHT

                    for win_num in range(num_windows_per_floor):
                        win_x0 = (win_num + 1) * spacing + win_num * window_width
                        win_x1 = win_x0 + window_width

                        # Fenster-Rechteck
                        fig.add_trace(go.Scatter(
                            x=[win_x0, win_x1, win_x1, win_x0, win_x0],
                            y=[window_base_z, window_base_z,
                               window_base_z + window_height,
                               window_base_z + window_height,
                               window_base_z],
                            fill='toself',
                            fillcolor='rgba(100, 150, 255, 0.6)',
                            line=dict(color='darkblue', width=1),
                            showlegend=False,
                            hovertemplate=(
                                f"<b>Fenster {win_num+1}</b><br>"
                                f"Geschoss: {floor+1}<br>"
                                f"Größe: {window_width:.2f}m × {window_height:.2f}m<br>"
                                f"Fläche: {window_width * window_height:.2f} m²"
                                f"<extra></extra>"
                            )
                        ), row=row, col=col)

                # Info-Text für diese Fassade
                info_text = (
                    f"WWR: {orientation_wwr*100:.1f}%<br>"
                    f"Fenster: {total_window_area:.1f} m² ({num_windows_per_floor*num_floors} Stk.)"
                )

            else:
                # Keine Fenster für diese Orientierung
                info_text = "Keine Fenster"

        else:
            # Fallback: Einfache WWR-basierte Darstellung
            default_wwr = window_data.get('window_wall_ratio', 0.3) if window_data else 0.3
            num_windows_per_floor = 3
            window_spacing = facade_width / (num_windows_per_floor + 1)
            window_width = min(TYPICAL_WINDOW_WIDTH, facade_width * 0.15)
            window_height = min(TYPICAL_WINDOW_HEIGHT, floor_height * 0.6)

            for floor in range(num_floors):
                floor_base_z = floor * floor_height
                window_base_z = floor_base_z + WINDOW_SILL_HEIGHT

                for win_num in range(num_windows_per_floor):
                    win_x_center = (win_num + 1) * window_spacing
                    win_x0 = win_x_center - window_width / 2
                    win_x1 = win_x_center + window_width / 2

                    fig.add_trace(go.Scatter(
                        x=[win_x0, win_x1, win_x1, win_x0, win_x0],
                        y=[window_base_z, window_base_z,
                           window_base_z + window_height,
                           window_base_z + window_height,
                           window_base_z],
                        fill='toself',
                        fillcolor='rgba(100, 150, 255, 0.6)',
                        line=dict(color='darkblue', width=1),
                        showlegend=False,
                        hovertemplate=f"<b>Fenster</b><br>Geschoss {floor+1}<extra></extra>"
                    ), row=row, col=col)

            info_text = f"WWR: {default_wwr*100:.0f}% (vereinfacht)"

        # Achsen-Labels
        fig.update_xaxes(title_text="Breite [m]", row=row, col=col)
        fig.update_yaxes(title_text="Höhe [m]", row=row, col=col)

    fig.update_layout(
        title_text=title,
        height=800,
        showlegend=False,
    )

    return fig


def create_3d_building_with_zones(
    length: float,
    width: float,
    height: float,
    num_floors: int,
    zone_layout: Optional[Any] = None,
    title: str = "3D-Ansicht mit Zonen"
) -> go.Figure:
    """
    Erstellt 3D-Visualisierung mit farblich unterschiedenen Zonen.

    Args:
        length: Gebäudelänge in Metern
        width: Gebäudebreite in Metern
        height: Gesamthöhe in Metern
        num_floors: Anzahl Stockwerke
        zone_layout: Optional - Dict (für einzelnes Geschoss) oder List (für alle Geschosse)
        title: Titel der Visualisierung

    Returns:
        Plotly Figure-Objekt
    """
    fig = go.Figure()

    # Farben für Zonen (transparenter für 3D)
    zone_colors = {
        'north': 'rgba(255, 100, 100, 0.5)',
        'south': 'rgba(100, 255, 100, 0.5)',
        'east': 'rgba(100, 100, 255, 0.5)',
        'west': 'rgba(255, 255, 100, 0.5)',
        'core': 'rgba(200, 200, 200, 0.4)',
    }

    floor_height = height / num_floors

    if zone_layout:
        # Prüfe ob zone_layout eine Liste (alle Geschosse) oder Dict (ein Geschoss) ist
        zones_to_draw = []

        if isinstance(zone_layout, list):
            # Liste von Zonen (alle Geschosse)
            zones_to_draw = zone_layout
        elif isinstance(zone_layout, dict):
            # Dict von Zonen (nur ein Geschoss) - konvertiere zu Liste
            for zone_name, zone_data in zone_layout.items():
                zones_to_draw.append({
                    'zone_name': zone_name,
                    **zone_data
                })

        # Zeichne alle Zonen
        for zone_info in zones_to_draw:
            zone_name = zone_info.get('zone_name', 'unknown')
            x0 = zone_info['x_origin']
            y0 = zone_info['y_origin']
            z0 = zone_info['z_origin']
            zl = zone_info['length']  # zone length
            zw = zone_info['width']   # zone width
            zh = zone_info['height']  # zone height

            # 8 Eckpunkte der Zone
            vertices = [
                [x0, y0, z0],
                [x0 + zl, y0, z0],
                [x0 + zl, y0 + zw, z0],
                [x0, y0 + zw, z0],
                [x0, y0, z0 + zh],
                [x0 + zl, y0, z0 + zh],
                [x0 + zl, y0 + zw, z0 + zh],
                [x0, y0 + zw, z0 + zh],
            ]

            # Flächen
            faces = [
                [0, 1, 2], [0, 2, 3],  # Boden
                [4, 6, 5], [4, 7, 6],  # Decke
                [0, 5, 1], [0, 4, 5],  # Süd
                [2, 7, 3], [2, 6, 7],  # Nord
                [0, 3, 7], [0, 7, 4],  # West
                [1, 5, 6], [1, 6, 2],  # Ost
            ]

            x, y, z = zip(*vertices)
            i, j, k = zip(*faces)

            # Zeige nur eine Legende pro Zonen-Typ (nicht für jedes Geschoss)
            floor_num = zone_info.get('floor', 0)
            show_legend = (floor_num == 0)  # Nur für erstes Geschoss Legende zeigen

            fig.add_trace(go.Mesh3d(
                x=x, y=y, z=z,
                i=i, j=j, k=k,
                color=zone_colors.get(zone_name, 'rgba(150, 150, 150, 0.5)'),
                opacity=0.6,
                name=zone_name.capitalize(),
                legendgroup=zone_name,  # Gruppiere nach Zonen-Typ
                showlegend=show_legend,  # Nur einmal zeigen
                hovertemplate=f"<b>{zone_name.capitalize()} - Geschoss {floor_num+1}</b><br>" +
                             f"Fläche: {zone_info.get('floor_area', zl * zw):.1f} m²<extra></extra>"
            ))
    else:
        # SimpleBox: Einzelner Quader
        vertices = [
            [0, 0, 0],
            [length, 0, 0],
            [length, width, 0],
            [0, width, 0],
            [0, 0, height],
            [length, 0, height],
            [length, width, height],
            [0, width, height],
        ]

        faces = [
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 5, 1], [0, 4, 5],
            [2, 7, 3], [2, 6, 7],
            [0, 3, 7], [0, 7, 4],
            [1, 5, 6], [1, 6, 2],
        ]

        x, y, z = zip(*vertices)
        i, j, k = zip(*faces)

        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            color='lightblue',
            opacity=0.7,
            name='Gebäude',
            showscale=False,
        ))

    # Stockwerk-Linien
    for floor in range(1, num_floors):
        floor_z = floor * floor_height
        fig.add_trace(go.Scatter3d(
            x=[0, length, length, 0, 0],
            y=[0, 0, width, width, 0],
            z=[floor_z, floor_z, floor_z, floor_z, floor_z],
            mode='lines',
            line=dict(color='red', width=3),
            name=f'Stockwerk {floor}',
            showlegend=False,
        ))

    # Layout
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title='Länge (m)',
            yaxis_title='Breite (m)',
            zaxis_title='Höhe (m)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        height=700,
        showlegend=True,
    )

    return fig
