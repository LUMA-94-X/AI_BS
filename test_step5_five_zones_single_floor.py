#!/usr/bin/env python3
"""Step 5: Five zones on a single floor (Perimeter + Core).

Layout (Top view, Z=0-3m):
    0          5         10        15         20
0   +---------+---------+---------+---------+
    |         |         |         |         |
    |  North  |  North  |  North  |  North  |
    |    W    |         |         |    E    |
5   +---------+---------+---------+---------+
    |         |         |         |         |
    | West    |  CORE   |  CORE   |  East   |
    |         |         |         |         |
10  +---------+---------+---------+---------+
    |         |         |         |         |
    |  South  |  South  |  South  |  South  |
    |    W    |         |         |    E    |
15  +---------+---------+---------+---------+

5 Zones:
- Perimeter_North: (0,10,0) to (20,15,3)
- Perimeter_East:  (15,0,0) to (20,10,3)
- Perimeter_South: (0,0,0) to (20,5,3)
- Perimeter_West:  (0,5,0) to (5,15,3)
- Core:            (5,5,0) to (15,10,3)
"""
import tempfile
from pathlib import Path
from eppy.modeleditor import IDF

# Setup
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

# Create minimal IDF to initialize
minimal_content = "VERSION,\n  25.1;\n"
with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False) as f:
    f.write(minimal_content)
    temp_path = f.name

idf = IDF(temp_path)
Path(temp_path).unlink()

print("=" * 80)
print("STEP 5: FIVE ZONES ON SINGLE FLOOR (Perimeter + Core)")
print("=" * 80)

# GLOBALGEOMETRYRULES - Must be early
idf.newidfobject(
    "GLOBALGEOMETRYRULES",
    Starting_Vertex_Position="UpperLeftCorner",
    Vertex_Entry_Direction="Counterclockwise",
    Coordinate_System="Relative",
    Daylighting_Reference_Point_Coordinate_System="Relative",
    Rectangular_Surface_Coordinate_System="Relative",
)

# SIMULATIONCONTROL
idf.newidfobject(
    "SIMULATIONCONTROL",
    Do_Zone_Sizing_Calculation="No",
    Do_System_Sizing_Calculation="No",
    Do_Plant_Sizing_Calculation="No",
    Run_Simulation_for_Sizing_Periods="No",
    Run_Simulation_for_Weather_File_Run_Periods="Yes",
    Do_HVAC_Sizing_Simulation_for_Sizing_Periods="No",
    Maximum_Number_of_HVAC_Sizing_Simulation_Passes=1,
)

# BUILDING
idf.newidfobject(
    "BUILDING",
    Name="FiveZone_Test",
    North_Axis=0,
    Terrain="Suburbs",
    Loads_Convergence_Tolerance_Value=0.04,
    Temperature_Convergence_Tolerance_Value=0.4,
    Solar_Distribution="FullExterior",
    Maximum_Number_of_Warmup_Days=25,
    Minimum_Number_of_Warmup_Days=1,
)

# Surface algorithms
idf.newidfobject("SURFACECONVECTIONALGORITHM:INSIDE", Algorithm="Simple")
idf.newidfobject("SURFACECONVECTIONALGORITHM:OUTSIDE", Algorithm="SimpleCombined")
idf.newidfobject(
    "HEATBALANCEALGORITHM",
    Algorithm="ConductionTransferFunction",
    Surface_Temperature_Upper_Limit=200,
    Minimum_Surface_Convection_Heat_Transfer_Coefficient_Value=0.1,
    Maximum_Surface_Convection_Heat_Transfer_Coefficient_Value=1000,
)

# TIMESTEP
idf.newidfobject("TIMESTEP", Number_of_Timesteps_per_Hour=4)

# SITE:LOCATION
idf.newidfobject(
    "SITE:LOCATION",
    Name="Test_Location",
    Latitude=52.5,
    Longitude=13.4,
    Time_Zone=1,
    Elevation=50,
    Keep_Site_Location_Information="No",
)

