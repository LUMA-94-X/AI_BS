#!/usr/bin/env python3
"""Test HVAC implementation based on EnergyPlus example."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eppy.modeleditor import IDF
from features.hvac.ideal_loads import HVACTemplateManager

# Use existing IDF
idf_path = Path("output/simulation_20251111_233258/building.idf")

if not idf_path.exists():
    print(f"❌ IDF not found: {idf_path}")
    sys.exit(1)

print("=" * 80)
print("EXAMPLE-BASED HVAC TEST")
print("=" * 80)
print("Using syntax from: 5Zone_IdealLoadsAirSystems_ReturnPlenum.idf")
print("=" * 80)

# Load IDF
print(f"\nLoading IDF: {idf_path}")

# Set IDD
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

idf = IDF(str(idf_path))

# Count existing objects BEFORE
zones_before = len(idf.idfobjects.get('ZONE', []))
hvac_before = len(idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', []))
thermostats_before = len(idf.idfobjects.get('ZONECONTROL:THERMOSTAT', []))

print(f"\nBEFORE applying HVAC:")
print(f"  Zones: {zones_before}")
print(f"  Direct HVAC: {hvac_before}")
print(f"  Thermostats: {thermostats_before}")

# Remove existing HVAC
print(f"\nRemoving existing HVAC objects...")
for obj_type in ['ZONEHVAC:IDEALLOADSAIRSYSTEM', 'ZONEHVAC:EQUIPMENTLIST',
                 'ZONEHVAC:EQUIPMENTCONNECTIONS', 'ZONECONTROL:THERMOSTAT',
                 'THERMOSTATSETPOINT:DUALSETPOINT', 'HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM']:
    objects = idf.idfobjects.get(obj_type, [])
    for obj in list(objects):
        idf.removeidfobject(obj)

print("  ✓ Removed all HVAC objects")

# Apply HVAC with example-based code
print(f"\nApplying HVAC with example-based implementation...")
manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Count objects AFTER
zones_after = len(idf.idfobjects.get('ZONE', []))
hvac_after = len(idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', []))
thermostats_after = len(idf.idfobjects.get('ZONECONTROL:THERMOSTAT', []))
setpoints_after = len(idf.idfobjects.get('THERMOSTATSETPOINT:DUALSETPOINT', []))
equiplist_after = len(idf.idfobjects.get('ZONEHVAC:EQUIPMENTLIST', []))
equipconn_after = len(idf.idfobjects.get('ZONEHVAC:EQUIPMENTCONNECTIONS', []))

print(f"\nAFTER applying HVAC:")
print(f"  Zones: {zones_after}")
print(f"  ZONEHVAC:IDEALLOADSAIRSYSTEM: {hvac_after} {'✓' if hvac_after == zones_after else '❌'}")
print(f"  ZONEHVAC:EQUIPMENTLIST: {equiplist_after} {'✓' if equiplist_after == zones_after else '❌'}")
print(f"  ZONEHVAC:EQUIPMENTCONNECTIONS: {equipconn_after} {'✓' if equipconn_after == zones_after else '❌'}")
print(f"  ZONECONTROL:THERMOSTAT: {thermostats_after} {'✓' if thermostats_after == zones_after else '❌'}")
print(f"  THERMOSTATSETPOINT:DUALSETPOINT: {setpoints_after} (shared: should be 1) {'✓' if setpoints_after == 1 else '❌'}")

# Verify schedules
heating_sch = idf.idfobjects.get('SCHEDULE:CONSTANT', [])
heating_names = [sch.Name for sch in heating_sch]

print(f"\nSchedules:")
print(f"  HeatingSetpoint: {'✓' if 'HeatingSetpoint' in heating_names else '❌'}")
print(f"  CoolingSetpoint: {'✓' if 'CoolingSetpoint' in heating_names else '❌'}")
print(f"  AlwaysOn: {'✓' if 'AlwaysOn' in heating_names else '❌'}")

# Check AlwaysOn value
for sch in heating_sch:
    if sch.Name == "AlwaysOn":
        print(f"  AlwaysOn value: {sch.Hourly_Value} {'✓' if float(sch.Hourly_Value) == 4.0 else '❌ (should be 4.0)'}")

# Validate
print("\n" + "=" * 80)
if (hvac_after == zones_after and
    equiplist_after == zones_after and
    equipconn_after == zones_after and
    thermostats_after == zones_after and
    setpoints_after == 1):
    print("✅ TEST PASSED: All HVAC objects created correctly!")
    print(f"   - {hvac_after} ZONEHVAC:IDEALLOADSAIRSYSTEM objects")
    print(f"   - {equiplist_after} Equipment Lists")
    print(f"   - {equipconn_after} Equipment Connections")
    print(f"   - {thermostats_after} Thermostats")
    print(f"   - {setpoints_after} Shared DualSetpoint")

    # Save fixed IDF
    output_path = Path("output/building_example_based.idf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    idf.save(str(output_path))
    print(f"\n✅ Saved IDF to: {output_path}")

    # Check one HVAC object for correct syntax
    print("\n" + "=" * 80)
    print("CHECKING SYNTAX (first HVAC object):")
    print("=" * 80)
    first_hvac = idf.idfobjects['ZONEHVAC:IDEALLOADSAIRSYSTEM'][0]
    print(f"  Name: {first_hvac.Name}")
    print(f"  Maximum_Heating_Air_Flow_Rate: {first_hvac.Maximum_Heating_Air_Flow_Rate}")
    print(f"  Maximum_Cooling_Air_Flow_Rate: {first_hvac.Maximum_Cooling_Air_Flow_Rate}")
    print(f"  Dehumidification_Control_Type: {first_hvac.Dehumidification_Control_Type}")
    print(f"  Humidification_Control_Type: {first_hvac.Humidification_Control_Type}")

    if (first_hvac.Maximum_Heating_Air_Flow_Rate == "autosize" and
        first_hvac.Dehumidification_Control_Type == "ConstantSupplyHumidityRatio"):
        print("\n✅ Syntax matches EnergyPlus example!")
    else:
        print("\n⚠️  Syntax differs from example - may cause issues")

    print("\n" + "=" * 80)
    print("Next step: Test simulation")
    print("  python3 test_simulation_example_based.py")
    print("=" * 80)

    sys.exit(0)
else:
    print("❌ TEST FAILED!")
    if hvac_after != zones_after:
        print(f"   ❌ Expected {zones_after} HVAC objects, got {hvac_after}")
    if equiplist_after != zones_after:
        print(f"   ❌ Expected {zones_after} equipment lists, got {equiplist_after}")
    if equipconn_after != zones_after:
        print(f"   ❌ Expected {zones_after} equipment connections, got {equipconn_after}")
    if thermostats_after != zones_after:
        print(f"   ❌ Expected {zones_after} thermostats, got {thermostats_after}")
    if setpoints_after != 1:
        print(f"   ❌ Expected 1 shared setpoint, got {setpoints_after}")
    sys.exit(1)
