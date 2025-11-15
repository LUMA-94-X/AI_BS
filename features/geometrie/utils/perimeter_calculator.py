"""Adaptive Perimeter-Tiefe-Berechnung für 5-Zone-Modell."""

from dataclasses import dataclass
from typing import Dict, Tuple
import math


@dataclass
class ZoneGeometry:
    """Geometrie einer einzelnen Zone."""

    name: str  # z.B. "Perimeter_North_F1"
    x_origin: float  # X-Koordinate (m)
    y_origin: float  # Y-Koordinate (m)
    z_origin: float  # Z-Koordinate (m)
    length: float  # X-Dimension (m)
    width: float  # Y-Dimension (m)
    height: float  # Z-Dimension (m)

    @property
    def floor_area(self) -> float:
        """Grundfläche der Zone."""
        return self.length * self.width

    @property
    def volume(self) -> float:
        """Volumen der Zone."""
        return self.length * self.width * self.height

    @property
    def vertices_2d(self) -> Tuple[Tuple[float, float], ...]:
        """2D-Vertices (für Surface-Erstellung)."""
        x0, y0 = self.x_origin, self.y_origin
        x1 = x0 + self.length
        y1 = y0 + self.width

        # Counterclockwise (EnergyPlus-Konvention)
        return (
            (x0, y0),
            (x1, y0),
            (x1, y1),
            (x0, y1)
        )


@dataclass
class ZoneLayout:
    """Komplettes 5-Zonen-Layout für ein Stockwerk."""

    perimeter_north: ZoneGeometry
    perimeter_east: ZoneGeometry
    perimeter_south: ZoneGeometry
    perimeter_west: ZoneGeometry
    core: ZoneGeometry

    @property
    def all_zones(self) -> Dict[str, ZoneGeometry]:
        """Gibt alle Zonen als Dictionary zurück."""
        return {
            "north": self.perimeter_north,
            "east": self.perimeter_east,
            "south": self.perimeter_south,
            "west": self.perimeter_west,
            "core": self.core
        }

    @property
    def total_floor_area(self) -> float:
        """Gesamt-Grundfläche."""
        return sum(zone.floor_area for zone in self.all_zones.values())

    @property
    def perimeter_fraction(self) -> float:
        """Anteil Perimeter-Fläche (0-1)."""
        perimeter_area = (
            self.perimeter_north.floor_area +
            self.perimeter_east.floor_area +
            self.perimeter_south.floor_area +
            self.perimeter_west.floor_area
        )
        return perimeter_area / self.total_floor_area