# RUNPERIOD (full year)
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
    Apply_Weekend_Holiday_Rule="No",
    Use_Weather_File_Rain_Indicators="Yes",
    Use_Weather_File_Snow_Indicators="Yes",
    Treat_Weather_as_Actual="No",
    First_Hour_Interpolation_Starting_Values="Hour24",
)

# MATERIAL
idf.newidfobject(
    "MATERIAL",
    Name="TestMaterial",
    Roughness="Rough",
    Thickness=0.2,
    Conductivity=1.0,
    Density=1000,
    Specific_Heat=1000,
    Thermal_Absorptance=0.9,
    Solar_Absorptance=0.7,
    Visible_Absorptance=0.7,
)

# CONSTRUCTION
idf.newidfobject(
    "CONSTRUCTION",
    Name="TestConstruction",
    Outside_Layer="TestMaterial",
)

# Define 5 zones
zones = [
    {"name": "Perimeter_North", "x0": 0, "y0": 10, "x1": 20, "y1": 15},
    {"name": "Perimeter_East", "x0": 15, "y0": 0, "x1": 20, "y1": 10},
    {"name": "Perimeter_South", "x0": 0, "y0": 0, "x1": 20, "y1": 5},
    {"name": "Perimeter_West", "x0": 0, "y0": 5, "x1": 5, "y1": 15},
    {"name": "Core", "x0": 5, "y0": 5, "x1": 15, "y1": 10},
]

z_floor = 0.0
z_ceiling = 3.0

for zone in zones:
    name = zone["name"]
    x0, y0, x1, y1 = zone["x0"], zone["y0"], zone["x1"], zone["y1"]

    # ZONE
    idf.newidfobject(
        "ZONE",
        Name=name,
        Direction_of_Relative_North=0,
        X_Origin=0,
        Y_Origin=0,
        Z_Origin=0,
        Type=1,
        Multiplier=1,
        Ceiling_Height="autocalculate",
        Volume="autocalculate",
        Floor_Area="autocalculate",
        Part_of_Total_Floor_Area="Yes",
    )

    # FLOOR (Ground)
    idf.newidfobject(
        "BUILDINGSURFACE:DETAILED",
        Name=f"{name}_Floor",
        Surface_Type="Floor",
        Construction_Name="TestConstruction",
        Zone_Name=name,
        Outside_Boundary_Condition="Ground",
        Sun_Exposure="NoSun",
        Wind_Exposure="NoWind",
        View_Factor_to_Ground="autocalculate",
        Number_of_Vertices=4,
        # Floor vertices: [3,2,1,0] reversed
        Vertex_1_Xcoordinate=x0, Vertex_1_Ycoordinate=y1, Vertex_1_Zcoordinate=z_floor,
        Vertex_2_Xcoordinate=x1, Vertex_2_Ycoordinate=y1, Vertex_2_Zcoordinate=z_floor,
        Vertex_3_Xcoordinate=x1, Vertex_3_Ycoordinate=y0, Vertex_3_Zcoordinate=z_floor,
        Vertex_4_Xcoordinate=x0, Vertex_4_Ycoordinate=y0, Vertex_4_Zcoordinate=z_floor,
    )

    # CEILING (Roof)
    idf.newidfobject(
        "BUILDINGSURFACE:DETAILED",
        Name=f"{name}_Ceiling",
        Surface_Type="Roof",
        Construction_Name="TestConstruction",
        Zone_Name=name,
        Outside_Boundary_Condition="Outdoors",
        Sun_Exposure="SunExposed",
        Wind_Exposure="WindExposed",
        View_Factor_to_Ground="autocalculate",
        Number_of_Vertices=4,
        # Ceiling vertices: [0,1,2,3] normal up
        Vertex_1_Xcoordinate=x0, Vertex_1_Ycoordinate=y0, Vertex_1_Zcoordinate=z_ceiling,
        Vertex_2_Xcoordinate=x1, Vertex_2_Ycoordinate=y0, Vertex_2_Zcoordinate=z_ceiling,
        Vertex_3_Xcoordinate=x1, Vertex_3_Ycoordinate=y1, Vertex_3_Zcoordinate=z_ceiling,
        Vertex_4_Xcoordinate=x0, Vertex_4_Ycoordinate=y1, Vertex_4_Zcoordinate=z_ceiling,
    )

