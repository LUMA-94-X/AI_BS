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
    print("\n🚀 Next step:")
    print("   Run simulation on this IDF file and check for 8760 timesteps!")
    print(f"   Path: {output_path}")


if __name__ == "__main__":
    main()
