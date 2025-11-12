"""Test script for native internal loads - minimal test case.

This script tests the new NativeInternalLoadsManager by:
1. Loading the existing IDF from output/energieausweis/gebaeude_5zone.idf
2. Adding internal loads (PEOPLE only for first test)
3. Saving to a new file
4. User can then run simulation to verify it works
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eppy.modeleditor import IDF
from features.internal_loads.native_loads import NativeInternalLoadsManager


def main():
    # Path to existing IDF (created by UI)
    idf_path = Path(__file__).parent.parent / "output" / "energieausweis" / "gebaeude_5zone.idf"

    if not idf_path.exists():
        print(f"❌ IDF file not found: {idf_path}")
        print("   Please create geometry first in the UI!")
        return

    print(f"📂 Loading IDF from: {idf_path}")

    # Set IDD file for eppy (required!)
    idd_path = Path("C:/EnergyPlusV25-1-0/Energy+.idd")
    if not idd_path.exists():
        print(f"❌ IDD file not found: {idd_path}")
        print("   Please check EnergyPlus installation!")
        return

    IDF.setiddname(str(idd_path))
    print(f"✅ IDD file set: {idd_path}")

    # Load IDF
    idf = IDF(str(idf_path))

    # Get zones
    zones = idf.idfobjects.get("ZONE", [])
    if not zones:
        print("❌ No zones found in IDF!")
        return

    print(f"✅ Found {len(zones)} zones")

    # Calculate zone areas from existing geometry
    zone_areas = {}
    for zone in zones:
        zone_name = zone.Name
        # Get all surfaces for this zone
        surfaces = [
            s for s in idf.idfobjects.get("BUILDINGSURFACE:DETAILED", [])
            if hasattr(s, "Zone_Name") and s.Zone_Name == zone_name and s.Surface_Type == "Floor"
        ]
        # Sum floor areas (rough approximation from coordinates)
        area = 100.0  # default if we can't calculate
        if surfaces:
            # TODO: Calculate actual area from vertices
            # For now, assume 100m² per zone
            area = 100.0

        zone_areas[zone_name] = area
        print(f"   Zone: {zone_name} (~{area:.1f} m²)")

    # Initialize native loads manager
    manager = NativeInternalLoadsManager()

    # Get zone names
    zone_names = [z.Name for z in zones]

    # Add ONLY PEOPLE for first test (minimal change)
    print("\n🔥 TEST 1: Adding PEOPLE only...")
    schedules = manager.add_schedules(idf, building_type="office")
    print(f"   ✅ Added {len(schedules)} schedules")

    for zone_name in zone_names:
        area = zone_areas.get(zone_name, 100.0)
        manager.add_people_to_zone(
            idf,
            zone_name,
            area,
            building_type="office",
            schedule_name=schedules["occupancy"],
            activity_schedule=schedules["activity"],
        )

    # Save to new file
    output_path = idf_path.parent / "gebaeude_5zone_with_people.idf"
    idf.save(str(output_path))

    print(f"\n✅ Saved IDF with PEOPLE to: {output_path}")
    print("\n📋 Summary:")
    print(f"   - Zones: {len(zones)}")
    print(f"   - PEOPLE objects: {len(idf.idfobjects.get('PEOPLE', []))}")
    print(f"   - Schedules: {len(idf.idfobjects.get('SCHEDULE:CONSTANT', []))}")

    # ========================================
    # RUN SIMULATION
    # ========================================
    print("\n" + "="*60)
    print("🏃 STARTING ENERGYPLUS SIMULATION")
    print("="*60)

    from core.config import get_config
    from features.simulation.runner import EnergyPlusRunner

    config = get_config()
    weather_file = Path("C:/EnergyPlusV25-1-0/WeatherData/DEU_Berlin-Tempelhof.166550_IWEC.epw")

    if not weather_file.exists():
        print(f"❌ Weather file not found: {weather_file}")
        return

    print(f"   IDF: {output_path.name}")
    print(f"   Weather: {weather_file.name}")
    print()

    runner = EnergyPlusRunner(config)
    result = runner.run_simulation(
        idf_path=output_path,
        weather_file=weather_file,
    )

    print("\n" + "="*60)
    if result.success:
        print("✅ SIMULATION SUCCESSFUL!")
        print("="*60)
        print(f"   Output dir: {result.output_dir}")
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

                sql_size_mb = result.sql_file.stat().st_size / (1024 * 1024)

                print(f"\n📊 RESULTS:")
                print(f"   Timesteps: {timesteps}")
                print(f"   SQL size: {sql_size_mb:.1f} MB")

                if timesteps == 8760:
                    print("\n   🎉 PERFECT! Full year simulation with PEOPLE objects!")
                    print("   ✅ Native approach works!")
                elif timesteps > 0:
                    print(f"\n   ⚠️  Expected 8760, got {timesteps}")
                else:
                    print("\n   ❌ NO DATA!")

            except Exception as e:
                print(f"   ⚠️  Could not query SQL: {e}")
    else:
        print("❌ SIMULATION FAILED!")
        print("="*60)
        print(f"   Error: {result.error_message}")


if __name__ == "__main__":
    main()
