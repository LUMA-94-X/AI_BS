#!/usr/bin/env python3
"""Step 4: Two zones stacked vertically (Floor/Ceiling matching)."""
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
print("STEP 4: TWO ZONES STACKED VERTICALLY (Floor/Ceiling)")
print("=" * 80)

# Global settings
idf.newidfobject("GLOBALGEOMETRYRULES", Starting_Vertex_Position="UpperLeftCorner",
                 Vertex_Entry_Direction="Counterclockwise", Coordinate_System="Relative")
idf.newidfobject("SIMULATIONCONTROL", Do_Zone_Sizing_Calculation="No",
                 Do_System_Sizing_Calculation="No", Do_Plant_Sizing_Calculation="No",
                 Run_Simulation_for_Sizing_Periods="No",
                 Run_Simulation_for_Weather_File_Run_Periods="Yes")
idf.newidfobject("BUILDING", Name="VerticalZones_Test", North_Axis=0.0, Terrain="Suburbs",
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

# === ZONE LOWER (Z=0-3m) ===
idf.newidfobject("ZONE", Name="Zone_Lower", Direction_of_Relative_North=0.0,
                 X_Origin=0.0, Y_Origin=0.0, Z_Origin=0.0, Type=1)

# Lower Zone - Floor (on Ground)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Lower_Floor", Surface_Type="Floor",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Lower",
                 Outside_Boundary_Condition="Ground", Sun_Exposure="NoSun",
                 Wind_Exposure="NoWind", Number_of_Vertices=4,
                 # Floor vertices: REVERSED [3,2,1,0] so normal points DOWN
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=0.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=0.0)

# Lower Zone - Ceiling (Inter-Zone to Upper)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Lower_Ceiling", Surface_Type="Ceiling",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Lower",
                 Outside_Boundary_Condition="Surface",
                 Outside_Boundary_Condition_Object="Zone_Upper_Floor",
                 Sun_Exposure="NoSun", Wind_Exposure="NoWind", Number_of_Vertices=4,
                 # Ceiling vertices: [0,1,2,3] so normal points UP
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

# Lower Zone - 4 Exterior Walls
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Lower_Wall_North", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Lower",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Lower_Wall_East", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Lower",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=10.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=10.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=3.0)

idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Lower_Wall_South", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Lower",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=10.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=0.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=0.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=10.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Lower_Wall_West", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Lower",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=0.0,
                 Vertex_2_Xcoordinate=0.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=0.0,
                 Vertex_3_Xcoordinate=0.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

# === ZONE UPPER (Z=3-6m) ===
idf.newidfobject("ZONE", Name="Zone_Upper", Direction_of_Relative_North=0.0,
                 X_Origin=0.0, Y_Origin=0.0, Z_Origin=0.0, Type=1)

# Upper Zone - Floor (Inter-Zone to Lower) - MUST BE REVERSED FROM CEILING BELOW!
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Upper_Floor", Surface_Type="Floor",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Upper",
                 Outside_Boundary_Condition="Surface",
                 Outside_Boundary_Condition_Object="Zone_Lower_Ceiling",
                 Sun_Exposure="NoSun", Wind_Exposure="NoWind", Number_of_Vertices=4,
                 # Floor vertices: EXACT REVERSE of Ceiling below!
                 # Ceiling was: [0,1,2,3] = [(0,0,3), (10,0,3), (10,10,3), (0,10,3)]
                 # Floor must be: [3,2,1,0] = [(0,10,3), (10,10,3), (10,0,3), (0,0,3)]
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=3.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=3.0)

# Upper Zone - Roof (Exterior)
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Upper_Roof", Surface_Type="Roof",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Upper",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 # Roof vertices: [0,1,2,3] so normal points UP
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=6.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=6.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=6.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=6.0)

# Upper Zone - 4 Exterior Walls
idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Upper_Wall_North", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Upper",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=6.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=6.0)

idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Upper_Wall_East", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Upper",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=10.0, Vertex_1_Ycoordinate=10.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=10.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=10.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=6.0,
                 Vertex_4_Xcoordinate=10.0, Vertex_4_Ycoordinate=10.0, Vertex_4_Zcoordinate=6.0)

idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Upper_Wall_South", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Upper",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=10.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=0.0, Vertex_2_Ycoordinate=0.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=0.0, Vertex_3_Ycoordinate=0.0, Vertex_3_Zcoordinate=6.0,
                 Vertex_4_Xcoordinate=10.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=6.0)

