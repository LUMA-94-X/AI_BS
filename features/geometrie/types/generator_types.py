"""Data Models für FiveZoneGenerator Refactoring.

Diese Dataclasses strukturieren die Datenflüsse zwischen den Generator-Modulen
und ermöglichen bessere Typsicherheit und Dokumentation.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from pathlib import Path


# ============================================================================
# Zone-Related Models
# ============================================================================

@dataclass
class ZoneInfo:
    """Information über eine erstellte Zone.

    Diese Klasse wird von ZoneGenerator zurückgegeben und enthält
    sowohl die Geometrie-Daten als auch die Referenz zum IDF-Objekt.
    """
    name: str
    """Zone-Name (z.B. 'Perimeter_North_F1')"""

    floor: int
    """Geschoss-Nummer (0-basiert)"""

    floor_area: float
    """Grundfläche in m²"""

    volume: float
    """Volumen in m³"""

    z_origin: float
    """Z-Koordinate des Ursprungs"""

    idf_object: Any  # eppy ZONE object
    """Referenz zum eppy IDF ZONE-Objekt"""

    def __repr__(self) -> str:
        return (
            f"ZoneInfo(name='{self.name}', floor={self.floor}, "
            f"area={self.floor_area:.1f}m², z={self.z_origin:.1f}m)"
        )


@dataclass
class SurfaceInfo:
    """Information über eine erstellte Surface.

    Diese Klasse wird optional von SurfaceGenerator zurückgegeben,
    um Tracking und Validierung zu ermöglichen.
    """
    name: str
    """Surface-Name"""

    zone_name: str
    """Name der zugehörigen Zone"""

    surface_type: str
    """Surface-Typ: Wall, Floor, Ceiling, Roof"""

    outside_boundary_condition: str
    """Außen-Randbedingung: Outdoors, Ground, Surface, Adiabatic"""

    boundary_object: Optional[str] = None
    """Name der Boundary-Surface (bei inter-zone walls)"""

    area: float = 0.0
    """Fläche in m²"""

    has_window: bool = False
    """Hat diese Surface ein Fenster?"""

    def __repr__(self) -> str:
        return (
            f"SurfaceInfo(name='{self.name}', type={self.surface_type}, "
            f"area={self.area:.1f}m²)"
        )


@dataclass
class WindowInfo:
    """Information über ein erstelltes Fenster."""
    name: str
    """Fenster-Name"""

    parent_surface: str
    """Name der Parent-Surface"""

    area: float
    """Fensterfläche in m²"""

    wwr: float
    """Window-Wall-Ratio für diese Wand"""

    orientation: str
    """Orientierung: North, East, South, West"""


# ============================================================================
# Metadata & Settings Models
# ============================================================================

@dataclass
class MetadataConfig:
    """Konfiguration für Simulation-Metadaten.

    Diese Klasse erlaubt es, Simulation-Parameter zu konfigurieren,
    die an MetadataGenerator übergeben werden.
    """
    timestep: int = 4
    """Anzahl Timesteps pro Stunde (Standard: 4 = 15-Minuten-Intervalle)"""

    run_period_start: str = "01/01"
    """Start-Datum der Simulation (MM/DD)"""

    run_period_end: str = "12/31"
    """End-Datum der Simulation (MM/DD)"""

    include_design_days: bool = True
    """Sollen Design Days (Heating/Cooling) eingeschlossen werden?"""

    warmup_days: int = 25
    """Anzahl Warmup-Tage vor Simulation-Start"""

    building_name: str = "5Zone_Building_From_Energieausweis"
    """Name des Gebäudes im IDF"""

    terrain: str = "Suburbs"
    """Terrain-Typ für Wind-Berechnung: Country, Suburbs, City, Ocean"""

    solar_distribution: str = "FullExteriorWithReflections"
    """Solar-Distribution-Methode"""

    def __repr__(self) -> str:
        return (
            f"MetadataConfig(timestep={self.timestep}, "
            f"period={self.run_period_start}-{self.run_period_end})"
        )


@dataclass
class OutputVariable:
    """Definition einer Output-Variable für EnergyPlus."""
    key: str
    """Variable Key (z.B. '*' für alle Zonen)"""

    variable_name: str
    """Variable Name (z.B. 'Zone Mean Air Temperature')"""

    reporting_frequency: str = "Hourly"
    """Reporting-Frequenz: Timestep, Hourly, Daily, Monthly, RunPeriod"""

    def to_idf_args(self) -> Dict[str, str]:
        """Konvertiert zu IDF-Argumenten."""
        return {
            "Key_Value": self.key,
            "Variable_Name": self.variable_name,
            "Reporting_Frequency": self.reporting_frequency
        }


@dataclass
class OutputConfig:
    """Konfiguration für Output-Variablen."""
    variables: List[OutputVariable] = field(default_factory=list)
    """Liste der gewünschten Output-Variablen"""

    include_sqlite: bool = True
    """SQLite-Output generieren?"""

    include_html: bool = False
    """HTML-Summary generieren?"""

    @classmethod
    def standard_outputs(cls) -> 'OutputConfig':
        """Erstellt Standard-Output-Konfiguration."""
        return cls(variables=[
            # Basic temperature and energy
            OutputVariable("*", "Zone Mean Air Temperature", "Hourly"),
            OutputVariable("*", "Zone Air System Sensible Heating Energy", "Hourly"),
            OutputVariable("*", "Zone Air System Sensible Cooling Energy", "Hourly"),
            OutputVariable("*", "Zone Lights Electric Energy", "Hourly"),
            OutputVariable("*", "Zone Electric Equipment Electric Energy", "Hourly"),

            # Heating/Cooling loads (peak values) - Fixed for Ideal Loads
            OutputVariable("*", "Zone Ideal Loads Zone Total Heating Rate", "Hourly"),
            OutputVariable("*", "Zone Ideal Loads Zone Total Cooling Rate", "Hourly"),

            # Austrian Energieausweis metrics
            # Transmission heat losses (QT)
            OutputVariable("*", "Surface Average Face Conduction Heat Transfer Energy", "Hourly"),

            # Ventilation heat losses (QV)
            OutputVariable("*", "Zone Infiltration Sensible Heat Gain Energy", "Hourly"),
            OutputVariable("*", "Zone Ventilation Sensible Heat Gain Energy", "Hourly"),

            # Solar heat gains
            OutputVariable("*", "Zone Windows Total Heat Gain Energy", "Hourly"),

            # Internal heat gains
            OutputVariable("*", "Zone Lights Total Heating Energy", "Hourly"),
            OutputVariable("*", "Zone Electric Equipment Total Heating Energy", "Hourly"),
            OutputVariable("*", "Zone People Total Heating Energy", "Hourly"),
        ])

    @classmethod
    def minimal_outputs(cls) -> 'OutputConfig':
        """Erstellt minimale Output-Konfiguration (nur Temperatur)."""
        return cls(variables=[
            OutputVariable("*", "Zone Mean Air Temperature", "Hourly"),
        ])

    @classmethod
    def detailed_outputs(cls) -> 'OutputConfig':
        """Erstellt detaillierte Output-Konfiguration."""
        standard = cls.standard_outputs()
        standard.variables.extend([
            OutputVariable("*", "Zone Operative Temperature", "Hourly"),
            OutputVariable("*", "Zone Air Humidity Ratio", "Hourly"),
            OutputVariable("*", "Surface Outside Face Temperature", "Hourly"),
            OutputVariable("*", "Surface Inside Face Temperature", "Hourly"),
        ])
        return standard


# ============================================================================
# Location Model
# ============================================================================

@dataclass
class LocationData:
    """Geografische Standort-Daten."""
    name: str = "Salzburg"
    """Standort-Name"""

    latitude: float = 47.8
    """Breitengrad"""

    longitude: float = 13.05
    """Längengrad"""

    time_zone: float = 1.0
    """Zeitzone (GMT+X)"""

    elevation: float = 430.0
    """Höhe über Meer in Metern"""

    @classmethod
    def from_weather_file(cls, epw_path: Path) -> 'LocationData':
        """Extrahiert Location-Daten aus EPW-Datei.

        Note: Aktuell nur Placeholder. Echte Implementierung würde
        EPW-Header parsen.
        """
        # TODO: EPW-Header parsen
        return cls()  # Fallback zu Salzburg


# ============================================================================
# Generator Results
# ============================================================================

@dataclass
class GenerationResult:
    """Ergebnis einer IDF-Generierung.

    Diese Klasse kann erweitert werden, um Diagnose-Informationen
    über den Generierungs-Prozess zu speichern.
    """
    idf: Any  # eppy IDF object
    """Das generierte IDF-Objekt"""

    zones: List[ZoneInfo]
    """Liste aller erstellten Zonen"""

    num_surfaces: int = 0
    """Anzahl erstellter Surfaces"""

    num_windows: int = 0
    """Anzahl erstellter Fenster"""

    warnings: List[str] = field(default_factory=list)
    """Warnungen während der Generierung"""

    output_path: Optional[Path] = None
    """Pfad zur gespeicherten IDF-Datei (falls gespeichert)"""

    def summary(self) -> str:
        """Erstellt Zusammenfassung."""
        return (
            f"GenerationResult:\n"
            f"  Zones: {len(self.zones)}\n"
            f"  Surfaces: {self.num_surfaces}\n"
            f"  Windows: {self.num_windows}\n"
            f"  Warnings: {len(self.warnings)}\n"
            f"  Output: {self.output_path or 'Not saved'}"
        )


# ============================================================================
# Helper Functions
# ============================================================================

def create_zone_info_from_idf_object(idf_zone: Any, floor: int) -> ZoneInfo:
    """Erstellt ZoneInfo aus eppy ZONE-Objekt.

    Args:
        idf_zone: eppy ZONE-Objekt
        floor: Geschoss-Nummer (0-basiert)

    Returns:
        ZoneInfo-Instanz
    """
    return ZoneInfo(
        name=idf_zone.Name,
        floor=floor,
        floor_area=idf_zone.Floor_Area if hasattr(idf_zone, 'Floor_Area') else 0.0,
        volume=idf_zone.Volume if hasattr(idf_zone, 'Volume') else 0.0,
        z_origin=idf_zone.Z_Origin,
        idf_object=idf_zone
    )
