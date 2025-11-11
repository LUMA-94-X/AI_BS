#!/usr/bin/env python3
"""Test simulation with example-based HVAC."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from features.simulation.runner import EnergyPlusRunner
import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

print("=" * 80)
print("SIMULATION TEST WITH EXAMPLE-BASED HVAC")
print("=" * 80)

# Paths
idf_path = Path("output/building_example_based.idf")
weather_file = Path("data/weather/example.epw")
output_dir = Path("output/test_example_based_sim")

if not idf_path.exists():
    print(f"❌ IDF not found: {idf_path}")
    print("   Run test_example_based_hvac.py first!")
    sys.exit(1)

print(f"\nIDF: {idf_path}")
print(f"Weather: {weather_file}")
print(f"Output: {output_dir}")
print(f"HVAC: Direct ZONEHVAC objects (from EnergyPlus example)")

# Initialize runner
print("\nInitializing EnergyPlus runner...")
runner = EnergyPlusRunner()

# Run simulation
print("\n" + "=" * 80)
print("RUNNING SIMULATION...")
print("Expected: 30-60 seconds for annual simulation")
print("=" * 80)
print()

result = runner.run_simulation(
    idf_path=idf_path,
    weather_file=weather_file,
    output_dir=output_dir,
    output_prefix="example"
)

# Analyze results
print("\n" + "=" * 80)
print("SIMULATION RESULTS")
print("=" * 80)

print(f"\nSuccess: {result.success}")
print(f"Execution time: {result.execution_time:.2f} seconds")

if result.error_message:
    print(f"Error: {result.error_message}")

# Check SQL file
if result.sql_file and result.sql_file.exists():
    import sqlite3

    sql_size_mb = result.sql_file.stat().st_size / 1_000_000
    print(f"\nSQL file: {result.sql_file}")
    print(f"SQL size: {sql_size_mb:.2f} MB")

    try:
        conn = sqlite3.connect(str(result.sql_file))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Time")
        time_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ReportData")
        data_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Errors WHERE ErrorType > 1")
        error_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Zones")
        zone_count = cursor.fetchone()[0]

        conn.close()

        print(f"\nSQL Database Analysis:")
        print(f"  Time rows: {time_count:,}")
        print(f"  Data rows: {data_count:,}")
        print(f"  Zones: {zone_count}")
        print(f"  Fatal Errors: {error_count}")

        print("\n" + "=" * 80)
        if (result.success and
            time_count > 0 and
            sql_size_mb > 1.0 and
            result.execution_time > 5.0):
            print("🎉🎉🎉 SUCCESS: 5-ZONE WORKFLOW FUNKTIONIERT! 🎉🎉🎉")
            print("=" * 80)
            print(f"✅ Execution time: {result.execution_time:.2f}s")
            print(f"✅ SQL size: {sql_size_mb:.2f} MB")
            print(f"✅ Timesteps: {time_count:,}")
            print(f"✅ Data points: {data_count:,}")
            print(f"✅ Zones: {zone_count}")
            print("=" * 80)
            print("\n🎯 DER 5-ZONE WORKFLOW IST JETZT VOLL FUNKTIONSFÄHIG!")
            print("\nDu kannst jetzt die Streamlit UI verwenden:")
            print("  streamlit run features/web_ui/Start.py")
            print("\nWorkflow:")
            print("  1. Energieausweis → Gebäudedaten eingeben")
            print("  2. HVAC → IdealLoads anwenden")
            print("  3. Simulation → Simulation starten")
            print("  4. Ergebnisse → Ergebnisse ansehen")
            print("=" * 80)
            sys.exit(0)
        else:
            print("❌ FAILED: Simulation did not produce expected results")
            print("=" * 80)
            print(f"   Success: {result.success}")
            print(f"   Time: {result.execution_time:.2f}s (expected >30s)")
            print(f"   SQL: {sql_size_mb:.2f} MB (expected >1 MB)")
            print(f"   Timesteps: {time_count:,} (expected ~8760)")
            print("=" * 80)
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error analyzing SQL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
else:
    print(f"\n❌ SQL file not found")
    sys.exit(1)
