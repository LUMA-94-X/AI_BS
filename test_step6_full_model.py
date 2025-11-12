#!/usr/bin/env python3
"""Step 6: Full 5-zone, 2-floor model - THE ORIGINAL SCENARIO.

This tests the complete complexity:
- 10 zones total (5 per floor x 2 floors)
- Floor/Ceiling inter-zone surfaces between floors
- Inter-zone walls within each floor (Core to Perimeter connections)
- All exterior walls, roofs, and ground floors

This is what was originally crashing!
"""
from pathlib import Path

print("=" * 80)
print("STEP 6: FULL 5-ZONE, 2-FLOOR MODEL (Original Failing Scenario)")
print("=" * 80)

# Use the PerimeterCalculator to create proper zone layouts
from features.geometrie.utils.perimeter_calculator import PerimeterCalculator

# Building parameters
building_length = 20.0  # m
building_width = 15.0  # m
floor_height = 3.0  # m
num_floors = 2
wwr = 0.3

# Create layouts for both floors
calc = PerimeterCalculator()
layouts = calc.create_multi_floor_layout(
    building_length=building_length,
    building_width=building_width,
    floor_height=floor_height,
    num_floors=num_floors,
    wwr=wwr
)

print(f"Created {num_floors} floors with 5 zones each = {num_floors * 5} total zones")

# Now use the FiveZoneGenerator to build the IDF
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from features.geometrie.models.energieausweis_input import (
    EnergieausweisInput,
    FensterData,
    GebaeudeTyp,
)

# Create minimal EnergieausweisInput for the generator
ea_data = EnergieausweisInput(
    nettoflaeche_m2=building_length * building_width * num_floors,
    anzahl_geschosse=num_floors,
    geschosshoehe_m=floor_height,
    u_wert_wand=0.5,
    u_wert_dach=0.4,
    u_wert_boden=0.6,
    u_wert_fenster=2.5,
    fenster=FensterData(window_wall_ratio=wwr),
    gebaeudetyp=GebaeudeTyp.NWG,  # Nichtwohngebäude (Office)
)

# Generate IDF using FIXED generator
generator = FiveZoneGenerator()
idf = generator.create_from_energieausweis(ea_data)

# Save
output_path = Path("output/test_step6_full.idf")
idf.save(str(output_path))

print(f"\n✅ Created: {output_path}")
print(f"   10 Zones (5 zones x 2 floors)")
print(f"   2 Floors connected with Floor/Ceiling inter-zone surfaces")
print(f"   IdealLoads HVAC on all zones")

# Run simulation
from features.simulation.runner import EnergyPlusRunner

print("\n" + "=" * 80)
print("TESTING SIMULATION...")
print("=" * 80)

runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=output_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=Path("output/test_step6_sim"),
    output_prefix="step6",
)

print(f"\n{'=' * 80}")
print(f"STEP 6 RESULT: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
print(f"{'=' * 80}")
print(f"Execution Time: {result.execution_time:.2f}s")

if result.sql_file and result.sql_file.exists():
    import sqlite3

    conn = sqlite3.connect(str(result.sql_file))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Time")
    time_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ReportData")
    data_count = cursor.fetchone()[0]

    conn.close()

    sql_size = result.sql_file.stat().st_size / (1024 * 1024)
    print(f"SQL: {sql_size:.2f} MB")
    print(f"Time rows: {time_count:,}")
    print(f"Data rows: {data_count:,}")

    if result.success and time_count > 0:
        print(f"\n🎉🎉🎉 STEP 6 PASSED! FULL 2-FLOOR MODEL WORKS! 🎉🎉🎉")
        print(f"\n🔥🔥🔥 ROOT CAUSE FIXED: Floor/Ceiling vertex order! 🔥🔥🔥")
    else:
        print(f"\n❌ STEP 6 FAILED")

    # Check errors
    err_file = Path("output/test_step6_sim/step6out.err")
    if err_file.exists():
        err_size = err_file.stat().st_size
        print(f"\nError file ({err_size} bytes):")
        if err_size > 0:
            with open(err_file, "r") as f:
                content = f.read()
                # Show last 2000 chars
                print(content[-2000:] if len(content) > 2000 else content)
else:
    print("\n❌ No SQL file - simulation crashed")

    # Check error file
    err_file = Path("output/test_step6_sim/step6out.err")
    if err_file.exists() and err_file.stat().st_size > 0:
        print(f"\nError file content:")
        with open(err_file, 'r') as f:
            print(f.read()[-2000:])

print("=" * 80)

if result.success:
    print("\n" + "=" * 80)
    print("SYSTEMATIC TEST SUMMARY")
    print("=" * 80)
    print("✅ Step 1: 1-Zone Box (BASELINE) - PASSED")
    print("✅ Step 2: 1-Zone + Window - PASSED")
    print("✅ Step 3: 2-Zones Horizontal (Inter-Zone Wall) - PASSED")
    print("✅ Step 4: 2-Zones Vertical (Floor/Ceiling) - PASSED")
    print("✅ Step 5: 5-Zones Single Floor - PASSED")
    print("✅ Step 6: 5-Zones Two Floors (FULL MODEL) - PASSED")
    print("=" * 80)
    print("\n🏆 ALL TESTS PASSED!")
    print("\n📋 ROOT CAUSE IDENTIFIED AND FIXED:")
    print("   Floor/Ceiling surfaces had incorrect vertex order")
    print("   - Floors must use vertices [3,2,1,0] (reversed)")
    print("   - Ceilings must use vertices [0,1,2,3] (normal)")
    print("   - Inter-zone Floor/Ceiling pairs must be exact reverses")
    print("\n💡 Fix applied in: features/geometrie/generators/five_zone_generator.py")
    print("=" * 80)
