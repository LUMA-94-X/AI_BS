"""Gemeinsames Datenmodell für Gebäude (SimpleBox + Energieausweis)."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field


class BuildingModel(BaseModel):
    """
    Einheitliches Datenmodell für Gebäudemodelle aus verschiedenen Quellen.

    Ermöglicht konsistente Speicherung und Verarbeitung von:
    - SimpleBox-Modellen (parametrisch)
    - 5-Zone-Modellen aus Energieausweis (IDF-basiert)
    """

    source: Literal["simplebox", "energieausweis"] = Field(
        ...,
        description="Quelle des Modells"
    )

    geometry_summary: Dict[str, float] = Field(
        ...,
        description="Zusammenfassung der Geometrie (L/W/H, Flächen, Volumen)"
    )

    idf_path: Optional[Path] = Field(
        None,
        description="Pfad zur gespeicherten IDF-Datei (falls vorhanden)"
    )

    num_zones: int = Field(
        ...,
        ge=1,
        description="Anzahl der Zonen im Modell"
    )

    has_hvac: bool = Field(
        default=False,
        description="Gibt an, ob HVAC-System konfiguriert ist"
    )

    gebaeudetyp: Optional[str] = Field(
        None,
        description="Gebäudetyp (EFH, MFH, NWG) falls bekannt"
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Zeitpunkt der Erstellung"
    )

    # Zusätzliche Metadaten für Energieausweis
    energieausweis_data: Optional[Dict] = Field(
        None,
        description="Optional: Original Energieausweis-Daten für Referenz"
    )

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @classmethod
    def from_simplebox(
        cls,
        length: float,
        width: float,
        height: float,
        num_floors: int,
        floor_height: float,
        window_wall_ratio: float,
        idf_path: Optional[Path] = None
    ) -> "BuildingModel":
        """
        Erstellt BuildingModel aus SimpleBox-Parametern.

        Args:
            length: Gebäudelänge in m
            width: Gebäudebreite in m
            height: Gesamthöhe in m
            num_floors: Anzahl Geschosse
            floor_height: Geschosshöhe in m
            window_wall_ratio: Fensterflächenanteil
            idf_path: Optional - Pfad zur IDF-Datei

        Returns:
            BuildingModel-Instanz
        """
        floor_area = length * width
        total_floor_area = floor_area * num_floors
        volume = floor_area * height

        # Perimeter für A/V-Verhältnis
        perimeter = 2 * (length + width)
        wall_area = perimeter * height
        envelope_area = wall_area + 2 * floor_area  # Wände + Dach + Boden
        av_ratio = envelope_area / volume

        geometry_summary = {
            "length": length,
            "width": width,
            "height": height,
            "num_floors": num_floors,
            "floor_height": floor_height,
            "floor_area": floor_area,
            "total_floor_area": total_floor_area,
            "volume": volume,
            "av_ratio": av_ratio,
            "window_wall_ratio": window_wall_ratio
        }

        return cls(
            source="simplebox",
            geometry_summary=geometry_summary,
            idf_path=idf_path,
            num_zones=num_floors,  # SimpleBox: 1 Zone pro Geschoss
            has_hvac=False,
            gebaeudetyp="SimpleBox"
        )

    @classmethod
    def from_energieausweis(
        cls,
        geo_solution,  # GeometrySolution
        ea_data,  # EnergieausweisInput
        idf_path: Path,
        num_zones: int
    ) -> "BuildingModel":
        """
        Erstellt BuildingModel aus Energieausweis-Daten.

        Args:
            geo_solution: GeometrySolution mit berechneter Geometrie
            ea_data: EnergieausweisInput mit Original-Daten
            idf_path: Pfad zur erstellten IDF-Datei
            num_zones: Anzahl Zonen (5 × Geschosse)

        Returns:
            BuildingModel-Instanz
        """
        geometry_summary = {
            "length": geo_solution.length,
            "width": geo_solution.width,
            "height": geo_solution.height,
            "num_floors": geo_solution.num_floors,
            "floor_height": geo_solution.floor_height,
            "floor_area": geo_solution.floor_area,
            "total_floor_area": ea_data.bruttoflaeche_m2,
            "volume": geo_solution.volume,
            "av_ratio": geo_solution.av_ratio,
            "aspect_ratio": geo_solution.aspect_ratio
        }

        # Speichere VOLLSTÄNDIGE Energieausweis-Daten für YAML Export/Import
        # Wichtig: Alle Felder speichern, nicht nur Subset!
        ea_full_data = ea_data.model_dump()  # Pydantic serialization

        # Ergänze GeometrySolver-Metadaten
        ea_full_data["_geometry_solver_meta"] = {
            "method": geo_solution.method.value,
            "confidence": geo_solution.confidence,
            "calculated_length": geo_solution.length,
            "calculated_width": geo_solution.width,
            "calculated_height": geo_solution.height
        }

        return cls(
            source="energieausweis",
            geometry_summary=geometry_summary,
            idf_path=idf_path,
            num_zones=num_zones,
            has_hvac=False,  # Initial ohne HVAC
            gebaeudetyp=ea_data.gebaeudetyp.value,
            energieausweis_data=ea_full_data  # Now contains ALL fields!
        )

    def get_display_name(self) -> str:
        """Gibt lesbaren Namen für das Modell zurück."""
        if self.source == "simplebox":
            return f"SimpleBox ({self.geometry_summary['length']:.1f}m × {self.geometry_summary['width']:.1f}m)"
        else:
            return f"5-Zone-Modell {self.gebaeudetyp} ({self.geometry_summary['total_floor_area']:.0f} m²)"

    def get_summary_text(self) -> str:
        """Gibt mehrzeilige Zusammenfassung zurück."""
        lines = [
            f"**Quelle:** {self.source}",
            f"**Gebäudetyp:** {self.gebaeudetyp or 'N/A'}",
            f"**Zonen:** {self.num_zones}",
            f"**Grundfläche:** {self.geometry_summary.get('floor_area', 0):.1f} m²",
            f"**Gesamtfläche:** {self.geometry_summary.get('total_floor_area', 0):.1f} m²",
            f"**Volumen:** {self.geometry_summary.get('volume', 0):.0f} m³",
            f"**HVAC:** {'✅ Konfiguriert' if self.has_hvac else '❌ Noch nicht konfiguriert'}"
        ]
        return "\n".join(lines)


# ============================================================================
# SESSION STATE HELPERS
# ============================================================================

def get_building_model_from_session(session_state) -> Optional[BuildingModel]:
    """
    Lädt BuildingModel aus Streamlit Session State.

    Args:
        session_state: Streamlit session_state object

    Returns:
        BuildingModel wenn vorhanden, sonst None
    """
    if 'building_model' in session_state:
        model_dict = session_state['building_model']
        # Konvertiere zurück zu BuildingModel
        if isinstance(model_dict, dict):
            return BuildingModel(**model_dict)
        elif isinstance(model_dict, BuildingModel):
            return model_dict
    return None


def save_building_model_to_session(session_state, model: BuildingModel) -> None:
    """
    Speichert BuildingModel in Streamlit Session State.

    Args:
        session_state: Streamlit session_state object
        model: BuildingModel zum Speichern
    """
    # Speichere als Dict (Pydantic-Serialisierung)
    session_state['building_model'] = model.model_dump()

    # Zusätzlich: Alte Keys für Rückwärtskompatibilität
    if model.idf_path:
        session_state['idf_path'] = model.idf_path

    session_state['geometry_source'] = model.source


def clear_building_model_from_session(session_state) -> None:
    """
    Löscht BuildingModel und verwandte Keys aus Session State.

    Args:
        session_state: Streamlit session_state object
    """
    keys_to_remove = [
        'building_model',
        'geometry',
        'idf',
        'idf_path',
        'geometry_source',
        'ea_input',
        'geo_solution',
        'hvac_config',
        'hvac_type'
    ]

    for key in keys_to_remove:
        if key in session_state:
            del session_state[key]
