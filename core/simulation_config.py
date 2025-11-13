"""Simulation scenario configuration for reproducible simulations.

This module provides a comprehensive configuration system for defining
complete simulation scenarios in YAML format. Unlike Config (tool settings),
SimulationConfig describes a specific building to simulate.
"""

from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml


# ============================================================================
# Building Definition
# ============================================================================

class GeometryParams(BaseModel):
    """Geometry parameters for building generation."""

    length: float = Field(gt=0, description="Building length in meters")
    width: float = Field(gt=0, description="Building width in meters")
    height: float = Field(gt=0, description="Building height in meters")
    num_floors: int = Field(ge=1, description="Number of floors")
    floor_height: Optional[float] = Field(None, gt=0, description="Height per floor (overrides height)")
    window_wall_ratio: float = Field(0.3, ge=0, le=1, description="Window-to-wall ratio")
    orientation: float = Field(0.0, description="Building orientation in degrees (0=North)")


class FensterParams(BaseModel):
    """Window area parameters by orientation.

    Can specify either exact areas per orientation OR a window-to-wall ratio.
    """

    # Variant A: Exact areas per orientation (preferred)
    nord_m2: Optional[float] = Field(None, ge=0, description="North-facing window area [m²]")
    ost_m2: Optional[float] = Field(None, ge=0, description="East-facing window area [m²]")
    sued_m2: Optional[float] = Field(None, ge=0, description="South-facing window area [m²]")
    west_m2: Optional[float] = Field(None, ge=0, description="West-facing window area [m²]")

    # Variant B: Overall WWR (fallback)
    window_wall_ratio: Optional[float] = Field(
        0.3,
        ge=0.05,
        le=0.95,
        description="Overall window-to-wall ratio"
    )


class EnergieausweisParams(BaseModel):
    """Parameters from Austrian/German Energy Certificate (Energieausweis).

    This enables the 5-Zone model workflow using certified building data.
    Geometry will be reconstructed from envelope areas if provided.
    """

    # ============ REQUIRED: U-Values and Gross Floor Area ============
    bruttoflaeche_m2: float = Field(
        ...,
        gt=10,
        lt=50000,
        description="Gross floor area incl. walls [m²]"
    )

    u_wert_wand: float = Field(..., gt=0.1, lt=3.0, description="Wall U-value [W/m²K]")
    u_wert_dach: float = Field(..., gt=0.1, lt=2.0, description="Roof U-value [W/m²K]")
    u_wert_boden: float = Field(..., gt=0.1, lt=2.0, description="Floor slab U-value [W/m²K]")
    u_wert_fenster: float = Field(..., gt=0.5, lt=6.0, description="Window U-value [W/m²K]")

    # ============ OPTIONAL: Envelope Areas (for geometry reconstruction) ============
    wandflaeche_m2: Optional[float] = Field(None, gt=0, description="Total external wall area [m²]")
    dachflaeche_m2: Optional[float] = Field(None, gt=0, description="Roof area [m²]")
    bodenflaeche_m2: Optional[float] = Field(None, gt=0, description="Floor slab area [m²]")

    # ============ OPTIONAL: Geometry Hints ============
    anzahl_geschosse: int = Field(2, ge=1, le=20, description="Number of floors")
    geschosshoehe_m: float = Field(3.0, ge=2.3, le=4.5, description="Floor height [m]")
    aspect_ratio_hint: float = Field(
        1.5,
        ge=1.0,
        le=3.0,
        description="Hint for length/width ratio (for geometry reconstruction)"
    )

    # ============ WINDOWS ============
    fenster: FensterParams = Field(default_factory=FensterParams, description="Window areas by orientation")
    g_wert_fenster: float = Field(
        0.6,
        ge=0.1,
        le=0.9,
        description="Solar Heat Gain Coefficient (g-value / SHGC)"
    )

    # ============ VENTILATION ============
    luftwechselrate_h: float = Field(0.5, ge=0.0, le=3.0, description="Air change rate [1/h]")
    infiltration_ach50: Optional[float] = Field(
        None,
        ge=0.0,
        le=15.0,
        description="Infiltration at 50 Pa [1/h] from Blower Door test"
    )

    # ============ METADATA ============
    gebaeudetyp: Literal["EFH", "MFH", "NWG"] = Field("MFH", description="Building type: EFH (single-family), MFH (multi-family), NWG (commercial)")
    baujahr: Optional[int] = Field(None, ge=1800, le=2030, description="Year of construction")

    # ============ GEOMETRY SOLVER METADATA (auto-populated from UI) ============
    geometry_solver_method: Optional[str] = Field(
        None,
        description="Method used for geometry reconstruction (e.g., 'complete_areas', 'nettoflaeche_only')"
    )
    geometry_solver_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Confidence score of geometry reconstruction (0-1)"
    )