idf.newidfobject("BUILDINGSURFACE:DETAILED", Name="Zone_Upper_Wall_West", Surface_Type="Wall",
                 Construction_Name="TestConstruction", Zone_Name="Zone_Upper",
                 Outside_Boundary_Condition="Outdoors", Sun_Exposure="SunExposed",
                 Wind_Exposure="WindExposed", Number_of_Vertices=4,
                 Vertex_1_Xcoordinate=0.0, Vertex_1_Ycoordinate=0.0, Vertex_1_Zcoordinate=3.0,
                 Vertex_2_Xcoordinate=0.0, Vertex_2_Ycoordinate=10.0, Vertex_2_Zcoordinate=3.0,
                 Vertex_3_Xcoordinate=0.0, Vertex_3_Ycoordinate=10.0, Vertex_3_Zcoordinate=6.0,
                 Vertex_4_Xcoordinate=0.0, Vertex_4_Ycoordinate=0.0, Vertex_4_Zcoordinate=6.0)

# Apply HVAC
from features.hvac.ideal_loads import HVACTemplateManager
manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Save
output_path = Path("output/test_step4_vertical.idf")
idf.save(str(output_path))

print(f"\n✅ Created: {output_path}")
print(f"   2 Zones (Stacked), 12 Surfaces, Floor/Ceiling Match, IdealLoads HVAC")

# Verify Floor/Ceiling matching
print(f"\n🔍 Verifying Floor/Ceiling Vertex Matching:")
surfaces = idf.idfobjects.get('BUILDINGSURFACE:DETAILED', [])
ceiling = [s for s in surfaces if s.Name == "Zone_Lower_Ceiling"][0]
floor = [s for s in surfaces if s.Name == "Zone_Upper_Floor"][0]

print(f"\nCeiling vertices:")
print(f"  V1: ({ceiling.Vertex_1_Xcoordinate}, {ceiling.Vertex_1_Ycoordinate}, {ceiling.Vertex_1_Zcoordinate})")
print(f"  V2: ({ceiling.Vertex_2_Xcoordinate}, {ceiling.Vertex_2_Ycoordinate}, {ceiling.Vertex_2_Zcoordinate})")
print(f"  V3: ({ceiling.Vertex_3_Xcoordinate}, {ceiling.Vertex_3_Ycoordinate}, {ceiling.Vertex_3_Zcoordinate})")
print(f"  V4: ({ceiling.Vertex_4_Xcoordinate}, {ceiling.Vertex_4_Ycoordinate}, {ceiling.Vertex_4_Zcoordinate})")

print(f"\nFloor vertices (should be REVERSED):")
print(f"  V1: ({floor.Vertex_1_Xcoordinate}, {floor.Vertex_1_Ycoordinate}, {floor.Vertex_1_Zcoordinate})")
print(f"  V2: ({floor.Vertex_2_Xcoordinate}, {floor.Vertex_2_Ycoordinate}, {floor.Vertex_2_Zcoordinate})")
print(f"  V3: ({floor.Vertex_3_Xcoordinate}, {floor.Vertex_3_Ycoordinate}, {floor.Vertex_3_Zcoordinate})")
print(f"  V4: ({floor.Vertex_4_Xcoordinate}, {floor.Vertex_4_Ycoordinate}, {floor.Vertex_4_Zcoordinate})")

# Check if reversed
is_match = (
    floor.Vertex_1_Xcoordinate == ceiling.Vertex_4_Xcoordinate and
    floor.Vertex_1_Ycoordinate == ceiling.Vertex_4_Ycoordinate and
    floor.Vertex_2_Xcoordinate == ceiling.Vertex_3_Xcoordinate and
    floor.Vertex_2_Ycoordinate == ceiling.Vertex_3_Ycoordinate
)

if is_match:
    print(f"\n✅ Floor vertices are REVERSED from Ceiling - CORRECT!")
else:
    print(f"\n❌ Floor/Ceiling vertices DO NOT MATCH!")

# Test simulation
from features.simulation.runner import EnergyPlusRunner

print("\n" + "=" * 80)
print("TESTING SIMULATION...")
print("=" * 80)

runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=output_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=Path("output/test_step4_sim"),
    output_prefix="step4"
)

print(f"\n{'='*80}")
print(f"STEP 4 RESULT: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
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
        print(f"\n🎉🎉🎉 STEP 4 PASSED! 2-Zones VERTICAL works! 🎉🎉🎉")
        print(f"\n🔥 BREAKTHROUGH: Floor/Ceiling matching funktioniert! 🔥")
    else:
        print(f"\n❌ STEP 4 FAILED")
else:
    print("\n❌ No SQL file - simulation crashed")

# Check for errors
err_file = Path("output/test_step4_sim/step4out.err")
if err_file.exists() and err_file.stat().st_size > 0:
    print(f"\nError file ({err_file.stat().st_size} bytes):")
    with open(err_file, 'r') as f:
        content = f.read()
        if "upside down" in content.lower():
            print("  ⚠️ Contains 'upside down' warnings!")
        if "volume" in content.lower() and "negative" in content.lower():
            print("  ⚠️ Contains negative volume warnings!")
        # Show severe errors
        for line in content.split('\n'):
            if 'severe' in line.lower() or 'fatal' in line.lower():
                print(f"  {line}")

print("=" * 80)
