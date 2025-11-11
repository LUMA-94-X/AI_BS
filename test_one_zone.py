#!/usr/bin/env python3
"""Test with just one zone."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eppy.modeleditor import IDF
from features.hvac.ideal_loads import HVACTemplateManager

# Load existing IDF
idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
IDF.setiddname(str(idd_file))

idf_path = Path("output/simulation_20251111_233258/building.idf")
idf = IDF(str(idf_path))

# Keep only FIRST zone and its surfaces
zones = idf.idfobjects.get('ZONE', [])
first_zone = zones[0]
first_zone_name = first_zone.Name

print(f"Keeping only zone: {first_zone_name}")

# Remove all other zones
for zone in zones[1:]:
    idf.removeidfobject(zone)

# Remove surfaces not belonging to first zone
surfaces = idf.idfobjects.get('BUILDINGSURFACE:DETAILED', [])
for surf in list(surfaces):
    if surf.Zone_Name != first_zone_name:
        idf.removeidfobject(surf)

# Remove all existing HVAC
for obj_type in ['ZONEHVAC:IDEALLOADSAIRSYSTEM', 'ZONEHVAC:EQUIPMENTLIST',
                 'ZONEHVAC:EQUIPMENTCONNECTIONS', 'ZONECONTROL:THERMOSTAT',
                 'THERMOSTATSETPOINT:DUALSETPOINT']:
    objects = idf.idfobjects.get(obj_type, [])
    for obj in list(objects):
        idf.removeidfobject(obj)

# Apply HVAC
manager = HVACTemplateManager()
idf = manager.apply_template_simple(idf, template_name="ideal_loads")

# Save
output_path = Path("output/building_one_zone.idf")
idf.save(str(output_path))

print(f"✅ Saved: {output_path}")
print(f"   Zones: {len(idf.idfobjects.get('ZONE', []))}")
print(f"   Surfaces: {len(idf.idfobjects.get('BUILDINGSURFACE:DETAILED', []))}")
print(f"   HVAC: {len(idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', []))}")