# Add walls for each zone
# Perimeter_North: North (exterior), South (to Core), East (exterior), West (exterior)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_North_Wall_North",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_North",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0, Vertex_1_Ycoordinate=15, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=20, Vertex_2_Ycoordinate=15, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=20, Vertex_3_Ycoordinate=15, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0, Vertex_4_Ycoordinate=15, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_North_Wall_ToCore",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_North",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Core_Wall_ToNorth",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=5, Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=15, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=15, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=5, Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_North_Wall_East",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_North",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=20, Vertex_1_Ycoordinate=15, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=20, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=20, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=20, Vertex_4_Ycoordinate=15, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_North_Wall_West",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_North",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0, Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=0, Vertex_2_Ycoordinate=15, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=0, Vertex_3_Ycoordinate=15, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0, Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

# Perimeter_East: East (exterior), West (to Core), North (exterior), South (exterior)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_East_Wall_East",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_East",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=20, Vertex_1_Ycoordinate=0, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=20, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=20, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=20, Vertex_4_Ycoordinate=0, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_East_Wall_ToCore",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_East",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Core_Wall_ToEast",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=15, Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=15, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=15, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=15, Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_East_Wall_North",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_East",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=20, Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=15, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=15, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=20, Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_East_Wall_South",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_East",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=15, Vertex_1_Ycoordinate=0, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=20, Vertex_2_Ycoordinate=0, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=20, Vertex_3_Ycoordinate=0, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=15, Vertex_4_Ycoordinate=0, Vertex_4_Zcoordinate=3,
)

# Perimeter_South: South (exterior), North (to Core), East (exterior), West (exterior)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_South_Wall_South",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_South",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=20, Vertex_1_Ycoordinate=0, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=0, Vertex_2_Ycoordinate=0, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=0, Vertex_3_Ycoordinate=0, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=20, Vertex_4_Ycoordinate=0, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_South_Wall_ToCore",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_South",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Core_Wall_ToSouth",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=15, Vertex_1_Ycoordinate=5, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=5, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=5, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=15, Vertex_4_Ycoordinate=5, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_South_Wall_East",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_South",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=20, Vertex_1_Ycoordinate=5, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=20, Vertex_2_Ycoordinate=0, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=20, Vertex_3_Ycoordinate=0, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=20, Vertex_4_Ycoordinate=5, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_South_Wall_West",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_South",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0, Vertex_1_Ycoordinate=0, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=0, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=0, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0, Vertex_4_Ycoordinate=0, Vertex_4_Zcoordinate=3,
)

# Perimeter_West: West (exterior), East (to Core), North (exterior), South (exterior)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_West_Wall_West",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_West",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0, Vertex_1_Ycoordinate=15, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=0, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=0, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0, Vertex_4_Ycoordinate=15, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_West_Wall_ToCore",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_West",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Core_Wall_ToWest",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=5, Vertex_1_Ycoordinate=5, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=5, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=5, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=5, Vertex_4_Ycoordinate=5, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_West_Wall_North",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_West",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=5, Vertex_1_Ycoordinate=15, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=0, Vertex_2_Ycoordinate=15, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=0, Vertex_3_Ycoordinate=15, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=5, Vertex_4_Ycoordinate=15, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Perimeter_West_Wall_South",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Perimeter_West",
    Outside_Boundary_Condition="Outdoors",
    Sun_Exposure="SunExposed",
    Wind_Exposure="WindExposed",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0, Vertex_1_Ycoordinate=5, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=5, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=5, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0, Vertex_4_Ycoordinate=5, Vertex_4_Zcoordinate=3,
)

