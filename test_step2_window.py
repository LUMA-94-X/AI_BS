#!/usr/bin/env python3
"""Step 2: Add ONE window to the working 1-zone box."""
from pathlib import Path
from eppy.modeleditor import IDF

# Load working 1-zone box
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

idf = IDF(str(Path("output/minimal_test.idf")))

print("=" * 80)
print("STEP 2: Adding ONE WINDOW to 1-Zone Box")
print("=" * 80)

# Add simple window construction (if not exists)
window_mat = idf.idfobjects.get('WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', [])
if not window_mat:
    idf.newidfobject(
        "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
        Name="SimpleWindow",
        UFactor=2.5,
        Solar_Heat_Gain_Coefficient=0.6,
    )

window_const = idf.idfobjects.get('CONSTRUCTION', [])
window_const_exists = any(c.Name == "WindowConstruction" for c in window_const)
if not window_const_exists:
    idf.newidfobject(
        "CONSTRUCTION",
        Name="WindowConstruction",
        Outside_Layer="SimpleWindow",
    )

# Add ONE window on South Wall (2m x 1.5m, centered)
# Wall is at Y=0, from (0,0,0) to (10,0,3)
# Window: 4m from left edge, 2m wide, 0.5m from floor, 1.5m high
idf.newidfobject(
    "FENESTRATIONSURFACE:DETAILED",
    Name="TestZone_Window_South",
    Surface_Type="Window",
    Construction_Name="WindowConstruction",
    Building_Surface_Name="TestZone_Wall_South",
    Outside_Boundary_Condition_Object="",
    View_Factor_to_Ground="autocalculate",
    Frame_and_Divider_Name="",
    Multiplier=1,
    Number_of_Vertices=4,
    # Window vertices (counterclockwise from outside, bottom-left first)
    Vertex_1_Xcoordinate=6.0,  # Right edge
    Vertex_1_Ycoordinate=0.0,
    Vertex_1_Zcoordinate=0.5,  # Bottom
    Vertex_2_Xcoordinate=4.0,  # Left edge
    Vertex_2_Ycoordinate=0.0,
    Vertex_2_Zcoordinate=0.5,  # Bottom
    Vertex_3_Xcoordinate=4.0,  # Left edge
    Vertex_3_Ycoordinate=0.0,
    Vertex_3_Zcoordinate=2.0,  # Top
    Vertex_4_Xcoordinate=6.0,  # Right edge
    Vertex_4_Ycoordinate=0.0,
    Vertex_4_Zcoordinate=2.0,  # Top
)

# Save
output_path = Path("output/test_step2_window.idf")
idf.save(str(output_path))

print(f"\n✅ Created: {output_path}")
print(f"   1 Zone, 6 Surfaces, 1 Window, IdealLoads HVAC")

# Test simulation
from features.simulation.runner import EnergyPlusRunner

print("\n" + "=" * 80)
print("TESTING SIMULATION...")
print("=" * 80)

runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=output_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=Path("output/test_step2_sim"),
    output_prefix="step2"
)

print(f"\n{'='*80}")
print(f"STEP 2 RESULT: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
print(f"{'='*80}")
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

    print(f"Time rows: {time_count:,}")
    print(f"Data rows: {data_count:,}")

    if result.success and time_count > 0:
        print(f"\n🎉 STEP 2 PASSED! 1-Zone + Window works!")
    else:
        print(f"\n❌ STEP 2 FAILED - Window causes crash")
        # Check for errors
        err_file = Path("output/test_step2_sim/step2out.err")
        if err_file.exists() and err_file.stat().st_size > 0:
            print(f"\nErrors:")
            with open(err_file, 'r') as f:
                print(f.read()[:1000])
else:
    print("\n❌ No SQL file - simulation crashed")

print("=" * 80)
