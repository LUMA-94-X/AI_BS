#!/usr/bin/env python3
"""Fix 5-Zone IDF: Upgrade to v25.1 and disable sizing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from eppy.modeleditor import IDF

def fix_idf(idf_path: Path):
    """Fix IDF file."""

    print(f"Fixing IDF: {idf_path}")

    # Set IDD for version 25.1
    idd_file = Path("/mnt/c/EnergyPlusV25-1-0/Energy+.idd")
    if not idd_file.exists():
        print(f"❌ IDD file not found: {idd_file}")
        return False

    IDF.setiddname(str(idd_file))

    try:
        # Load IDF
        idf = IDF(str(idf_path))

        # Check version
        version_obj = idf.idfobjects['VERSION'][0]
        current_version = version_obj.Version_Identifier
        print(f"Current version: {current_version}")

        # Update version to 25.1
        if current_version != "25.1":
            version_obj.Version_Identifier = "25.1"
            print(f"✓ Updated version to 25.1")

        # Disable sizing (not needed for IdealLoads)
        sim_control = idf.idfobjects['SIMULATIONCONTROL'][0]

        print("\nSimulationControl BEFORE:")
        print(f"  Do Zone Sizing: {sim_control.Do_Zone_Sizing_Calculation}")
        print(f"  Do System Sizing: {sim_control.Do_System_Sizing_Calculation}")
        print(f"  Run Weather File Periods: {sim_control.Run_Simulation_for_Weather_File_Run_Periods}")

        sim_control.Do_Zone_Sizing_Calculation = "No"
        sim_control.Do_System_Sizing_Calculation = "No"
        # Keep Run Weather File Periods = Yes!

        print("\nSimulationControl AFTER:")
        print(f"  Do Zone Sizing: {sim_control.Do_Zone_Sizing_Calculation}")
        print(f"  Do System Sizing: {sim_control.Do_System_Sizing_Calculation}")
        print(f"  Run Weather File Periods: {sim_control.Run_Simulation_for_Weather_File_Run_Periods}")

        # Remove SIZING:ZONE objects (not needed, can cause errors)
        sizing_zones = idf.idfobjects.get('SIZING:ZONE', [])
        if sizing_zones:
            print(f"\n✓ Removing {len(sizing_zones)} SIZING:ZONE objects (not needed for IdealLoads)")
            for obj in list(sizing_zones):
                idf.removeidfobject(obj)

        # Save
        idf.save(str(idf_path))
        print(f"\n✅ IDF fixed and saved: {idf_path}")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    idf_path = Path("output/energieausweis/gebaeude_5zone.idf")

    if not idf_path.exists():
        print(f"❌ IDF not found: {idf_path}")
        sys.exit(1)

    # Create backup
    backup_path = idf_path.parent / f"{idf_path.stem}_backup.idf"
    import shutil
    shutil.copy(str(idf_path), str(backup_path))
    print(f"✓ Backup created: {backup_path}\n")

    success = fix_idf(idf_path)

    sys.exit(0 if success else 1)
