"""Zone Generator für thermische Zonen.

Erstellt ZONE-Objekte aus ZoneLayout-Geometrien.
Jede Zone repräsentiert einen thermisch gekoppelten Raum im Gebäude.
"""

from typing import Any, Dict, List

from ..models import ZoneInfo, create_zone_info_from_idf_object


class ZoneGenerator:
    """Generiert thermische Zonen für EnergyPlus IDFs.

    Die Hauptaufgabe ist, aus ZoneLayout-Geometrien (von PerimeterCalculator)
    ZONE-Objekte zu erstellen mit korrekten Koordinaten und Eigenschaften.
    """

    def add_zones(
        self,
        idf: Any,
        layouts: Dict[int, Any]  # Dict[int, ZoneLayout]
    ) -> List[ZoneInfo]:
        """Erstellt alle thermischen Zonen.

        Args:
            idf: eppy IDF-Objekt
            layouts: Dictionary {floor_number: ZoneLayout}
                    von PerimeterCalculator.create_multi_floor_layout()

        Returns:
            Liste von ZoneInfo-Objekten mit Metadaten über erstellte Zonen

        Note:
            - SIZING:ZONE wird NICHT erstellt (IdealLoads braucht kein Sizing)
            - Zone Naming Convention: {orientation}_{floor} (z.B. "Perimeter_North_F1", "Core_F2")
            - Floor_Area wird leer gelassen (EnergyPlus berechnet automatisch aus Surfaces)
        """
        zone_infos = []

        for floor_num, layout in layouts.items():
            for orient, zone_geom in layout.all_zones.items():
                # Erstelle ZONE-Objekt
                idf_zone = idf.newidfobject(
                    "ZONE",
                    Name=zone_geom.name,
                    Direction_of_Relative_North=0,  # Orientation via surface coords
                    X_Origin=zone_geom.x_origin,
                    Y_Origin=zone_geom.y_origin,
                    Z_Origin=zone_geom.z_origin,
                    Type="",  # Leer = Standard thermal zone
                    Multiplier=1,  # Jede Zone wird einmal berechnet
                    Ceiling_Height=zone_geom.height,
                    Volume=zone_geom.volume,
                    Floor_Area="",  # Leer = Auto-calculate from surfaces
                    Zone_Inside_Convection_Algorithm="",  # Default
                    Zone_Outside_Convection_Algorithm="",  # Default
                    Part_of_Total_Floor_Area="Yes",  # Zählt zur Gesamt-NGF
                )

                # Erstelle ZoneInfo für Tracking
                zone_info = ZoneInfo(
                    name=zone_geom.name,
                    floor=floor_num,
                    floor_area=zone_geom.floor_area,
                    volume=zone_geom.volume,
                    z_origin=zone_geom.z_origin,
                    idf_object=idf_zone
                )
                zone_infos.append(zone_info)

        return zone_infos

    def get_zone_by_name(
        self,
        zone_infos: List[ZoneInfo],
        name: str
    ) -> ZoneInfo:
        """Findet ZoneInfo nach Name.

        Args:
            zone_infos: Liste von ZoneInfo-Objekten
            name: Zone-Name

        Returns:
            ZoneInfo-Objekt

        Raises:
            ValueError: Falls Zone nicht gefunden
        """
        for zone in zone_infos:
            if zone.name == name:
                return zone

        raise ValueError(f"Zone '{name}' not found in zone_infos")

    def get_zones_by_floor(
        self,
        zone_infos: List[ZoneInfo],
        floor: int
    ) -> List[ZoneInfo]:
        """Findet alle Zonen eines Geschosses.

        Args:
            zone_infos: Liste von ZoneInfo-Objekten
            floor: Geschoss-Nummer (0-basiert)

        Returns:
            Liste von ZoneInfo-Objekten für dieses Geschoss
        """
        return [z for z in zone_infos if z.floor == floor]

    def validate_zones(
        self,
        zone_infos: List[ZoneInfo],
        expected_zones_per_floor: int = 5
    ) -> List[str]:
        """Validiert Zone-Konfiguration.

        Args:
            zone_infos: Liste von ZoneInfo-Objekten
            expected_zones_per_floor: Erwartete Anzahl Zonen pro Geschoss

        Returns:
            Liste von Warnungen (leer = alles OK)
        """
        warnings = []

        # Gruppiere nach Floors
        floors = {}
        for zone in zone_infos:
            floors.setdefault(zone.floor, []).append(zone)

        # Prüfe Anzahl pro Floor
        for floor, zones in floors.items():
            if len(zones) != expected_zones_per_floor:
                warnings.append(
                    f"Floor {floor}: Expected {expected_zones_per_floor} zones, "
                    f"got {len(zones)}"
                )

        # Prüfe Z-Koordinaten (sollten aufsteigend sein)
        sorted_floors = sorted(floors.keys())
        for i, floor in enumerate(sorted_floors):
            zones = floors[floor]
            z_coords = [z.z_origin for z in zones]
            min_z, max_z = min(z_coords), max(z_coords)

            # Alle Zonen eines Floors sollten gleiche Z-Koordinate haben
            if max_z - min_z > 0.01:  # Toleranz für Floating Point
                warnings.append(
                    f"Floor {floor}: Zones have different Z-coordinates "
                    f"({min_z:.2f} - {max_z:.2f})"
                )

        return warnings
