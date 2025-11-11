"""
Example: Batch Simulation

This example demonstrates how to run multiple simulations in parallel
with different building parameters.

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
import logging


def main():
    """Run batch simulations with parameter variations."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("Batch Simulation Example")
    logger.info("=" * 70)

    # Check for weather file
    weather_file = Path("data/weather/example.epw")
    if not weather_file.exists():
        logger.error(f"Weather file not found: {weather_file}")
        logger.info("Please download a weather file and place it in data/weather/")
        return 1

    # Define parameter variations
    variations = [
        {"length": 10, "width": 8, "wwr": 0.2, "floors": 1},
        {"length": 10, "width": 8, "wwr": 0.3, "floors": 1},
        {"length": 10, "width": 8, "wwr": 0.4, "floors": 1},
        {"length": 15, "width": 10, "wwr": 0.3, "floors": 2},
        {"length": 15, "width": 10, "wwr": 0.3, "floors": 3},
    ]

    logger.info(f"\nPreparing {len(variations)} simulations...")

    # Create models
    generator = SimpleBoxGenerator()
    simulations = []

    output_base = Path("output/batch_example")
    output_base.mkdir(parents=True, exist_ok=True)

    for i, var in enumerate(variations, 1):
        # Create geometry
        geometry = BuildingGeometry(
            length=var["length"],
            width=var["width"],
            height=var["floors"] * 3.0,
            num_floors=var["floors"],
            window_wall_ratio=var["wwr"],
            orientation=0.0
        )

        # Create IDF
        sim_name = f"sim_{i:02d}_L{var['length']}_W{var['width']}_WWR{int(var['wwr']*100)}_F{var['floors']}"
        idf_path = output_base / f"{sim_name}.idf"

        try:
            generator.create_model(geometry, idf_path=idf_path)

            # Add to simulation list
            simulations.append({
                "idf_path": idf_path,
                "weather_file": weather_file,
                "output_dir": output_base / f"{sim_name}_results",
                "output_prefix": sim_name,
            })

            logger.info(f"  [{i}/{len(variations)}] Created: {sim_name}")

        except Exception as e:
            logger.error(f"  [{i}/{len(variations)}] Failed: {e}")

    # Run batch simulation
    logger.info(f"\nRunning {len(simulations)} simulations in parallel...")
    logger.info("This may take several minutes...\n")

    try:
        runner = EnergyPlusRunner()
        results = runner.run_batch(simulations, parallel=True)

        # Summarize results
        logger.info("\n" + "=" * 70)
        logger.info("Batch Results Summary")
        logger.info("=" * 70)

        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        logger.info(f"\nTotal simulations: {len(results)}")
        logger.info(f"  Successful: {len(successful)}")
        logger.info(f"  Failed: {len(failed)}")

        if successful:
            total_time = sum(r.execution_time for r in successful)
            avg_time = total_time / len(successful)
            logger.info(f"\nExecution time:")
            logger.info(f"  Total: {total_time:.1f} seconds")
            logger.info(f"  Average: {avg_time:.1f} seconds per simulation")

        if failed:
            logger.warning("\nFailed simulations:")
            for r in failed:
                logger.warning(f"  - {r.idf_path.name}: {r.error_message}")

        logger.info(f"\nResults saved in: {output_base}")

        return 0 if not failed else 1

    except Exception as e:
        logger.error(f"Batch simulation error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
