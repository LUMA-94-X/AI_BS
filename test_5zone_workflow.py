#!/usr/bin/env python3
"""Test complete 5-Zone workflow: Energieausweis → IDF → Simulation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from features.geometrie.models.energieausweis_input import (
    EnergieausweisInput,
    FensterData,
    create_example_efh
)
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from core.config import get_config
from eppy.modeleditor import IDF


def test_5zone_workflow():
    """Test complete 5-Zone workflow."""

    print("=" * 80)
    print("5-ZONE WORKFLOW TEST")
    print("=" * 80)

    # 1. Create test Energieausweis input
    print("\n1. Creating test Energieausweis input...")

    # Use example data
    ea_data = create_example_efh()

    print(f"  ✓ Gebäudetyp: {ea_data.gebaeudetyp}")
    print(f"  ✓ Nettofläche: {ea_data.nettoflaeche_m2} m²")
    print(f"  ✓ Geschosse: {ea_data.anzahl_geschosse}")
    print(f"  ✓ U-Wand: {ea_data.u_wert_wand} W/m²K")
    print(f"  ✓ U-Fenster: {ea_data.u_wert_fenster} W/m²K")
    print(f"  ✓ Fensterflächen: N={ea_data.fenster.nord_m2}, O={ea_data.fenster.ost_m2}, "
          f"S={ea_data.fenster.sued_m2}, W={ea_data.fenster.west_m2} m²")

    # 2. Generate 5-Zone IDF
    print("\n2. Generating 5-Zone IDF...")

    try:
        config = get_config()
        generator = FiveZoneGenerator(config)

        output_path = Path("output/test_workflow/gebaeude_5zone_test.idf")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        idf = generator.create_from_energieausweis(
            ea_data=ea_data,
            output_path=output_path
        )

        print(f"  ✓ IDF created: {output_path}")

    except Exception as e:
        print(f"  ❌ Error creating IDF: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Verify IDF content
    print("\n3. Verifying IDF content...")

    try:
        # Re-read IDF to verify it was saved correctly
        idd_file = generator._get_idd_file()
        IDF.setiddname(idd_file)
        idf_verify = IDF(str(output_path))

        # Check VERSION
        version_obj = idf_verify.idfobjects['VERSION'][0]
        version = version_obj.Version_Identifier
        print(f"  VERSION: {version}")

        if version != "25.1":
            print(f"  ❌ FAIL: Expected version 25.1, got {version}")
            return False
        else:
            print(f"  ✓ PASS: Version is 25.1")

        # Check SIMULATIONCONTROL
        sim_control = idf_verify.idfobjects['SIMULATIONCONTROL'][0]
        zone_sizing = sim_control.Do_Zone_Sizing_Calculation
        system_sizing = sim_control.Do_System_Sizing_Calculation
        weather_run = sim_control.Run_Simulation_for_Weather_File_Run_Periods

        print(f"\n  SIMULATIONCONTROL:")
        print(f"    Do_Zone_Sizing_Calculation: {zone_sizing}")
        print(f"    Do_System_Sizing_Calculation: {system_sizing}")
        print(f"    Run_Simulation_for_Weather_File_Run_Periods: {weather_run}")

        if zone_sizing != "No":
            print(f"  ❌ FAIL: Zone sizing should be 'No', got '{zone_sizing}'")
            return False
        else:
            print(f"  ✓ PASS: Zone sizing is disabled")

        if system_sizing != "No":
            print(f"  ❌ FAIL: System sizing should be 'No', got '{system_sizing}'")
            return False
        else:
            print(f"  ✓ PASS: System sizing is disabled")

        if weather_run != "Yes":
            print(f"  ❌ FAIL: Weather run should be 'Yes', got '{weather_run}'")
            return False
        else:
            print(f"  ✓ PASS: Annual simulation is enabled")

        # Check SIZING:ZONE (should NOT exist)
        sizing_zones = idf_verify.idfobjects.get('SIZING:ZONE', [])
        if sizing_zones:
            print(f"  ❌ FAIL: Found {len(sizing_zones)} SIZING:ZONE objects (should be 0)")
            return False
        else:
            print(f"  ✓ PASS: No SIZING:ZONE objects (correct)")

        # Check zones
        zones = idf_verify.idfobjects['ZONE']
        print(f"\n  ZONES: {len(zones)} zones created")
        for zone in zones:
            print(f"    - {zone.Name}")

        if len(zones) < 5:
            print(f"  ⚠ WARNING: Expected at least 5 zones per floor")
        else:
            print(f"  ✓ PASS: Zones created")

        # Check surfaces
        surfaces = idf_verify.idfobjects['BUILDINGSURFACE:DETAILED']
        windows = idf_verify.idfobjects.get('FENESTRATIONSURFACE:DETAILED', [])

        print(f"\n  SURFACES:")
        print(f"    BuildingSurface:Detailed: {len(surfaces)}")
        print(f"    FenestrationSurface:Detailed: {len(windows)}")

        if len(surfaces) == 0:
            print(f"  ❌ FAIL: No surfaces created")
            return False
        else:
            print(f"  ✓ PASS: Surfaces created")

        # Check HVAC
        ideal_loads = idf_verify.idfobjects.get('HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM', [])
        print(f"\n  HVAC:")
        print(f"    HVACTemplate:Zone:IdealLoadsAirSystem: {len(ideal_loads)}")

        if len(ideal_loads) == 0:
            print(f"  ⚠ WARNING: No IdealLoads HVAC found")
        else:
            print(f"  ✓ PASS: IdealLoads HVAC configured")

    except Exception as e:
        print(f"  ❌ Error verifying IDF: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Optional: Quick simulation test (commented out by default)
    print("\n4. Simulation test (skipped - run manually if needed)")
    print("   To test simulation, use: features/simulation/runner.py")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Test in Streamlit UI:")
    print("     streamlit run features/web_ui/Start.py")
    print("  2. Go through Energieausweis → HVAC → Simulation workflow")
    print("  3. Verify annual simulation produces results (not 0.6s)")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = test_5zone_workflow()
    sys.exit(0 if success else 1)
