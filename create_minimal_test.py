#!/usr/bin/env python3
"""Create minimal 1-zone test IDF."""
import tempfile
from pathlib import Path
from eppy.modeleditor import IDF

# Set IDD
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

# Create minimal IDF
minimal_content = "VERSION,\n  25.1;\n"
with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False) as f:
    f.write(minimal_content)
    temp_path = f.name

idf = IDF(temp_path)
Path(temp_path).unlink()

print("Creating MINIMAL 1-zone test IDF...")

# GlobalGeometryRules (FIRST!)
idf.newidfobject(
    "GLOBALGEOMETRYRULES",
    Starting_Vertex_Position="UpperLeftCorner",
    Vertex_Entry_Direction="Counterclockwise",
    Coordinate_System="Relative",
)

# Simulation Control
idf.newidfobject(
    "SIMULATIONCONTROL",
    Do_Zone_Sizing_Calculation="No",
    Do_System_Sizing_Calculation="No",
    Do_Plant_Sizing_Calculation="No",
    Run_Simulation_for_Sizing_Periods="No",
    Run_Simulation_for_Weather_File_Run_Periods="Yes",
)

# Building
idf.newidfobject(
    "BUILDING",
    Name="Minimal_Test",
    North_Axis=0.0,
    Terrain="Suburbs",
    Loads_Convergence_Tolerance_Value=0.04,
    Temperature_Convergence_Tolerance_Value=0.4,
    Solar_Distribution="FullExterior",
)

# HeatBalanceAlgorithm
idf.newidfobject(
    "HEATBALANCEALGORITHM",
    Algorithm="ConductionTransferFunction",
)

# Timestep
idf.newidfobject("TIMESTEP", Number_of_Timesteps_per_Hour=4)

# RunPeriod
idf.newidfobject(
    "RUNPERIOD",
    Name="Annual",
    Begin_Month=1,
    Begin_Day_of_Month=1,
    End_Month=12,
    End_Day_of_Month=31,
    Day_of_Week_for_Start_Day="Monday",
    Use_Weather_File_Holidays_and_Special_Days="Yes",
    Use_Weather_File_Daylight_Saving_Period="Yes",
)

# Site:Location
idf.newidfobject(
    "SITE:LOCATION",
    Name="Test_Location",
    Latitude=52.5,
    Longitude=13.4,
    Time_Zone=1.0,
    Elevation=50.0,
)

# Material
idf.newidfobject(
    "MATERIAL",
    Name="TestMaterial",
    Roughness="Rough",
    Thickness=0.2,
    Conductivity=1.0,
    Density=1000.0,
    Specific_Heat=1000.0,
)

# Construction
idf.newidfobject(
    "CONSTRUCTION",
    Name="TestConstruction",
    Outside_Layer="TestMaterial",
)

# Zone
idf.newidfobject(
    "ZONE",
    Name="TestZone",
    Direction_of_Relative_North=0.0,
    X_Origin=0.0,
    Y_Origin=0.0,
    Z_Origin=0.0,
    Type=1,
)

# Simple 10x10x3m box
# Floor
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="TestZone_Floor",
    Surface_Type="Floor",
    Construction_Name="TestConstruction",
    Zone_Name="TestZone",
    Outside_Boundary_Condition="Ground",
    Outside_Boundary_Condition_Object="",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0.0,
    Vertex_1_Ycoordinate=0.0,
    Vertex_1_Zcoordinate=0.0,
    Vertex_2_Xcoordinate=10.0,
    Vertex_2_Ycoordinate=0.0,
    Vertex_2_Zcoordinate=0.0,
    Vertex_3_Xcoordinate=10.0,
    Vertex_3_Ycoordinate=10.0,
    Vertex_3_Zcoordinate=0.0,
    Vertex_4_Xcoordinate=0.0,
    Vertex_4_Ycoordinate=10.0,
    Vertex_4_Zcoordinate=0.0,
)

