#!/usr/bin/env python3
"""Run EnergyPlus simulation from YAML configuration file.

This script provides a command-line interface for running reproducible
simulations using YAML configuration files.

Usage:
    python scripts/run_from_config.py scenarios/efh_standard.yaml
    python scripts/run_from_config.py scenarios/efh_passivhaus.yaml --verbose
    python scripts/run_from_config.py path/to/config.yaml --output custom_output/

Examples:
    # Run standard EFH simulation
    python scripts/run_from_config.py scenarios/efh_standard.yaml

    # Run with custom output directory
    python scripts/run_from_config.py scenarios/office_small.yaml --output results/office_test

    # Validate config without running
    python scripts/run_from_config.py scenarios/efh_passivhaus.yaml --validate-only
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.simulation_config import SimulationConfig
from features.geometrie.box_generator import SimpleBoxGenerator, BuildingGeometry
from features.hvac.ideal_loads import create_building_with_hvac
from features.simulation.runner import EnergyPlusRunner
from features.auswertung.kpi_rechner import KennzahlenRechner


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def validate_config(config: SimulationConfig) -> None:
    """Validate configuration and check file paths.

    Args:
        config: Simulation configuration to validate

    Raises:
        FileNotFoundError: If required files don't exist
        ValueError: If configuration is invalid
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating configuration...")

    # Validate weather file
    weather_path = Path(config.simulation.weather_file)
    if not weather_path.is_absolute():
        weather_path = PROJECT_ROOT / weather_path

    if not weather_path.exists():
        raise FileNotFoundError(f"Weather file not found: {weather_path}")

    logger.info(f"  ✓ Weather file: {weather_path.name}")

    # Validate building parameters
    geom = config.building.geometry
    logger.info(f"  ✓ Geometry: {geom.length}m × {geom.width}m × {geom.height}m")
    logger.info(f"  ✓ Floors: {geom.num_floors}")
    logger.info(f"  ✓ WWR: {geom.window_wall_ratio:.1%}")

    # Calculate floor area
    floor_area = geom.length * geom.width * geom.num_floors
    logger.info(f"  ✓ Total floor area: {floor_area:.1f} m²")

    logger.info("Configuration is valid!")


