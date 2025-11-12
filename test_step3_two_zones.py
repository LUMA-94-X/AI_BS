#!/usr/bin/env python3
"""Step 3: Two zones side-by-side with inter-zone wall."""
import tempfile
from pathlib import Path
from eppy.modeleditor import IDF

# Create new IDF from scratch
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

minimal_content = "VERSION,\n  25.1;\n"
with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False) as f:
    f.write(minimal_content)
    temp_path = f.name

idf = IDF(temp_path)
Path(temp_path).unlink()

print("=" * 80)
print("STEP 3: TWO ZONES SIDE-BY-SIDE (Inter-Zone Wall)")
print("=" * 80)

# Global settings (copy from working minimal test)
idf.newidfobject("GLOBALGEOMETRYRULES", Starting_Vertex_Position="UpperLeftCorner",
                 Vertex_Entry_Direction="Counterclockwise", Coordinate_System="Relative")
idf.newidfobject("SIMULATIONCONTROL", Do_Zone_Sizing_Calculation="No",
                 Do_System_Sizing_Calculation="No", Do_Plant_Sizing_Calculation="No",
                 Run_Simulation_for_Sizing_Periods="No",
                 Run_Simulation_for_Weather_File_Run_Periods="Yes")
idf.newidfobject("BUILDING", Name="TwoZone_Test", North_Axis=0.0, Terrain="Suburbs",
                 Loads_Convergence_Tolerance_Value=0.04,
                 Temperature_Convergence_Tolerance_Value=0.4,
                 Solar_Distribution="FullExterior")
idf.newidfobject("HEATBALANCEALGORITHM", Algorithm="ConductionTransferFunction")
idf.newidfobject("TIMESTEP", Number_of_Timesteps_per_Hour=4)
idf.newidfobject("RUNPERIOD", Name="Annual", Begin_Month=1, Begin_Day_of_Month=1,
                 End_Month=12, End_Day_of_Month=31, Day_of_Week_for_Start_Day="Monday",
                 Use_Weather_File_Holidays_and_Special_Days="Yes",
                 Use_Weather_File_Daylight_Saving_Period="Yes")
idf.newidfobject("SITE:LOCATION", Name="Test_Location", Latitude=52.5, Longitude=13.4,
                 Time_Zone=1.0, Elevation=50.0)

# Material & Construction
idf.newidfobject("MATERIAL", Name="TestMaterial", Roughness="Rough", Thickness=0.2,
                 Conductivity=1.0, Density=1000.0, Specific_Heat=1000.0)
idf.newidfobject("CONSTRUCTION", Name="TestConstruction", Outside_Layer="TestMaterial")

# OUTPUT
idf.newidfobject("OUTPUTCONTROL:TABLE:STYLE", Column_Separator="HTML")
idf.newidfobject("OUTPUT:SQLITE", Option_Type="SimpleAndTabular",
                 Unit_Conversion_for_Tabular_Data="UseOutputControlTableStyle")
idf.newidfobject("OUTPUT:VARIABLE", Key_Value="*",
                 Variable_Name="Zone Mean Air Temperature",
                 Reporting_Frequency="Hourly")

# === ZONE WEST (0-5m) ===
idf.newidfobject("ZONE", Name="Zone_West", Direction_of_Relative_North=0.0,
                 X_Origin=0.0, Y_Origin=0.0, Z_Origin=0.0, Type=1)

# West Zone - Floor
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_West_Floor", Surface_Type="Floor",
                 Construction_Name="TestConstruction", Zone_Name="Zone_West",
                 Outside_Boundary_Condition="Ground", Sun_Exposure="NoSun",
                 Wind_Exposure="NoWind", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=5.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=5.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=0.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=0.0)

# West Zone - Roof
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_West_Roof", Surface_Type="Roof",
                 Construction_Name="TestConstruction", Zone_Name="Zone_West",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=5.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=5.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# West Zone - North Wall (exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_West_Wall_North", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_West",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=5.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=5.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# West Zone - South Wall (exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_West_Wall_South", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_West",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=5.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=0.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=0.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=5.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

