"""Configuration management for EnergyPlus Automation Tool."""

import os
import platform
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class EnergyPlusConfig(BaseModel):
    """EnergyPlus installation configuration."""

    installation_path: str = ""
    version: str = "23.2"
    executable: str = ""

    def get_executable_path(self) -> Path:
        """Get the path to EnergyPlus executable, auto-detecting if necessary."""
        if self.executable:
            return Path(self.executable)

        if self.installation_path:
            base_path = Path(self.installation_path)
        else:
            # Auto-detect based on operating system
            base_path = self._auto_detect_installation()

        # Determine executable name based on OS
        system = platform.system()
        if system == "Windows":
            exe_name = "energyplus.exe"
        else:
            exe_name = "energyplus"

        return base_path / exe_name

    def _auto_detect_installation(self) -> Path:
        """Auto-detect EnergyPlus installation directory."""
        system = platform.system()

        if system == "Windows":
            base = Path("C:/EnergyPlusV23-2-0")
            if base.exists():
                return base
            # Try other common locations
            program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            for ep_dir in program_files.glob("EnergyPlus*"):
                return ep_dir

        elif system == "Linux":
            base = Path("/usr/local/EnergyPlus-23-2-0")
            if base.exists():
                return base

        elif system == "Darwin":  # macOS
            base = Path("/Applications/EnergyPlus-23-2-0")
            if base.exists():
                return base

        raise FileNotFoundError(
            f"Could not auto-detect EnergyPlus installation on {system}. "
            "Please set 'energyplus.installation_path' in config."
        )


class SimulationConfig(BaseModel):
    """Simulation execution configuration."""

    output_dir: str = "output"
    num_processes: int = Field(default=4, ge=1, le=32)
    keep_intermediate_files: bool = False
    timeout: int = Field(default=3600, ge=60)


class WeatherConfig(BaseModel):
    """Weather data configuration."""

    data_dir: str = "data/weather"
    default_file: str = ""


class StandardsConfig(BaseModel):
    """Building standards configuration."""

    data_dir: str = "data/standards"
    default_standard: str = "ISO_13790"
    available: list[str] = ["ISO_13790", "TABULA_DE", "ASHRAE_90_1", "EN_15459"]


class GeometryConfig(BaseModel):
    """Geometry generation configuration."""

    defaults: Dict[str, float] = {
        "floor_height": 3.0,
        "window_wall_ratio": 0.3,
        "orientation": 0,
        "num_floors": 2,
    }
    min_zone_volume: float = Field(default=10.0, ge=1.0)


class MaterialsConfig(BaseModel):
    """Materials and constructions configuration."""

    data_dir: str = "data/materials"
    database: str = "materials_database.json"


class HVACConfig(BaseModel):
    """HVAC system configuration."""

    default_type: str = "IdealLoadsAirSystem"
    templates_dir: str = "src/templates/hvac"


class PostProcessingConfig(BaseModel):
    """Post-processing configuration."""

    output_variables: list[str] = [
        "Zone Mean Air Temperature",
        "Zone Air System Sensible Heating Energy",
        "Zone Air System Sensible Cooling Energy",
    ]
    reporting_frequency: str = "Hourly"
    auto_plot: bool = False


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    log_file: str = "energyplus_automation.log"
    console_output: bool = True


class Config(BaseModel):
    """Main configuration class."""

    energyplus: EnergyPlusConfig = EnergyPlusConfig()
    simulation: SimulationConfig = SimulationConfig()
    weather: WeatherConfig = WeatherConfig()
    standards: StandardsConfig = StandardsConfig()
    geometry: GeometryConfig = GeometryConfig()
    materials: MaterialsConfig = MaterialsConfig()
    hvac: HVACConfig = HVACConfig()
    postprocessing: PostProcessingConfig = PostProcessingConfig()
    logging: LoggingConfig = LoggingConfig()

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "Config":
        """Load configuration from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def load_default(cls) -> "Config":
        """Load default configuration."""
        config_path = Path(__file__).parent.parent.parent / "config" / "default_config.yaml"
        if config_path.exists():
            return cls.from_yaml(config_path)
        return cls()

    def to_yaml(self, yaml_path: str | Path) -> None:
        """Save configuration to YAML file."""
        with open(yaml_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load_default()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def load_config(config_path: str | Path) -> Config:
    """Load and set configuration from file."""
    config = Config.from_yaml(config_path)
    set_config(config)
    return config
