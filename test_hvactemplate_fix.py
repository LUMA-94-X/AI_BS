#!/usr/bin/env python3
"""Test HVACTEMPLATE fix - use template objects instead of direct HVAC objects."""

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
print("HVACTEMPLATE FIX TEST")
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
template_before = len(idf.idfobjects.get('HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM', []))
thermostats_before = len(idf.idfobjects.get('ZONECONTROL:THERMOSTAT', []))

print(f"\nBEFORE applying HVAC:")
print(f"  Zones: {zones_before}")
print(f"  Direct HVAC: {hvac_before}")
print(f"  HVACTEMPLATE: {template_before}")
print(f"  Thermostats: {thermostats_before}")

# Remove existing HVAC (to test clean application)
print(f"\nRemoving existing HVAC objects...")
for obj_type in ['ZONEHVAC:IDEALLOADSAIRSYSTEM', 'ZONEHVAC:EQUIPMENTLIST',
                 'ZONEHVAC:EQUIPMENTCONNECTIONS', 'ZONECONTROL:THERMOSTAT',
                 'THERMOSTATSETPOINT:DUALSETPOINT', 'HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM']:
    objects = idf.idfobjects.get(obj_type, [])
    for obj in list(objects):
        idf.removeidfobject(obj)

print("  ✓ Removed all HVAC objects")

# Apply HVAC with new HVACTEMPLATE code
print(f"\nApplying HVAC with HVACTEMPLATE fix...")
manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Count objects AFTER
zones_after = len(idf.idfobjects.get('ZONE', []))
hvac_after = len(idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', []))
template_after = len(idf.idfobjects.get('HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM', []))
thermostats_after = len(idf.idfobjects.get('ZONECONTROL:THERMOSTAT', []))
setpoints_after = len(idf.idfobjects.get('THERMOSTATSETPOINT:DUALSETPOINT', []))

print(f"\nAFTER applying HVAC:")
print(f"  Zones: {zones_after}")
print(f"  Direct HVAC: {hvac_after} (should be 0 - using templates)")
print(f"  HVACTEMPLATE: {template_after} {'✓' if template_after == zones_after else '❌'}")
print(f"  Thermostats: {thermostats_after} {'✓' if thermostats_after == zones_after else '❌'}")
print(f"  Setpoints: {setpoints_after} {'✓' if setpoints_after == zones_after else '❌'}")

# Verify schedules
heating_sch = idf.idfobjects.get('SCHEDULE:CONSTANT', [])
heating_names = [sch.Name for sch in heating_sch]

print(f"\nSchedules:")
print(f"  HeatingSetpoint: {'✓' if 'HeatingSetpoint' in heating_names else '❌'}")
print(f"  CoolingSetpoint: {'✓' if 'CoolingSetpoint' in heating_names else '❌'}")
print(f"  AlwaysOn: {'✓' if 'AlwaysOn' in heating_names else '❌'}")

# Validate
print("\n" + "=" * 80)
if (template_after == zones_after and
    thermostats_after == zones_after and
    setpoints_after == zones_after and
    hvac_after == 0):
    print("✅ TEST PASSED: All zones have HVACTEMPLATE + thermostats!")
    print(f"   - {template_after} HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM objects")
    print(f"   - {thermostats_after} ZONECONTROL:THERMOSTAT objects")
    print(f"   - {setpoints_after} THERMOSTATSETPOINT:DUALSETPOINT objects")
    print(f"   - 0 direct HVAC objects (will be created by ExpandObjects)")

    # Save fixed IDF
    output_path = Path("output/building_with_hvactemplate.idf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    idf.save(str(output_path))
    print(f"\n✅ Saved fixed IDF to: {output_path}")

    print("\n" + "=" * 80)
    print("Next step: Test simulation with runner.py")
    print("  (runner.py will automatically run ExpandObjects)")
    print("=" * 80)

    sys.exit(0)
else:
    print("❌ TEST FAILED!")
    if hvac_after > 0:
        print(f"   ❌ Found {hvac_after} direct HVAC objects (should be 0)")
    if template_after != zones_after:
        print(f"   ❌ Expected {zones_after} templates, got {template_after}")
    if thermostats_after != zones_after:
        print(f"   ❌ Expected {zones_after} thermostats, got {thermostats_after}")
    if setpoints_after != zones_after:
        print(f"   ❌ Expected {zones_after} setpoints, got {setpoints_after}")
    sys.exit(1)
