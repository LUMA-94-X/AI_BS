#!/usr/bin/env python3
"""Debug script to manually test EnergyPlus simulation."""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from features.simulation.runner import EnergyPlusRunner
from core.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run a test simulation with detailed logging."""

    # Paths
    idf_path = Path("output/energieausweis/gebaeude_5zone.idf")
    weather_file = Path("data/weather/example.epw")
    output_dir = Path("output/test_debug_simulation")

    if not idf_path.exists():
        logger.error(f"IDF not found: {idf_path}")
        return

    if not weather_file.exists():
        logger.error(f"Weather file not found: {weather_file}")
        return

    logger.info("="*80)
    logger.info("STARTING DEBUG SIMULATION")
    logger.info("="*80)
    logger.info(f"IDF: {idf_path}")
    logger.info(f"Weather: {weather_file}")
    logger.info(f"Output: {output_dir}")
    logger.info("="*80)

    # Get config and temporarily set keep_intermediate_files to True
    config = get_config()
    original_keep = config.simulation.keep_intermediate_files
    config.simulation.keep_intermediate_files = True
    logger.info(f"Set keep_intermediate_files = True (was {original_keep})")

    # Create runner
    runner = EnergyPlusRunner(config)

    logger.info(f"EnergyPlus executable: {runner.energyplus_exe}")
    logger.info(f"ExpandObjects: {runner.expand_objects_exe}")
    logger.info(f"ExpandObjects exists: {runner.expand_objects_exe.exists()}")

    # Check IDF for HVACTemplate objects
    needs_expand = runner._needs_expand_objects(idf_path)
    logger.info(f"Needs ExpandObjects: {needs_expand}")

    # Run simulation
    result = runner.run_simulation(
        idf_path=str(idf_path),
        weather_file=str(weather_file),
        output_dir=str(output_dir),
        output_prefix="eplus"
    )

    logger.info("="*80)
    logger.info("SIMULATION RESULT")
    logger.info("="*80)
    logger.info(f"Success: {result.success}")
    logger.info(f"Execution time: {result.execution_time:.2f}s")
    logger.info(f"Output dir: {result.output_dir}")
    logger.info(f"Error message: {result.error_message}")
    logger.info(f"SQL file: {result.sql_file}")
    logger.info(f"SQL exists: {result.sql_file.exists() if result.sql_file else False}")
    logger.info(f"SQL size: {result.sql_file.stat().st_size if result.sql_file and result.sql_file.exists() else 0} bytes")

    # Check output files
    logger.info("="*80)
    logger.info("OUTPUT FILES")
    logger.info("="*80)
    if result.output_dir.exists():
        for f in sorted(result.output_dir.iterdir()):
            size = f.stat().st_size if f.is_file() else 0
            logger.info(f"  {f.name:30s} {size:>10,} bytes")

    # Check err file
    err_file = result.output_dir / "eplusout.err"
    if err_file.exists():
        logger.info("="*80)
        logger.info("ERROR FILE CONTENT (first 100 lines)")
        logger.info("="*80)
        with open(err_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()[:100]
            for line in lines:
                logger.info(line.rstrip())
    else:
        logger.warning("Error file does not exist!")

if __name__ == "__main__":
    main()