# Core: 4 walls to perimeter zones (no exterior walls)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Core_Wall_ToNorth",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Core",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Perimeter_North_Wall_ToCore",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    # REVERSED from Perimeter_North_Wall_ToCore
    Vertex_1_Xcoordinate=15, Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=5, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=5, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=15, Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Core_Wall_ToEast",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Core",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Perimeter_East_Wall_ToCore",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    # REVERSED from Perimeter_East_Wall_ToCore
    Vertex_1_Xcoordinate=15, Vertex_1_Ycoordinate=5, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=15, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=15, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=15, Vertex_4_Ycoordinate=5, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Core_Wall_ToSouth",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Core",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Perimeter_South_Wall_ToCore",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    # REVERSED from Perimeter_South_Wall_ToCore
    Vertex_1_Xcoordinate=5, Vertex_1_Ycoordinate=5, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=15, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=15, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=5, Vertex_4_Ycoordinate=5, Vertex_4_Zcoordinate=3,
)

idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Core_Wall_ToWest",
    Surface_Type="Wall",
    Construction_Name="TestConstruction",
    Zone_Name="Core",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Perimeter_West_Wall_ToCore",
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    View_Factor_to_Ground="autocalculate",
    Number_of_Vertices=4,
    # REVERSED from Perimeter_West_Wall_ToCore
    Vertex_1_Xcoordinate=5, Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=0,
    Vertex_2_Xcoordinate=5, Vertex_2_Ycoordinate=5, Vertex_2_Zcoordinate=0,
    Vertex_3_Xcoordinate=5, Vertex_3_Ycoordinate=5, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=5, Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

# Save IDF
output_path = Path("output/test_step5_five_zones.idf")
idf.save(str(output_path))

print(f"\n✅ Created: {output_path}")
print(f"   5 Zones (1 Floor), 30 Surfaces (10 Floor+Ceiling, 20 Walls), IdealLoads HVAC")

# Apply HVAC
from features.hvac.ideal_loads import HVACTemplateManager

manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Save again after HVAC
idf.save(str(output_path))

# Add OUTPUT objects
idf.newidfobject("OUTPUTCONTROL:TABLE:STYLE", Column_Separator="HTML", Unit_Conversion="None")
idf.newidfobject(
    "OUTPUT:SQLITE",
    Option_Type="SimpleAndTabular",
    Unit_Conversion_for_Tabular_Data="UseOutputControlTableStyle",
)
idf.newidfobject(
    "OUTPUT:VARIABLE",
    Key_Value="*",
    Variable_Name="Zone Mean Air Temperature",
    Reporting_Frequency="Hourly",
)

# Save final (OUTPUT:DIAGNOSTICS already added by HVAC template)
idf.save(str(output_path))

# Test simulation
from features.simulation.runner import EnergyPlusRunner

print("\n" + "=" * 80)
print("TESTING SIMULATION...")
print("=" * 80)

runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=output_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=Path("output/test_step5_sim"),
    output_prefix="step5",
)

print(f"\n{'=' * 80}")
print(f"STEP 5 RESULT: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
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
        print(f"\n🎉🎉🎉 STEP 5 PASSED! 5-Zones on single floor works! 🎉🎉🎉")
    else:
        print(f"\n❌ STEP 5 FAILED")

    # Check errors
    err_file = Path("output/test_step5_sim/step5out.err")
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

    # Show stderr if available
    if hasattr(result, 'stderr') and result.stderr:
        print(f"\nEnergyPlus stderr:\n{result.stderr[:1000]}")

    # Check error file
    err_file = Path("output/test_step5_sim/step5out.err")
    if err_file.exists() and err_file.stat().st_size > 0:
        print(f"\nError file content:")
        with open(err_file, 'r') as f:
            print(f.read()[-2000:])

print("=" * 80)
