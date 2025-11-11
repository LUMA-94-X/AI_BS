#!/usr/bin/env python3
"""Create minimal test IDF to isolate the crash."""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eppy.modeleditor import IDF

# Set IDD
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

print("=" * 80)
print("CREATING MINIMAL TEST IDF")
print("=" * 80)

# Create minimal IDF content
minimal_content = """
VERSION,
    25.1;

BUILDING,
    Minimal Test Building,
    0,
    Suburbs,
    0.04,
    0.4,
    FullInteriorAndExterior,
    25,
    6;

TIMESTEP,
    4;

SIMULATIONCONTROL,
    No,
    No,
    No,
    No,
    Yes;

SITE:LOCATION,
    Test Location,
    48.0,
    11.0,
    1.0,
    500.0;

RUNPERIOD,
    Annual,
    1,
    1,
    2024,
    12,
    31,
    2024,
    Monday,
    Yes,
    Yes,
    No,
    Yes,
    1;

GLOBALGEOMETRYRULES,
    UpperLeftCorner,
    CounterClockWise,
    Relative,
    Relative,
    Relative;

MATERIAL,
    Concrete,
    MediumRough,
    0.20,
    1.95,
    2240,
    900;

CONSTRUCTION,
    SimpleConstruction,
    Concrete;

SCHEDULE:CONSTANT,
    AlwaysOn,
    ,
    1.0;

SCHEDULE:CONSTANT,
    HeatingSetpoint,
    ,
    20.0;

SCHEDULE:CONSTANT,
    CoolingSetpoint,
    ,
    26.0;

ZONE,
    TestZone,
    0,
    0,
    0,
    0,
    1,
    1,
    autocalculate,
    autocalculate;

BUILDINGSURFACE:DETAILED,
    Zone_Floor,
    Floor,
    SimpleConstruction,
    TestZone,
    ,
    Ground,
    ,
    NoSun,
    NoWind,
    autocalculate,
    4,
    0, 0, 0,
    10, 0, 0,
    10, 10, 0,
    0, 10, 0;

BUILDINGSURFACE:DETAILED,
    Zone_Ceiling,
    Roof,
    SimpleConstruction,
    TestZone,
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    autocalculate,
    4,
    0, 0, 3,
    0, 10, 3,
    10, 10, 3,
    10, 0, 3;

BUILDINGSURFACE:DETAILED,
    Zone_Wall_North,
    Wall,
    SimpleConstruction,
    TestZone,
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    autocalculate,
    4,
    0, 10, 0,
    10, 10, 0,
    10, 10, 3,
    0, 10, 3;

BUILDINGSURFACE:DETAILED,
    Zone_Wall_East,
    Wall,
    SimpleConstruction,
    TestZone,
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    autocalculate,
    4,
    10, 0, 0,
    10, 10, 0,
    10, 10, 3,
    10, 0, 3;

BUILDINGSURFACE:DETAILED,
    Zone_Wall_South,
    Wall,
    SimpleConstruction,
    TestZone,
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    autocalculate,
    4,
    10, 0, 0,
    0, 0, 0,
    0, 0, 3,
    10, 0, 3;

BUILDINGSURFACE:DETAILED,
    Zone_Wall_West,
    Wall,
    SimpleConstruction,
    TestZone,
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    autocalculate,
    4,
    0, 0, 0,
    0, 10, 0,
    0, 10, 3,
    0, 0, 3;

ZONEHVAC:IDEALLOADSAIRSYSTEM,
    TestZone_IdealLoads,
    TestZone_Supply_Node,
    ,
    ,
    50.0,
    13.0,
    0.015,
    0.010,
    NoLimit,
    ,
    ,
    NoLimit,
    ,
    ,
    AlwaysOn,
    AlwaysOn,
    None,
    ,
    None,
    ,
    None,
    NoEconomizer,
    None,
    0.70,
    0.65;

ZONEHVAC:EQUIPMENTLIST,
    TestZone_Equipment_List,
    SequentialLoad,
    ZoneHVAC:IdealLoadsAirSystem,
    TestZone_IdealLoads,
    1,
    1,
    ,
    ;

ZONEHVAC:EQUIPMENTCONNECTIONS,
    TestZone,
    TestZone_Equipment_List,
    TestZone_Supply_Node,
    ,
    TestZone_Air_Node,
    TestZone_Return_Node;

ZONECONTROL:THERMOSTAT,
    TestZone_Thermostat,
    TestZone,
    AlwaysOn,
    ThermostatSetpoint:DualSetpoint,
    TestZone_DualSetpoint;

THERMOSTATSETPOINT:DUALSETPOINT,
    TestZone_DualSetpoint,
    HeatingSetpoint,
    CoolingSetpoint;

OUTPUT:VARIABLE,
    *,
    Zone Mean Air Temperature,
    Hourly;

OUTPUT:SQLITE,
    SimpleAndTabular;
"""

# Write to file
output_path = Path("output/minimal_test.idf")
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, 'w') as f:
    f.write(minimal_content)

print(f"✅ Created minimal IDF: {output_path}")
print(f"   File size: {output_path.stat().st_size:,} bytes")

# Now test simulation
weather_file = Path("/mnt/c/Users/lugma/source/repos/AI_BS/data/weather/example.epw")
sim_output_dir = Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/test_minimal_sim")
sim_output_dir.mkdir(parents=True, exist_ok=True)

# Convert paths
result_idf = subprocess.run(['wslpath', '-w', str(output_path.absolute())],
                           capture_output=True, text=True)
result_weather = subprocess.run(['wslpath', '-w', str(weather_file.absolute())],
                               capture_output=True, text=True)
result_output = subprocess.run(['wslpath', '-w', str(sim_output_dir.absolute())],
                              capture_output=True, text=True)

print("\n" + "=" * 80)
print("TESTING SIMULATION...")
print("=" * 80)

cmd = [
    "/mnt/c/EnergyPlusV25-1-0/energyplus.exe",
    "--weather", result_weather.stdout.strip(),
    "--output-directory", result_output.stdout.strip(),
    "--output-prefix", "min",
    result_idf.stdout.strip()
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(sim_output_dir.absolute()))

print(f"Return Code: {result.returncode}")
print(f"\nSTDOUT:\n{result.stdout}")

if result.returncode == 0:
    print("\n✅ SUCCESS: Minimal IDF works!")
else:
    print(f"\n❌ FAILED: Return code {result.returncode}")
    print(f"STDERR:\n{result.stderr}")