def create_building_from_config(config: SimulationConfig, output_path: Path) -> Path:
    """Create IDF building model from configuration.

    Args:
        config: Simulation configuration
        output_path: Path to save IDF file

    Returns:
        Path to generated IDF file
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating building model...")

    # Create geometry from config
    geom_params = config.building.geometry
    geometry = BuildingGeometry(
        length=geom_params.length,
        width=geom_params.width,
        height=geom_params.height,
        num_floors=geom_params.num_floors,
        window_wall_ratio=geom_params.window_wall_ratio,
        orientation=geom_params.orientation,
    )

    logger.info(f"  Building: {geometry.length}m × {geometry.width}m × {geometry.height}m")
    logger.info(f"  Floor area: {geometry.total_floor_area:.1f} m²")

    # Build sim_settings from YAML config
    sim_settings = {
        'timestep': config.simulation.timestep,
        'start_month': config.simulation.period.start_month,
        'start_day': config.simulation.period.start_day,
        'end_month': config.simulation.period.end_month,
        'end_day': config.simulation.period.end_day,
        'output_variables': config.simulation.output.output_variables,
        'reporting_frequency': config.simulation.output.reporting_frequency,
    }

    logger.info(f"  Simulation settings:")
    logger.info(f"    Timestep: {sim_settings['timestep']}/hour ({60/sim_settings['timestep']:.1f} min)")
    logger.info(f"    Period: {sim_settings['start_month']}/{sim_settings['start_day']} - {sim_settings['end_month']}/{sim_settings['end_day']}")
    logger.info(f"    Output frequency: {sim_settings['reporting_frequency']}")

    # Generate IDF (don't save yet - we'll add HVAC first!)
    generator = SimpleBoxGenerator()
    idf = generator.create_model(geometry, idf_path=None, sim_settings=sim_settings)

    logger.info(f"  ✓ IDF created (in memory)")

    # Add HVAC system
    if config.hvac.system_type == "ideal_loads":
        logger.info("Adding HVAC system (Ideal Loads)...")
        hvac_params = config.hvac.ideal_loads

        # Pass user-defined setpoints from YAML config
        idf = create_building_with_hvac(
            idf,
            "ideal_loads",
            heating_setpoint=hvac_params.heating_setpoint,
            cooling_setpoint=hvac_params.cooling_setpoint
        )

        logger.info(f"  Heating setpoint: {hvac_params.heating_setpoint}°C")
        logger.info(f"  Cooling setpoint: {hvac_params.cooling_setpoint}°C")
        logger.info("  ✓ HVAC system added with custom setpoints")

    # NOW save the complete IDF (geometry + HVAC)
    idf.save(str(output_path))
    logger.info(f"  ✓ IDF saved: {output_path}")

    return output_path


def run_simulation_from_config(
    config: SimulationConfig,
    output_dir_override: Path | None = None
) -> tuple[Path, float]:
    """Run EnergyPlus simulation from configuration.

    Args:
        config: Simulation configuration
        output_dir_override: Override output directory from config

    Returns:
        Tuple of (output_dir, execution_time)

    Raises:
        RuntimeError: If simulation fails
    """
    logger = logging.getLogger(__name__)

    # Determine output directory
    if output_dir_override:
        output_dir = output_dir_override
    else:
        output_dir = PROJECT_ROOT / config.simulation.output.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Output directory: {output_dir}")

    # Create IDF
    idf_path = output_dir / "building.idf"
    create_building_from_config(config, idf_path)

    # Resolve weather file path
    weather_path = Path(config.simulation.weather_file)
    if not weather_path.is_absolute():
        weather_path = PROJECT_ROOT / weather_path

    logger.info(f"Weather file: {weather_path}")

    # Run simulation
    logger.info("Running EnergyPlus simulation...")
    runner = EnergyPlusRunner()

    result = runner.run_simulation(
        idf_path=str(idf_path),
        weather_file=str(weather_path),
        output_dir=str(output_dir),
    )

    if not result.success:
        logger.error(f"Simulation failed: {result.error_message}")
        error_file = output_dir / "eplusout.err"
        if error_file.exists():
            logger.error(f"Check error log: {error_file}")
        raise RuntimeError(f"Simulation failed: {result.error_message}")

    logger.info(f"✓ Simulation completed in {result.execution_time:.1f}s")

    return output_dir, result.execution_time


def calculate_results(output_dir: Path, floor_area: float) -> None:
    """Calculate and display KPIs from simulation results.

    Args:
        output_dir: Directory containing simulation results
        floor_area: Building floor area in m²
    """
    logger = logging.getLogger(__name__)
    sql_file = output_dir / "eplusout.sql"

    if not sql_file.exists():
        logger.warning("SQL results file not found, skipping KPI calculation")
        return

    logger.info("Calculating KPIs...")

    rechner = KennzahlenRechner(nettoflaeche_m2=floor_area)
    kennzahlen = rechner.berechne_kennzahlen(sql_file=sql_file)

    # Display results
    print("\n" + "=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)
    print(f"Energy Performance: {kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a")
    print(f"Efficiency Class:   {kennzahlen.effizienzklasse}")
    print(f"Heating Demand:     {kennzahlen.heizkennzahl_kwh_m2a:.1f} kWh/m²a")
    print(f"Cooling Demand:     {kennzahlen.kuehlkennzahl_kwh_m2a:.1f} kWh/m²a")
    print(f"Thermal Comfort:    {kennzahlen.thermische_behaglichkeit}")
    print(f"\nAssessment: {kennzahlen.bewertung}")
    print("=" * 60 + "\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run EnergyPlus simulation from YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "config",
        type=Path,
        help="Path to YAML configuration file"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Override output directory from config"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate configuration without running simulation"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info(f"Loading configuration: {args.config}")

        if not args.config.exists():
            logger.error(f"Configuration file not found: {args.config}")
            return 1

        config = SimulationConfig.from_yaml(args.config)
        logger.info(f"✓ Loaded: {config.name}")
        if config.description:
            logger.info(f"  {config.description}")

        # Validate
        validate_config(config)

        if args.validate_only:
            logger.info("Validation complete (--validate-only mode)")
            return 0

        # Run simulation
        logger.info("\n" + "=" * 60)
        logger.info(f"Starting simulation: {config.name}")
        logger.info("=" * 60)

        start_time = datetime.now()

        output_dir, exec_time = run_simulation_from_config(config, args.output)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info(f"✓ Simulation completed successfully!")
        logger.info(f"  Total time: {total_time:.1f}s")
        logger.info(f"  Output: {output_dir}")
        logger.info("=" * 60)

        # Calculate and display results
        floor_area = (
            config.building.geometry.length *
            config.building.geometry.width *
            config.building.geometry.num_floors
        )
        calculate_results(output_dir, floor_area)

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1

    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
