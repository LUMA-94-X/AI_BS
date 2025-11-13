"""Simulation scenario configuration for reproducible simulations.

This module provides a comprehensive configuration system for defining
complete simulation scenarios in YAML format. Unlike Config (tool settings),
SimulationConfig describes a specific building to simulate.
"""

from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
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
    """Complete building definition."""

    name: str = Field(description="Building name/identifier")
    building_type: Literal["residential", "office", "retail", "mixed"] = "residential"

    geometry: GeometryParams
    envelope: EnvelopeParams = Field(default_factory=EnvelopeParams)
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