# West Zone - West Wall (exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_West_Wall_West", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_West",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=0.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=0.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

# West Zone - East Wall (INTER-ZONE to Zone_East)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_West_Wall_ToEast", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_West",
                 Outside_Boundary_Condition="Surface",
                 Outside_Boundary_Condition_Object="Zone_East_Wall_ToWest",
                 Sun_Exposure="NoSun", Wind_Exposure="NoWind", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=5.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=5.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=5.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=5.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# === ZONE EAST (5-10m) ===
idf.newidfobject("ZONE", Name="Zone_East", Direction_of_Relative_North=0.0,
                 X_Origin=0.0, Y_Origin=0.0, Z_Origin=0.0, Type=1)

# East Zone - Floor
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_East_Floor", Surface_Type="Floor",
                 Construction_Name="TestConstruction", Zone_Name="Zone_East",
                 Outside_Boundary_Condition="Ground", Sun_Exposure="NoSun",
                 Wind_Exposure="NoWind", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=5.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=0.0,
                 Vertex_4_Xcoordinate=5.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=0.0)

# East Zone - Roof
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_East_Roof", Surface_Type="Roof",
                 Construction_Name="TestConstruction", Zone_Name="Zone_East",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=5.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=5.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# East Zone - North Wall (exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_East_Wall_North", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_East",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=5.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=5.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# East Zone - South Wall (exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_East_Wall_South", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_East",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=10.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=5.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=5.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=10.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

# East Zone - East Wall (exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_East_Wall_East", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_East",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=10.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=10.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# East Zone - West Wall (INTER-ZONE to Zone_West) - MUST BE REVERSED!
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_East_Wall_ToWest", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_East",
                 Outside_Boundary_Condition="Surface",
                 Outside_Boundary_Condition_Object="Zone_West_Wall_ToEast",
                 Sun_Exposure="NoSun", Wind_Exposure="NoWind", Number_of_Vertices=4,
                 # REVERSED from Zone_West_Wall_ToEast!
                 Vertex_1_Xcoordinate=5.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=5.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=5.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=5.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

# Apply HVAC
from features.hvac.ideal_loads import HVACTemplateManager
manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Save
output_path = Path("output/test_step3_two_zones.idf")
idf.save(str(output_path))

print(f"\n✅ Created: {output_path}")
print(f"   2 Zones, 12 Surfaces (2 Inter-Zone Walls), IdealLoads HVAC")

# Test simulation
from features.simulation.runner import EnergyPlusRunner

print("\n" + "=" * 80)
print("TESTING SIMULATION...")
print("=" * 80)

runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=output_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=Path("output/test_step3_sim"),
    output_prefix="step3"
)

print(f"\n{'='*80}")
print(f"STEP 3 RESULT: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
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

    print(f"SQL: {result.sql_file.stat().st_size / 1_000_000:.2f} MB")
    print(f"Time rows: {time_count:,}")
    print(f"Data rows: {data_count:,}")

    if result.success and time_count > 8000:
        print(f"\n🎉🎉🎉 STEP 3 PASSED! 2-Zones + Inter-Zone Wall works! 🎉🎉🎉")
    else:
        print(f"\n❌ STEP 3 FAILED")
else:
    print("\n❌ No SQL file - simulation crashed")

# Check for errors
err_file = Path("output/test_step3_sim/step3out.err")
if err_file.exists() and err_file.stat().st_size > 0:
    print(f"\nError file ({err_file.stat().st_size} bytes):")
    with open(err_file, 'r') as f:
        content = f.read()
        if "upside down" in content.lower():
            print("  ⚠️ Contains 'upside down' warnings")
        # Show first 20 lines
        for line in content.split('\n')[:20]:
            if 'severe' in line.lower() or 'fatal' in line.lower():
                print(f"  {line}")

print("=" * 80)