class PerimeterCalculator:
    """Berechnet adaptive Perimeter-Tiefen für 5-Zone-Modell."""

    # Perimeter-Tiefe-Grenzen (ASHRAE/ISO-Standard)
    P_MIN = 3.0  # Minimale Perimeter-Tiefe [m]
    P_MAX = 6.0  # Maximale Perimeter-Tiefe [m]

    # WWR-Bereich für Normalisierung
    WWR_MIN = 0.1  # 10% Fensteranteil
    WWR_MAX = 0.6  # 60% Fensteranteil

    # Mindest-Kern-Fraktion (verhindert zu große Perimeter-Zonen)
    MIN_CORE_FRACTION = 0.3  # Kern sollte mind. 30% der Fläche haben

    def calculate_perimeter_depth(
        self,
        wwr: float,
        building_length: float,
        building_width: float
    ) -> float:
        """
        Berechnet adaptive Perimeter-Tiefe basierend auf WWR.

        Logik:
        - Höherer WWR → größere Perimeter-Zone (mehr Solareinfluss/Tageslicht)
        - WWR 10-20%: P ≈ 3m (Mindest-Tageslicht)
        - WWR 40-60%: P ≈ 5-6m (mehr Solareinfluss)

        Args:
            wwr: Window-to-Wall Ratio (0.0 - 1.0)
            building_length: Gebäudelänge [m]
            building_width: Gebäudebreite [m]

        Returns:
            Perimeter-Tiefe [m]
        """

        # 1. Normalisiere WWR auf 0-1
        wwr_clamped = max(self.WWR_MIN, min(self.WWR_MAX, wwr))
        wwr_norm = (wwr_clamped - self.WWR_MIN) / (self.WWR_MAX - self.WWR_MIN)

        # 2. Lineare Interpolation zwischen P_MIN und P_MAX
        p_depth_base = self.P_MIN + (self.P_MAX - self.P_MIN) * wwr_norm

        # 3. Constraint: Max 30% der kleineren Gebäudeabmessung
        max_depth_geometric = 0.3 * min(building_length, building_width)
        p_depth = min(p_depth_base, max_depth_geometric)

        # 4. Constraint: Kern-Fraktion muss >= MIN_CORE_FRACTION sein
        p_depth = self._enforce_min_core_fraction(
            p_depth,
            building_length,
            building_width
        )

        return p_depth

    def _enforce_min_core_fraction(
        self,
        p_depth: float,
        building_length: float,
        building_width: float
    ) -> float:
        """
        Stellt sicher, dass Kern mindestens MIN_CORE_FRACTION der Fläche hat.

        Returns:
            Angepasste Perimeter-Tiefe
        """

        # Berechne Kern-Fläche bei gegebener Perimeter-Tiefe
        core_length = building_length - 2 * p_depth
        core_width = building_width - 2 * p_depth

        # Falls Kern zu klein oder negativ
        if core_length <= 0 or core_width <= 0:
            # Fallback: Symmetrische Aufteilung
            p_depth = min(building_length, building_width) * 0.25
            core_length = building_length - 2 * p_depth
            core_width = building_width - 2 * p_depth

        core_area = core_length * core_width
        total_area = building_length * building_width
        core_fraction = core_area / total_area

        # FIXED: Adaptive minimum - für schmale Gebäude kleiner als P_MIN
        # Absolute Mindesttiefe: 1.5m (funktionale Untergrenze für Perimeter-Zone)
        adaptive_min = max(1.5, min(self.P_MIN, min(building_length, building_width) * 0.2))

        # Iterativ reduzieren falls Kern-Fraktion zu klein
        while core_fraction < self.MIN_CORE_FRACTION and p_depth > adaptive_min:
            p_depth *= 0.9  # Reduziere um 10%
            core_length = building_length - 2 * p_depth
            core_width = building_width - 2 * p_depth
            core_area = core_length * core_width
            core_fraction = core_area / total_area

        # Mindestens adaptive_min, aber MIN_CORE_FRACTION hat Priorität
        return max(adaptive_min, p_depth)

    def create_zone_layout(
        self,
        building_length: float,
        building_width: float,
        floor_height: float,
        floor_number: int,
        wwr: float = 0.3
    ) -> ZoneLayout:
        """
        Erstellt 5-Zonen-Layout für ein Stockwerk.

        Koordinatensystem (Draufsicht):
        Y (North)
        ↑
        │  +----------------+
        │  | North          |
        │  +---+--------+---+
        │  |W  | CORE   | E |
        │  +---+--------+---+
        │  | South          |
        │  +----------------+
        └──────────────────→ X (East)

        Args:
            building_length: Gebäudelänge (X-Richtung) [m]
            building_width: Gebäudebreite (Y-Richtung) [m]
            floor_height: Geschosshöhe [m]
            floor_number: Geschossnummer (0-basiert)
            wwr: Window-to-Wall Ratio

        Returns:
            ZoneLayout mit 5 Zonen
        """

        # 1. Berechne Perimeter-Tiefe
        p = self.calculate_perimeter_depth(wwr, building_length, building_width)

        # 2. Z-Koordinate des Stockwerks
        z_origin = floor_number * floor_height

        # 3. Kern-Dimensionen
        core_length = building_length - 2 * p
        core_width = building_width - 2 * p

        # Falls Gebäude zu klein für 5 Zonen
        if core_length <= 0 or core_width <= 0:
            raise ValueError(
                f"Gebäude zu klein für 5-Zonen-Modell "
                f"(L={building_length:.1f}m, W={building_width:.1f}m, P={p:.1f}m). "
                f"Kern-Abmessungen wären negativ."
            )

        # 4. Erstelle Zonen-Geometrien

        # NORTH Perimeter (volle Breite)
        zone_north = ZoneGeometry(
            name=f"Perimeter_North_F{floor_number+1}",
            x_origin=0.0,
            y_origin=building_width - p,  # Oben
            z_origin=z_origin,
            length=building_length,
            width=p,
            height=floor_height
        )

        # SOUTH Perimeter (volle Breite)
        zone_south = ZoneGeometry(
            name=f"Perimeter_South_F{floor_number+1}",
            x_origin=0.0,
            y_origin=0.0,  # Unten
            z_origin=z_origin,
            length=building_length,
            width=p,
            height=floor_height
        )

        # EAST Perimeter (ohne Nord/Süd-Ecken)
        zone_east = ZoneGeometry(
            name=f"Perimeter_East_F{floor_number+1}",
            x_origin=building_length - p,  # Rechts
            y_origin=p,  # Zwischen Süd und Nord
            z_origin=z_origin,
            length=p,
            width=core_width,
            height=floor_height
        )

        # WEST Perimeter (ohne Nord/Süd-Ecken)
        zone_west = ZoneGeometry(
            name=f"Perimeter_West_F{floor_number+1}",
            x_origin=0.0,  # Links
            y_origin=p,  # Zwischen Süd und Nord
            z_origin=z_origin,
            length=p,
            width=core_width,
            height=floor_height
        )

        # CORE (Kern)
        zone_core = ZoneGeometry(
            name=f"Core_F{floor_number+1}",
            x_origin=p,
            y_origin=p,
            z_origin=z_origin,
            length=core_length,
            width=core_width,
            height=floor_height
        )

        return ZoneLayout(
            perimeter_north=zone_north,
            perimeter_east=zone_east,
            perimeter_south=zone_south,
            perimeter_west=zone_west,
            core=zone_core
        )

    def create_multi_floor_layout(
        self,
        building_length: float,
        building_width: float,
        floor_height: float,
        num_floors: int,
        wwr: float = 0.3
    ) -> Dict[int, ZoneLayout]:
        """
        Erstellt 5-Zonen-Layouts für alle Stockwerke.

        Args:
            building_length: Gebäudelänge [m]
            building_width: Gebäudebreite [m]
            floor_height: Geschosshöhe [m]
            num_floors: Anzahl Geschosse
            wwr: Window-to-Wall Ratio

        Returns:
            Dictionary {floor_number: ZoneLayout}
        """

        layouts = {}
        for floor_num in range(num_floors):
            layouts[floor_num] = self.create_zone_layout(
                building_length=building_length,
                building_width=building_width,
                floor_height=floor_height,
                floor_number=floor_num,
                wwr=wwr
            )

        return layouts


# ============ UTILITY FUNCTIONS ============

def print_zone_layout_summary(layout: ZoneLayout) -> None:
    """Druckt Zusammenfassung des Zonen-Layouts."""

    print("\n" + "="*60)
    print("5-ZONEN-LAYOUT")
    print("="*60)

    for orient, zone in layout.all_zones.items():
        print(f"\n{zone.name}:")
        print(f"  Position: ({zone.x_origin:.1f}, {zone.y_origin:.1f}, {zone.z_origin:.1f}) m")
        print(f"  Dimensionen: {zone.length:.1f} × {zone.width:.1f} × {zone.height:.1f} m")
        print(f"  Grundfläche: {zone.floor_area:.1f} m²")
        print(f"  Volumen: {zone.volume:.1f} m³")

    print(f"\nGESAMT:")
    print(f"  Grundfläche: {layout.total_floor_area:.1f} m²")
    print(f"  Perimeter-Anteil: {layout.perimeter_fraction*100:.1f}%")
    print(f"  Kern-Anteil: {(1-layout.perimeter_fraction)*100:.1f}%")
    print("="*60 + "\n")
