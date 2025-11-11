"""Geometrie-Seite für Gebäudeparameter."""

import streamlit as st
import plotly.graph_objects as go
import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from features.geometrie.box_generator import BuildingGeometry

st.set_page_config(
    page_title="Geometrie - Gebäudesimulation",
    page_icon="🏗️",
    layout="wide",
)

st.title("🏗️ Gebäudegeometrie")
st.markdown("---")

# Info-Box
st.info("""
**Hinweis:** Definieren Sie hier die Grundparameter Ihres Gebäudes.
Die 3D-Vorschau aktualisiert sich automatisch.
""")

# Zwei Spalten: Eingabe links, Vorschau rechts
col_input, col_preview = st.columns([1, 2])

with col_input:
    st.subheader("📐 Parameter")

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

# Erstelle Geometrie-Objekt
geometry = BuildingGeometry(
    length=length,
    width=width,
    height=height,
    num_floors=num_floors,
    window_wall_ratio=window_wall_ratio,
    orientation=orientation,
)

# Speichere in Session State
st.session_state['geometry'] = geometry

# Berechne Kennzahlen
total_area = geometry.total_floor_area
wall_area = 2 * (length + width) * height
window_area = wall_area * window_wall_ratio
volume = length * width * height

with col_input:
    st.markdown("---")
    st.subheader("📊 Kennzahlen")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nettogrundfläche", f"{total_area:.1f} m²")
        st.metric("Wandfläche", f"{wall_area:.1f} m²")
    with col2:
        st.metric("Volumen", f"{volume:.1f} m³")
        st.metric("Fensterfläche", f"{window_area:.1f} m²")

with col_preview:
    st.subheader("👁️ 3D-Vorschau")

    # Erstelle 3D-Box mit Plotly
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
    )

    st.plotly_chart(fig, use_container_width=True)

    # Zusätzliche Hinweise
    st.caption("💡 **Tipp:** Sie können die 3D-Ansicht mit der Maus drehen, zoomen und verschieben.")

# Navigation
st.markdown("---")
st.markdown("### ➡️ Nächster Schritt")
st.markdown("Gehen Sie zur **HVAC-Seite** im Menü links, um das Heizungs-/Kühlsystem zu konfigurieren.")

# Zeige aktuelle Konfiguration
with st.expander("🔍 Aktuelle Konfiguration (JSON)"):
    import json
    config_dict = {
        "length": length,
        "width": width,
        "height": height,
        "num_floors": num_floors,
        "window_wall_ratio": window_wall_ratio,
        "orientation": orientation,
        "total_floor_area": total_area,
        "volume": volume,
    }
    st.json(config_dict)
