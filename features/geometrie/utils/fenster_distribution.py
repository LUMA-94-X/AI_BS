"""Fensterverteilung auf Orientierungen."""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

from features.geometrie.models.energieausweis_input import (
    FensterData,
    GebaeudeTyp
)


class Orientation(str, Enum):
    """Himmelsrichtungen."""

    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


@dataclass
class OrientationWWR:
    """Window-to-Wall Ratio pro Orientierung."""

    north: float  # 0.0 - 1.0
    east: float
    south: float
    west: float

    @property
    def average(self) -> float:
        """Durchschnittlicher WWR."""
        return (self.north + self.east + self.south + self.west) / 4.0

    def get(self, orientation: Orientation) -> float:
        """Gibt WWR für bestimmte Orientierung zurück."""
        return getattr(self, orientation.value)


class FensterDistribution:
    """Verteilt Fensterflächen auf Orientierungen."""

    # Heuristische Verteilungen pro Gebäudetyp (falls keine exakten Daten)
    # Format: [Nord, Ost, Süd, West] als Anteil des Gesamt-WWR
    HEURISTIC_DISTRIBUTIONS = {
        GebaeudeTyp.EFH: {
            "weights": [0.15, 0.25, 0.40, 0.20],  # Süd bevorzugt
            "description": "EFH: Süd>Ost/West>Nord (Wohnkomfort)"
        },
        GebaeudeTyp.MFH: {
            "weights": [0.20, 0.27, 0.33, 0.20],  # Süd leicht bevorzugt
            "description": "MFH: Ausgewogener, Süd bevorzugt"
        },
        GebaeudeTyp.NWG: {
            "weights": [0.22, 0.28, 0.28, 0.22],  # Fast gleichmäßig
            "description": "NWG/Büro: Gleichmäßige Verteilung"
        }
    }

    def calculate_orientation_wwr(
        self,
        fenster_data: FensterData,
        wall_areas: Dict[str, float],
        gebaeudetyp: GebaeudeTyp = GebaeudeTyp.MFH
    ) -> OrientationWWR:
        """
        Berechnet WWR pro Orientierung.

        Args:
            fenster_data: Fensterdaten (exakt oder WWR)
            wall_areas: Wandflächen pro Orientierung {"north": 50.0, ...}
            gebaeudetyp: Gebäudetyp für Heuristik

        Returns:
            OrientationWWR mit WWR pro Richtung
        """

        if fenster_data.has_exact_areas:
            return self._calculate_from_exact_areas(fenster_data, wall_areas)
        else:
            return self._calculate_from_heuristic(
                fenster_data.window_wall_ratio,
                gebaeudetyp
            )

    def _calculate_from_exact_areas(
        self,
        fenster_data: FensterData,
        wall_areas: Dict[str, float]
    ) -> OrientationWWR:
        """
        Berechnet WWR aus exakten Fensterfl ächen.

        Args:
            fenster_data: Mit nord_m2, ost_m2, sued_m2, west_m2
            wall_areas: Wandflächen pro Orientierung

        Returns:
            OrientationWWR
        """

        # Sichere Division: Falls Wandfläche 0, dann WWR = 0
        def safe_wwr(fenster_m2: Optional[float], wand_m2: float) -> float:
            if fenster_m2 is None or wand_m2 == 0:
                return 0.0
            return min(fenster_m2 / wand_m2, 0.95)  # Max 95% WWR

        return OrientationWWR(
            north=safe_wwr(fenster_data.nord_m2, wall_areas.get("north", 1.0)),
            east=safe_wwr(fenster_data.ost_m2, wall_areas.get("east", 1.0)),
            south=safe_wwr(fenster_data.sued_m2, wall_areas.get("south", 1.0)),
            west=safe_wwr(fenster_data.west_m2, wall_areas.get("west", 1.0))
        )

    def _calculate_from_heuristic(
        self,
        wwr_total: float,
        gebaeudetyp: GebaeudeTyp
    ) -> OrientationWWR:
        """
        Berechnet WWR aus Heuristik basierend auf Gebäudetyp.

        Args:
            wwr_total: Gesamt-WWR (z.B. 0.3)
            gebaeudetyp: Gebäudetyp

        Returns:
            OrientationWWR mit verteilten WWR-Werten
        """

        weights = self.HEURISTIC_DISTRIBUTIONS[gebaeudetyp]["weights"]

        return OrientationWWR(
            north=wwr_total * weights[0],
            east=wwr_total * weights[1],
            south=wwr_total * weights[2],
            west=wwr_total * weights[3]
        )

    def calculate_window_areas(
        self,
        orientation_wwr: OrientationWWR,
        wall_areas: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Berechnet absolute Fensterflächen aus WWR und Wandflächen.

        Args:
            orientation_wwr: WWR pro Orientierung
            wall_areas: Wandflächen {"north": 50.0, ...}

        Returns:
            Fensterflächen {"north": 10.0, ...} in m²
        """

        return {
            "north": orientation_wwr.north * wall_areas.get("north", 0.0),
            "east": orientation_wwr.east * wall_areas.get("east", 0.0),
            "south": orientation_wwr.south * wall_areas.get("south", 0.0),
            "west": orientation_wwr.west * wall_areas.get("west", 0.0)
        }

    @staticmethod
    def estimate_wall_areas_from_geometry(
        building_length: float,
        building_width: float,
        building_height: float
    ) -> Dict[str, float]:
        """
        Schätzt Wandflächen aus Gebäudegeometrie.

        Annahme: Rechteckiges Gebäude ohne Fensterabzug

        Args:
            building_length: Länge (X-Richtung = Ost-West)
            building_width: Breite (Y-Richtung = Nord-Süd)
            building_height: Höhe

        Returns:
            Wandflächen {"north": ..., "east": ..., "south": ..., "west": ...}
        """

        return {
            "north": building_length * building_height,
            "south": building_length * building_height,
            "east": building_width * building_height,
            "west": building_width * building_height
        }


# ============ UTILITY FUNCTIONS ============

def print_window_distribution(
    orientation_wwr: OrientationWWR,
    wall_areas: Optional[Dict[str, float]] = None
) -> None:
    """Druckt Fensterverteilung."""

    print("\n" + "="*60)
    print("FENSTER-VERTEILUNG")
    print("="*60)

    print(f"\nWindow-to-Wall Ratio pro Orientierung:")
    print(f"  Nord:  {orientation_wwr.north*100:5.1f}%")
    print(f"  Ost:   {orientation_wwr.east*100:5.1f}%")
    print(f"  Süd:   {orientation_wwr.south*100:5.1f}%")
    print(f"  West:  {orientation_wwr.west*100:5.1f}%")
    print(f"  Durchschnitt: {orientation_wwr.average*100:5.1f}%")

    if wall_areas:
        dist = FensterDistribution()
        fenster_areas = dist.calculate_window_areas(orientation_wwr, wall_areas)

        print(f"\nFensterflächen (absolut):")
        print(f"  Nord:  {fenster_areas['north']:6.1f} m²  (Wand: {wall_areas['north']:6.1f} m²)")
        print(f"  Ost:   {fenster_areas['east']:6.1f} m²  (Wand: {wall_areas['east']:6.1f} m²)")
        print(f"  Süd:   {fenster_areas['south']:6.1f} m²  (Wand: {wall_areas['south']:6.1f} m²)")
        print(f"  West:  {fenster_areas['west']:6.1f} m²  (Wand: {wall_areas['west']:6.1f} m²)")

        total_fenster = sum(fenster_areas.values())
        total_wand = sum(wall_areas.values())
        print(f"  GESAMT: {total_fenster:6.1f} m²  (Wand: {total_wand:6.1f} m²)")
        print(f"  Gesamt-WWR: {total_fenster/total_wand*100:.1f}%")

    print("="*60 + "\n")


def create_example_distributions() -> Dict[GebaeudeTyp, OrientationWWR]:
    """Erstellt Beispiel-Verteilungen für alle Gebäudetypen."""

    dist = FensterDistribution()
    examples = {}

    wwr_test = 0.30  # 30% Gesamt-WWR

    for typ in GebaeudeTyp:
        examples[typ] = dist._calculate_from_heuristic(wwr_test, typ)

    return examples