class EnvelopeParams(BaseModel):
    """Building envelope (walls, roof, floor) parameters."""

    wall_construction: str = Field("medium_insulated", description="Wall construction type")
    wall_u_value: Optional[float] = Field(None, gt=0, description="Wall U-value [W/m²K]")

    roof_construction: str = Field("insulated_roof", description="Roof construction type")
    roof_u_value: Optional[float] = Field(None, gt=0, description="Roof U-value [W/m²K]")

    floor_construction: str = Field("slab_on_grade", description="Floor construction type")
    floor_u_value: Optional[float] = Field(None, gt=0, description="Floor U-value [W/m²K]")

    window_type: str = Field("double_glazed", description="Window type")
    window_u_value: Optional[float] = Field(None, gt=0, description="Window U-value [W/m²K]")
    window_shgc: Optional[float] = Field(None, ge=0, le=1, description="Solar Heat Gain Coefficient")


class ZoneParams(BaseModel):
    """Zone-specific parameters."""

    zone_type: Literal["residential", "office", "retail", "other"] = "residential"

    # Internal loads
    people_density: float = Field(0.02, ge=0, description="People per m² floor area")
    lighting_power: float = Field(5.0, ge=0, description="Lighting power density [W/m²]")
    equipment_power: float = Field(3.0, ge=0, description="Equipment power density [W/m²]")

    # Schedules
    occupancy_schedule: str = Field("residential", description="Occupancy schedule type")
    lighting_schedule: str = Field("residential", description="Lighting schedule type")
    equipment_schedule: str = Field("residential", description="Equipment schedule type")

    # Infiltration
    infiltration_rate: float = Field(0.5, ge=0, description="Air changes per hour from infiltration")


class BuildingParams(BaseModel):
    """Complete building definition.

    Supports two workflows:
    1. SimpleBox: Provide 'geometry' + 'envelope' parameters
    2. Energieausweis: Provide 'energieausweis' parameters (geometry will be reconstructed)
    """

    name: str = Field(description="Building name/identifier")
    building_type: Literal["residential", "office", "retail", "mixed"] = "residential"

    # Source workflow (auto-determined from which params are provided)
    source: Literal["simplebox", "energieausweis"] = Field(
        "simplebox",
        description="Source workflow: 'simplebox' or 'energieausweis'"
    )

    # SimpleBox workflow params
    geometry: Optional[GeometryParams] = Field(None, description="Geometry parameters (SimpleBox workflow)")
    envelope: EnvelopeParams = Field(default_factory=EnvelopeParams, description="Envelope parameters (SimpleBox workflow)")

    # Energieausweis workflow params
    energieausweis: Optional[EnergieausweisParams] = Field(
        None,
        description="Energieausweis parameters (5-Zone workflow)"
    )

    # Calculated geometry (populated after Energieausweis reconstruction)
    calculated_geometry: Optional[GeometryParams] = Field(
        None,
        description="Geometry calculated from Energieausweis data (auto-populated)"
    )

    # Zone configurations
    zones: Dict[str, ZoneParams] = Field(default_factory=dict, description="Zone configurations")

    # If zones is empty, use default zone params for whole building
    default_zone: ZoneParams = Field(default_factory=ZoneParams)

    @field_validator('zones')
    @classmethod
    def ensure_zone_names(cls, v: Dict[str, ZoneParams]) -> Dict[str, ZoneParams]:
        """Validate zone names are not empty."""
        if v and any(not name.strip() for name in v.keys()):
            raise ValueError("Zone names cannot be empty")
        return v

    @model_validator(mode='after')
    def validate_workflow(self):
        """Validate that either geometry OR energieausweis is provided."""
        has_geometry = self.geometry is not None
        has_ea = self.energieausweis is not None

        if not has_geometry and not has_ea:
            raise ValueError(
                "Must provide either 'geometry' (SimpleBox workflow) "
                "OR 'energieausweis' (5-Zone workflow)"
            )

        if has_geometry and has_ea:
            raise ValueError(
                "Cannot provide both 'geometry' and 'energieausweis'. "
                "Choose one workflow: SimpleBox or Energieausweis"
            )

        # Auto-set source based on what's provided
        if has_ea:
            self.source = "energieausweis"
        else:
            self.source = "simplebox"

        return self


