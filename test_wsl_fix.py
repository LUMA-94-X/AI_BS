#!/usr/bin/env python3
"""Test WSL path conversion fix."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Force reload of runner module
if 'features.simulation.runner' in sys.modules:
    del sys.modules['features.simulation.runner']

from features.simulation.runner import EnergyPlusRunner
from core.config import get_config

def main():
    """Test simulation with WSL path conversion."""

    # Paths
    idf_path = Path("output/energieausweis/gebaeude_5zone.idf")
    weather_file = Path("data/weather/example.epw")
    output_dir = Path("output/test_wsl_fix")

    print("="*80)
    print("TESTING WSL PATH CONVERSION FIX")
    print("="*80)
    print(f"IDF: {idf_path.absolute()}")
    print(f"Weather: {weather_file.absolute()}")
    print(f"Output: {output_dir.absolute()}")
    print("="*80)

    # Get config
    config = get_config()
    config.simulation.keep_intermediate_files = True

    # Create runner
    print("\n Creating EnergyPlusRunner...")
    runner = EnergyPlusRunner(config)

    print(f"EnergyPlus executable: {runner.energyplus_exe}")
    print(f"ExpandObjects: {runner.expand_objects_exe}")

    # Test path conversion
    print("\n" + "="*80)
    print("TESTING PATH CONVERSION")
    print("="*80)

    test_path = Path("/mnt/c/Users/lugma/source/repos/AI_BS/data/weather/example.epw")
    converted = runner._convert_wsl_to_windows_path(test_path)
    print(f"Original:  {test_path}")
    print(f"Converted: {converted}")
    print("="*80)

    # Run simulation
    print("\n" + "="*80)
    print("RUNNING SIMULATION")
    print("="*80)

    result = runner.run_simulation(
        idf_path=str(idf_path),
        weather_file=str(weather_file),
        output_dir=str(output_dir),
        output_prefix="eplus"
    )

    print("\n" + "="*80)
    print("RESULT")
    print("="*80)
    print(f"Success: {result.success}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print(f"Error message: {result.error_message}")
    print(f"Output dir: {result.output_dir}")

    # Check files
    err_file = result.output_dir / "eplusout.err"
    sql_file = result.output_dir / "eplusout.sql"

    if err_file.exists():
        err_size = err_file.stat().st_size
        print(f"\nErr file size: {err_size:,} bytes")

        if err_size > 0:
            print("\n" + "="*80)
            print("ERR FILE CONTENT (first 100 lines)")
            print("="*80)
            with open(err_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[:100]
                for line in lines:
                    print(line.rstrip())
        else:
            print("⚠️ ERR FILE IS EMPTY!")
    else:
        print("❌ ERR FILE DOES NOT EXIST!")

    if sql_file.exists():
        sql_size = sql_file.stat().st_size
        print(f"\nSQL file size: {sql_size:,} bytes")
        if sql_size < 500_000:
            print("⚠️ SQL FILE IS SUSPICIOUSLY SMALL!")
    else:
        print("❌ SQL FILE DOES NOT EXIST!")

if __name__ == "__main__":
    main()
