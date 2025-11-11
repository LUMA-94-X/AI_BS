"""
Example: Simple Box Building Simulation

This example demonstrates how to:
1. Create a simple box-shaped building model
2. Run an EnergyPlus simulation
3. Access basic results

Prerequisites:
- EnergyPlus installed
- Weather file (EPW format)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.simulation.runner import EnergyPlusRunner
from src.utils.config import get_config
import logging


def main():
    """Run a simple box building simulation."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("Simple Box Building Simulation Example")
    logger.info("=" * 70)

    # Define building geometry
    geometry = BuildingGeometry(
        length=10.0,      # 10 meters
        width=8.0,        # 8 meters
        height=6.0,       # 6 meters (2 floors × 3m each)
        num_floors=2,
        window_wall_ratio=0.3,
        orientation=0.0   # North-facing
    )

    logger.info("\nBuilding Geometry:")
    logger.info(f"  Dimensions: {geometry.length}m × {geometry.width}m × {geometry.height}m")
    logger.info(f"  Number of floors: {geometry.num_floors}")
    logger.info(f"  Floor area: {geometry.floor_area:.1f} m²")
    logger.info(f"  Total floor area: {geometry.total_floor_area:.1f} m²")
    logger.info(f"  Volume: {geometry.volume:.1f} m³")
    logger.info(f"  Window-to-wall ratio: {geometry.window_wall_ratio:.0%}")

    # Create model
    logger.info("\nCreating building model...")
    generator = SimpleBoxGenerator()

    # Create output directory
    output_dir = Path("output/example_simple_box")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate IDF file
    idf_path = output_dir / "simple_box.idf"
    try:
        idf = generator.create_model(geometry, idf_path=idf_path)
        logger.info(f"IDF file created: {idf_path}")
    except Exception as e:
        logger.error(f"Failed to create IDF: {e}")
        return 1

    # Check for weather file
    weather_file = Path("data/weather/example.epw")
    if not weather_file.exists():
        logger.warning("\n" + "!" * 70)
        logger.warning("Weather file not found!")
        logger.warning(f"Expected location: {weather_file}")
        logger.warning("\nTo run the simulation, you need to:")
        logger.warning("1. Download a weather file (EPW format) for your location")
        logger.warning("   from: https://energyplus.net/weather")
        logger.warning("2. Place it in: data/weather/")
        logger.warning("3. Update the weather_file path in this script")
        logger.warning("!" * 70)
        logger.info("\nIDF file has been created successfully. Skipping simulation.")
        return 0

    # Run simulation
    logger.info("\nRunning EnergyPlus simulation...")
    logger.info("This may take a few minutes...")

    try:
        runner = EnergyPlusRunner()
        result = runner.run_simulation(
            idf_path=idf_path,
            weather_file=weather_file,
            output_dir=output_dir / "simulation_results",
            output_prefix="simple_box"
        )

        # Display results
        logger.info("\n" + "=" * 70)
        logger.info("Simulation Results")
        logger.info("=" * 70)

        if result.success:
            logger.info(f"✓ Simulation completed successfully!")
            logger.info(f"  Execution time: {result.execution_time:.2f} seconds")
            logger.info(f"  Output directory: {result.output_dir}")

            if result.sql_file and result.sql_file.exists():
                logger.info(f"  SQL database: {result.sql_file}")
                logger.info(f"  Size: {result.sql_file.stat().st_size / 1024:.1f} KB")

            if result.csv_files:
                logger.info(f"  CSV files: {len(result.csv_files)} files")

            logger.info("\nNext steps:")
            logger.info("  - View results in the output directory")
            logger.info("  - Open .htm file in a browser for summary reports")
            logger.info("  - Query .sql file for detailed hourly data")

        else:
            logger.error(f"✗ Simulation failed!")
            logger.error(f"  Error: {result.error_message}")
            logger.info(f"  Check error file: {result.output_dir}/simple_boxout.err")
            return 1

    except FileNotFoundError as e:
        logger.error(f"\n✗ EnergyPlus not found: {e}")
        logger.info("\nPlease ensure EnergyPlus is installed and configured.")
        logger.info("Set the installation path in: config/default_config.yaml")
        return 1

    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    logger.info("\n" + "=" * 70)
    logger.info("Example completed successfully!")
    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
