"""Quick simulation test for IDF with PEOPLE objects."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import get_config
from features.simulation.runner import EnergyPlusRunner


def main():
    # Config
    config = get_config()

    # Paths
    idf_path = project_root / "output" / "energieausweis" / "gebaeude_5zone_with_people.idf"
    weather_file = Path("C:/EnergyPlusV25-1-0/WeatherData/DEU_Berlin-Tempelhof.166550_IWEC.epw")

    if not idf_path.exists():
        print(f"❌ IDF not found: {idf_path}")
        print("   Run test_native_internal_loads.py first!")
        return

    if not weather_file.exists():
        print(f"❌ Weather file not found: {weather_file}")
        return

    print(f"🏃 Running simulation...")
    print(f"   IDF: {idf_path.name}")
    print(f"   Weather: {weather_file.name}")
    print()

    # Run simulation
    runner = EnergyPlusRunner(config)
    result = runner.run_simulation(
        idf_path=idf_path,
        weather_file=weather_file,
    )

    if result.success:
        print(f"\n✅ SIMULATION SUCCESSFUL!")
        print(f"   Output dir: {result.output_dir}")
        print(f"   SQL file: {result.sql_file}")
        print(f"   Execution time: {result.execution_time:.1f}s")

        # Check timesteps
        if result.sql_file and result.sql_file.exists():
            import sqlite3
            try:
                conn = sqlite3.connect(str(result.sql_file))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ReportData")
                timesteps = cursor.fetchone()[0]
                conn.close()

                print(f"\n📊 TIMESTEPS: {timesteps}")

                if timesteps == 8760:
                    print("   ✅ PERFECT! Full year simulation!")
                elif timesteps > 0:
                    print(f"   ⚠️  Expected 8760, got {timesteps}")
                else:
                    print("   ❌ NO DATA!")

            except Exception as e:
                print(f"   ⚠️  Could not query SQL: {e}")

        # Check file sizes
        sql_size_mb = result.sql_file.stat().st_size / (1024 * 1024) if result.sql_file else 0
        print(f"\n📁 SQL file size: {sql_size_mb:.1f} MB")

        if sql_size_mb > 10:
            print("   ✅ Good size (>10MB)")
        else:
            print(f"   ⚠️  Small size (<10MB) - might be incomplete")

    else:
        print(f"\n❌ SIMULATION FAILED!")
        print(f"   Error: {result.error_message}")


if __name__ == "__main__":
    main()
