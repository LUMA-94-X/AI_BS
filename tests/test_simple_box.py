"""Unit tests for simple_box.py"""

import pytest
import tempfile
from pathlib import Path

from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.utils.config import get_config


class TestBuildingGeometry:
    """Tests for BuildingGeometry dataclass."""

    def test_valid_geometry(self):
        """Test creation of valid geometry."""
        geom = BuildingGeometry(
            length=10.0,
            width=8.0,
            height=3.0,
            num_floors=1,
            window_wall_ratio=0.3,
            orientation=0.0,
        )
        assert geom.length == 10.0
        assert geom.width == 8.0
        assert geom.height == 3.0
        assert geom.num_floors == 1
        assert geom.window_wall_ratio == 0.3
        assert geom.orientation == 0.0

    def test_floor_height_calculation(self):
        """Test floor height calculation."""
        geom = BuildingGeometry(10.0, 8.0, 6.0, num_floors=2)
        assert geom.floor_height == 3.0

    def test_floor_area_calculation(self):
        """Test floor area calculation."""
        geom = BuildingGeometry(10.0, 8.0, 3.0)
        assert geom.floor_area == 80.0

    def test_total_floor_area_calculation(self):
        """Test total floor area calculation."""
        geom = BuildingGeometry(10.0, 8.0, 6.0, num_floors=2)
        assert geom.total_floor_area == 160.0

    def test_volume_calculation(self):
        """Test volume calculation."""
        geom = BuildingGeometry(10.0, 8.0, 3.0)
        assert geom.volume == 240.0

    def test_invalid_dimensions(self):
        """Test validation of invalid dimensions."""
        with pytest.raises(ValueError, match="Dimensions must be positive"):
            BuildingGeometry(-10.0, 8.0, 3.0)

        with pytest.raises(ValueError, match="Dimensions must be positive"):
            BuildingGeometry(10.0, 0.0, 3.0)

    def test_invalid_num_floors(self):
        """Test validation of invalid number of floors."""
        with pytest.raises(ValueError, match="Number of floors must be at least 1"):
            BuildingGeometry(10.0, 8.0, 3.0, num_floors=0)

    def test_invalid_wwr(self):
        """Test validation of invalid window-to-wall ratio."""
        with pytest.raises(ValueError, match="Window-to-wall ratio must be between 0 and 1"):
            BuildingGeometry(10.0, 8.0, 3.0, window_wall_ratio=1.5)

        with pytest.raises(ValueError, match="Window-to-wall ratio must be between 0 and 1"):
            BuildingGeometry(10.0, 8.0, 3.0, window_wall_ratio=-0.1)

    def test_invalid_orientation(self):
        """Test validation of invalid orientation."""
        with pytest.raises(ValueError, match="Orientation must be between 0 and 360 degrees"):
            BuildingGeometry(10.0, 8.0, 3.0, orientation=400.0)

        with pytest.raises(ValueError, match="Orientation must be between 0 and 360 degrees"):
            BuildingGeometry(10.0, 8.0, 3.0, orientation=-10.0)


class TestSimpleBoxGenerator:
    """Tests for SimpleBoxGenerator."""

    def test_generator_initialization(self):
        """Test generator initialization."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        assert generator.config == config

    def test_create_model_basic(self):
        """Test basic model creation."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.0)

        idf = generator.create_model(geometry)

        # Check basic objects exist
        assert len(idf.idfobjects['BUILDING']) == 1
        assert len(idf.idfobjects['ZONE']) == 1
        assert len(idf.idfobjects['BUILDINGSURFACE:DETAILED']) == 6  # 4 walls + floor + ceiling

    def test_create_model_with_windows(self):
        """Test model creation with windows."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.3)

        idf = generator.create_model(geometry)

        # Check windows were created
        windows = idf.idfobjects.get('FENESTRATIONSURFACE:DETAILED', [])
        assert len(windows) == 4  # One window per wall

    def test_create_model_multi_floor(self):
        """Test model creation with multiple floors."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 6.0, num_floors=2, window_wall_ratio=0.2)

        idf = generator.create_model(geometry)

        # Check zones
        zones = idf.idfobjects['ZONE']
        assert len(zones) == 2

        # Check surfaces (2 floors * 6 surfaces each)
        surfaces = idf.idfobjects['BUILDINGSURFACE:DETAILED']
        assert len(surfaces) == 12

        # Check windows (2 floors * 4 windows each)
        windows = idf.idfobjects.get('FENESTRATIONSURFACE:DETAILED', [])
        assert len(windows) == 8

    def test_create_model_no_windows(self):
        """Test model creation without windows (WWR = 0)."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.0)

        idf = generator.create_model(geometry)

        # Check no windows were created
        windows = idf.idfobjects.get('FENESTRATIONSURFACE:DETAILED', [])
        assert len(windows) == 0

    def test_save_idf_file(self):
        """Test saving IDF to file."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.3)

        with tempfile.TemporaryDirectory() as tmpdir:
            idf_path = Path(tmpdir) / "test.idf"
            idf = generator.create_model(geometry, idf_path=idf_path)

            # Check file was created
            assert idf_path.exists()
            assert idf_path.stat().st_size > 0

            # Check file content
            content = idf_path.read_text(encoding='utf-8')
            assert "VERSION" in content
            assert "BUILDING" in content
            assert "ZONE" in content

    def test_materials_and_constructions(self):
        """Test that materials and constructions are added."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.3)

        idf = generator.create_model(geometry)

        # Check materials exist
        materials = idf.idfobjects.get('MATERIAL', [])
        assert len(materials) > 0

        # Check constructions exist
        constructions = idf.idfobjects.get('CONSTRUCTION', [])
        assert len(constructions) > 0

    def test_schedules_added(self):
        """Test that schedules are added."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.0)

        idf = generator.create_model(geometry)

        # Check schedules exist
        schedules_constant = idf.idfobjects.get('SCHEDULE:CONSTANT', [])
        schedules_compact = idf.idfobjects.get('SCHEDULE:COMPACT', [])
        assert len(schedules_constant) + len(schedules_compact) > 0

    def test_internal_loads_added(self):
        """Test that internal loads are added."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.0)

        idf = generator.create_model(geometry)

        # Check internal loads exist
        people = idf.idfobjects.get('PEOPLE', [])
        lights = idf.idfobjects.get('LIGHTS', [])
        equipment = idf.idfobjects.get('ELECTRICEQUIPMENT', [])

        assert len(people) == 1
        assert len(lights) == 1
        assert len(equipment) == 1

    def test_output_variables_added(self):
        """Test that output variables are added."""
        config = get_config()
        generator = SimpleBoxGenerator(config)
        geometry = BuildingGeometry(10.0, 8.0, 3.0, num_floors=1, window_wall_ratio=0.0)

        idf = generator.create_model(geometry)

        # Check output variables exist
        output_vars = idf.idfobjects.get('OUTPUT:VARIABLE', [])
        assert len(output_vars) > 0

        # Check output tables
        output_tables = idf.idfobjects.get('OUTPUT:TABLE:SUMMARYREPORTS', [])
        assert len(output_tables) > 0

        # Check SQL output
        output_sql = idf.idfobjects.get('OUTPUT:SQLITE', [])
        assert len(output_sql) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
