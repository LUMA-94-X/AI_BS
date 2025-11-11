"""
Unit tests for geometry generation module.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geometry.simple_box import BuildingGeometry, SimpleBoxGenerator


class TestBuildingGeometry:
    """Tests for BuildingGeometry dataclass."""

    def test_valid_geometry(self):
        """Test creation of valid geometry."""
        geometry = BuildingGeometry(
            length=10.0,
            width=8.0,
            height=6.0,
            num_floors=2,
            window_wall_ratio=0.3,
            orientation=0.0
        )

        assert geometry.length == 10.0
        assert geometry.width == 8.0
        assert geometry.height == 6.0
        assert geometry.num_floors == 2

    def test_floor_height_calculation(self):
        """Test floor height calculation."""
        geometry = BuildingGeometry(
            length=10.0,
            width=8.0,
            height=9.0,
            num_floors=3
        )

        assert geometry.floor_height == 3.0

    def test_floor_area_calculation(self):
        """Test floor area calculation."""
        geometry = BuildingGeometry(
            length=10.0,
            width=8.0,
            height=6.0
        )

        assert geometry.floor_area == 80.0
        assert geometry.total_floor_area == 80.0  # 1 floor by default

    def test_volume_calculation(self):
        """Test volume calculation."""
        geometry = BuildingGeometry(
            length=10.0,
            width=8.0,
            height=6.0
        )

        assert geometry.volume == 480.0

    def test_invalid_dimensions(self):
        """Test that invalid dimensions raise ValueError."""
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            BuildingGeometry(
                length=-10.0,
                width=8.0,
                height=6.0
            )

    def test_invalid_num_floors(self):
        """Test that invalid number of floors raises ValueError."""
        with pytest.raises(ValueError, match="Number of floors must be at least 1"):
            BuildingGeometry(
                length=10.0,
                width=8.0,
                height=6.0,
                num_floors=0
            )

    def test_invalid_window_wall_ratio(self):
        """Test that invalid WWR raises ValueError."""
        with pytest.raises(ValueError, match="Window-to-wall ratio must be between 0 and 1"):
            BuildingGeometry(
                length=10.0,
                width=8.0,
                height=6.0,
                window_wall_ratio=1.5
            )

    def test_invalid_orientation(self):
        """Test that invalid orientation raises ValueError."""
        with pytest.raises(ValueError, match="Orientation must be between 0 and 360"):
            BuildingGeometry(
                length=10.0,
                width=8.0,
                height=6.0,
                orientation=400.0
            )


class TestSimpleBoxGenerator:
    """Tests for SimpleBoxGenerator."""

    def test_generator_initialization(self):
        """Test that generator can be initialized."""
        generator = SimpleBoxGenerator()
        assert generator is not None

    def test_idf_creation(self, tmp_path):
        """Test IDF file creation."""
        geometry = BuildingGeometry(
            length=10.0,
            width=8.0,
            height=6.0,
            num_floors=2,
            window_wall_ratio=0.3
        )

        generator = SimpleBoxGenerator()
        idf_path = tmp_path / "test_building.idf"

        # This test requires EnergyPlus to be installed
        # Skip if not available
        try:
            idf = generator.create_model(geometry, idf_path=idf_path)
            assert idf is not None
            assert idf_path.exists()
        except FileNotFoundError:
            pytest.skip("EnergyPlus not installed")

    def test_multiple_floors(self, tmp_path):
        """Test creation of multi-floor building."""
        geometry = BuildingGeometry(
            length=12.0,
            width=10.0,
            height=12.0,
            num_floors=4
        )

        generator = SimpleBoxGenerator()
        idf_path = tmp_path / "multi_floor.idf"

        try:
            idf = generator.create_model(geometry, idf_path=idf_path)
            # Check that 4 zones were created
            zones = idf.idfobjects["ZONE"]
            assert len(zones) == 4
        except FileNotFoundError:
            pytest.skip("EnergyPlus not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