# ============================================================================
# HVAC System Configuration
# ============================================================================

class IdealLoadsParams(BaseModel):
    """Ideal Loads Air System parameters."""

    heating_setpoint: float = Field(20.0, description="Heating setpoint [°C]")
    cooling_setpoint: float = Field(26.0, description="Cooling setpoint [°C]")

    heating_limit: Optional[float] = Field(None, description="Max heating capacity [W]")
    cooling_limit: Optional[float] = Field(None, description="Max cooling capacity [W]")

    outdoor_air_flow_rate: float = Field(0.0, ge=0, description="Outdoor air flow rate [m³/s]")
    economizer: bool = Field(False, description="Enable economizer")


class HVACSystemConfig(BaseModel):
    """HVAC system configuration."""

    system_type: Literal["ideal_loads", "vav", "fan_coil", "none"] = "ideal_loads"

    # Type-specific params
    ideal_loads: Optional[IdealLoadsParams] = Field(default_factory=IdealLoadsParams)

    # Future: VAV, Fan Coil, etc.


# ============================================================================
# Simulation Parameters
# ============================================================================

class SimulationPeriod(BaseModel):
    """Simulation time period."""

    start_month: int = Field(1, ge=1, le=12)
    start_day: int = Field(1, ge=1, le=31)
    end_month: int = Field(12, ge=1, le=12)
    end_day: int = Field(31, ge=1, le=31)


class OutputParams(BaseModel):
    """Output configuration."""

    output_dir: str = Field("output", description="Output directory (relative or absolute)")
    save_idf: bool = Field(True, description="Save generated IDF file")
    save_sql: bool = Field(True, description="Save SQL output database")

    # Variables to report
    output_variables: List[str] = Field(
        default_factory=lambda: [
            "Zone Mean Air Temperature",
            "Zone Air System Sensible Heating Energy",
            "Zone Air System Sensible Cooling Energy",
        ],
        description="EnergyPlus output variables to report"
    )
    reporting_frequency: Literal["Timestep", "Hourly", "Daily", "Monthly", "Annual"] = "Hourly"


class SimulationParams(BaseModel):
    """Simulation execution parameters."""

    weather_file: str = Field(description="Path to EPW weather file (relative or absolute)")

    # Simulation timestep
    timestep: int = Field(
        default=4,
        ge=1,
        le=60,
        description="Number of timesteps per hour (1-60). Default: 4 (15 min intervals)"
    )

    period: SimulationPeriod = Field(default_factory=SimulationPeriod)
    output: OutputParams = Field(default_factory=OutputParams)

    # Execution
    timeout: int = Field(3600, ge=60, description="Simulation timeout in seconds")


# ============================================================================
# Main Configuration
# ============================================================================

class SimulationConfig(BaseModel):
    """Complete simulation scenario configuration.

    This config describes everything needed to run a complete simulation:
    - Building geometry and envelope
    - Internal loads and schedules
    - HVAC system
    - Weather data
    - Output requirements

    Example:
        >>> config = SimulationConfig.from_yaml("scenarios/efh_passivhaus.yaml")
        >>> # Run simulation with this config
    """

    # Metadata
    name: str = Field(description="Scenario name")
    description: str = Field("", description="Scenario description")
    version: str = Field("1.0", description="Config version")

    # Main sections
    building: BuildingParams
    hvac: HVACSystemConfig = Field(default_factory=HVACSystemConfig)
    simulation: SimulationParams

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "SimulationConfig":
        """Load simulation config from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            Parsed and validated SimulationConfig

        Raises:
            FileNotFoundError: If YAML file doesn't exist
            yaml.YAMLError: If YAML is invalid
            pydantic.ValidationError: If config doesn't match schema
        """
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_yaml(self, yaml_path: str | Path) -> None:
        """Save configuration to YAML file.

        Args:
            yaml_path: Destination path for YAML file
        """
        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                self.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    def validate_paths(self, base_dir: Optional[Path] = None) -> None:
        """Validate that referenced files exist.

        Args:
            base_dir: Base directory for resolving relative paths

        Raises:
            FileNotFoundError: If weather file doesn't exist
        """
        if base_dir is None:
            base_dir = Path.cwd()

        # Check weather file
        weather_path = Path(self.simulation.weather_file)
        if not weather_path.is_absolute():
            weather_path = base_dir / weather_path

        if not weather_path.exists():
            raise FileNotFoundError(f"Weather file not found: {weather_path}")