# Roof
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="TestZone_Roof",
    Surface_Type="Roof",
    Construction_Name="TestConstruction",
    Zone_Name="TestZone",
    Outside_Boundary_Condition="Outdoors",
    Outside_Boundary_Condition_Object="",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0.0,
    Vertex_1_Ycoordinate=10.0,
    Vertex_1_Zcoordinate=3.0,
    Vertex_2_Xcoordinate=10.0,
    Vertex_2_Ycoordinate=10.0,
    Vertex_2_Zcoordinate=3.0,
    Vertex_3_Xcoordinate=10.0,
    Vertex_3_Ycoordinate=0.0,
    Vertex_3_Zcoordinate=3.0,
    Vertex_4_Xcoordinate=0.0,
    Vertex_4_Ycoordinate=0.0,
    Vertex_4_Zcoordinate=3.0,
)

# 4 Walls
# North Wall
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="TestZone_Wall_North",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="TestZone",
    Outside_Boundary_Condition="Outdoors",
    Outside_Boundary_Condition_Object="",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0.0,
    Vertex_1_Ycoordinate=10.0,
    Vertex_1_Zcoordinate=0.0,
    Vertex_2_Xcoordinate=10.0,
    Vertex_2_Ycoordinate=10.0,
    Vertex_2_Zcoordinate=0.0,
    Vertex_3_Xcoordinate=10.0,
    Vertex_3_Ycoordinate=10.0,
    Vertex_3_Zcoordinate=3.0,
    Vertex_4_Xcoordinate=0.0,
    Vertex_4_Ycoordinate=10.0,
    Vertex_4_Zcoordinate=3.0,
)

# East Wall
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="TestZone_Wall_East",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="TestZone",
    Outside_Boundary_Condition="Outdoors",
    Outside_Boundary_Condition_Object="",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=10.0,
    Vertex_1_Ycoordinate=10.0,
    Vertex_1_Zcoordinate=0.0,
    Vertex_2_Xcoordinate=10.0,
    Vertex_2_Ycoordinate=0.0,
    Vertex_2_Zcoordinate=0.0,
    Vertex_3_Xcoordinate=10.0,
    Vertex_3_Ycoordinate=0.0,
    Vertex_3_Zcoordinate=3.0,
    Vertex_4_Xcoordinate=10.0,
    Vertex_4_Ycoordinate=10.0,
    Vertex_4_Zcoordinate=3.0,
)

# South Wall
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="TestZone_Wall_South",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="TestZone",
    Outside_Boundary_Condition="Outdoors",
    Outside_Boundary_Condition_Object="",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=10.0,
    Vertex_1_Ycoordinate=0.0,
    Vertex_1_Zcoordinate=0.0,
    Vertex_2_Xcoordinate=0.0,
    Vertex_2_Ycoordinate=0.0,
    Vertex_2_Zcoordinate=0.0,
    Vertex_3_Xcoordinate=0.0,
    Vertex_3_Ycoordinate=0.0,
    Vertex_3_Zcoordinate=3.0,
    Vertex_4_Xcoordinate=10.0,
    Vertex_4_Ycoordinate=0.0,
    Vertex_4_Zcoordinate=3.0,
)

# West Wall
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="TestZone_Wall_West",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="TestZone",
    Outside_Boundary_Condition="Outdoors",
    Outside_Boundary_Condition_Object="",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0.0,
    Vertex_1_Ycoordinate=0.0,
    Vertex_1_Zcoordinate=0.0,
    Vertex_2_Xcoordinate=0.0,
    Vertex_2_Ycoordinate=10.0,
    Vertex_2_Zcoordinate=0.0,
    Vertex_3_Xcoordinate=0.0,
    Vertex_3_Ycoordinate=10.0,
    Vertex_3_Zcoordinate=3.0,
    Vertex_4_Xcoordinate=0.0,
    Vertex_4_Ycoordinate=0.0,
    Vertex_4_Zcoordinate=3.0,
)

# Apply HVAC (from our working implementation)
from features.hvac.ideal_loads import HVACTemplateManager

manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Save
output_path = Path("output/minimal_test.idf")
idf.save(str(output_path))

print(f"✅ Created: {output_path}")
print(f"   1 Zone, 6 Surfaces, IdealLoads HVAC")
