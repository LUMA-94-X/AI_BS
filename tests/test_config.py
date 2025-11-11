"""
Unit tests for configuration module.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import (
    Config,
    EnergyPlusConfig,
    SimulationConfig,
    get_config,
    set_config
)


class TestEnergyPlusConfig:
    """Tests for EnergyPlusConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EnergyPlusConfig()
        assert config.version == "23.2"
        assert config.installation_path == ""
        assert config.executable == ""

    def test_explicit_path(self):
        """Test with explicit installation path."""
        config = EnergyPlusConfig(
            installation_path="/custom/path/EnergyPlus"
        )
        assert config.installation_path == "/custom/path/EnergyPlus"


class TestSimulationConfig:
    """Tests for SimulationConfig."""

    def test_default_values(self):
        """Test default simulation configuration."""
        config = SimulationConfig()
        assert config.output_dir == "output"
        assert config.num_processes == 4
        assert config.keep_intermediate_files is False
        assert config.timeout == 3600

    def test_custom_values(self):
        """Test custom simulation configuration."""
        config = SimulationConfig(
            output_dir="custom_output",
            num_processes=8,
            keep_intermediate_files=True,
            timeout=7200
        )
        assert config.output_dir == "custom_output"
        assert config.num_processes == 8
        assert config.keep_intermediate_files is True
        assert config.timeout == 7200

    def test_validation_num_processes(self):
        """Test validation of num_processes."""
        with pytest.raises(ValueError):
            SimulationConfig(num_processes=0)

        with pytest.raises(ValueError):
            SimulationConfig(num_processes=100)

    def test_validation_timeout(self):
        """Test validation of timeout."""
        with pytest.raises(ValueError):
            SimulationConfig(timeout=30)  # Too short


class TestConfig:
    """Tests for main Config class."""

    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        assert config.energyplus is not None
        assert config.simulation is not None
        assert config.weather is not None

    def test_load_default(self):
        """Test loading default config from YAML."""
        config = Config.load_default()
        assert config is not None

    def test_get_config(self):
        """Test global config getter."""
        config = get_config()
        assert config is not None
        assert isinstance(config, Config)

    def test_set_config(self):
        """Test global config setter."""
        new_config = Config()
        set_config(new_config)
        retrieved = get_config()
        assert retrieved is new_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
