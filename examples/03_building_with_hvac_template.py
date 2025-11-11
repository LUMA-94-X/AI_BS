"""Example: Create building with HVAC template system.

This example demonstrates how to:
1. Generate building geometry with SimpleBoxGenerator
2. Apply an HVAC template using HVACTemplateManager
3. Run a complete simulation with Salzburg weather
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.hvac.template_manager import HVACTemplateManager, create_building_with_hvac
from src.simulation.runner import EnergyPlusRunner
from src.utils.config import get_config


def main():
    print("=" * 80)
    print("🏢 Gebäude mit HVAC-Template erstellen und simulieren")
    print("=" * 80)

    config = get_config()
    output_dir = Path("output/building_with_hvac")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create building geometry
    print("\n1️⃣  Erstelle Gebäude-Geometrie...")
    geometry = BuildingGeometry(
        length=15.0,       # 15m x 12m Grundfläche
        width=12.0,
        height=9.0,        # 9m hoch = 3 Geschosse à 3m
        num_floors=3,
        window_wall_ratio=0.35,  # 35% Fensterflächenanteil
        orientation=0.0,
    )

    print(f"   ✅ Gebäude: {geometry.length}m x {geometry.width}m x {geometry.height}m")
    print(f"   ✅ Geschosse: {geometry.num_floors}")
    print(f"   ✅ Gesamt-Grundfläche: {geometry.total_floor_area:.0f} m²")
    print(f"   ✅ WWR: {geometry.window_wall_ratio * 100:.0f}%")

    # Step 2: Generate geometry IDF
    print("\n2️⃣  Generiere Geometrie-Modell...")
    generator = SimpleBoxGenerator(config)
    idf = generator.create_model(geometry)  # Don't save yet

    zones = len(idf.idfobjects['ZONE'])
    surfaces = len(idf.idfobjects['BUILDINGSURFACE:DETAILED'])
    windows = len(idf.idfobjects.get('FENESTRATIONSURFACE:DETAILED', []))

    print(f"   ✅ {zones} Zonen")
    print(f"   ✅ {surfaces} Oberflächen")
    print(f"   ✅ {windows} Fenster")

    # Step 3: Apply HVAC template
    print("\n3️⃣  Füge HVAC-System hinzu...")

    # List available templates
    hvac_manager = HVACTemplateManager()
    templates = hvac_manager.list_templates()

    print(f"   📋 Verfügbare HVAC-Templates:")
    for name, template in templates.items():
        print(f"      - {name}: {template.description}")
        print(f"        Komplexität: {template.complexity}, Geeignet für: {', '.join(template.suitable_for)}")

    # Apply ideal_loads template (simplest and most reliable)
    print(f"\n   🔧 Wende 'ideal_loads' Template an...")
    idf = hvac_manager.apply_template_simple(idf, "ideal_loads")

    # Check HVAC was added
    hvac_count = len(idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', []))
    equip_list_count = len(idf.idfobjects.get('ZONEHVAC:EQUIPMENTLIST', []))
    equip_conn_count = len(idf.idfobjects.get('ZONEHVAC:EQUIPMENTCONNECTIONS', []))

    print(f"\n   📊 HVAC-Objekte:")
    print(f"      - Ideal Loads Systeme: {hvac_count}")
    print(f"      - Equipment Lists: {equip_list_count}")
    print(f"      - Equipment Connections: {equip_conn_count}")

    if hvac_count == zones:
        print(f"   ✅ HVAC erfolgreich für alle {zones} Zonen hinzugefügt!")
    else:
        print(f"   ⚠️  HVAC nur für {hvac_count} von {zones} Zonen hinzugefügt")

    # Step 4: Save complete IDF
    print("\n4️⃣  Speichere vollständiges IDF...")
    idf_path = output_dir / "complete_building.idf"
    idf.saveas(str(idf_path), encoding='utf-8')

    print(f"   ✅ IDF gespeichert: {idf_path}")
    print(f"   ✅ Dateigröße: {idf_path.stat().st_size:,} bytes")

    # Step 5: Run simulation
    print("\n5️⃣  Führe Simulation durch...")
    weather_file = Path("data/weather/example.epw")

    if not weather_file.exists():
        print(f"   ⚠️  Wetterdatei nicht gefunden: {weather_file}")
        print(f"   ℹ️  IDF wurde erstellt, Simulation übersprungen")
        return True

    runner = EnergyPlusRunner(config)

    try:
        result = runner.run_simulation(
            idf_path=idf_path,
            weather_file=weather_file,
            output_dir=output_dir / "simulation",
            output_prefix="building"
        )

        if result.success:
            print(f"\n   ✅ Simulation erfolgreich!")
            print(f"   ✅ Laufzeit: {result.execution_time:.2f} Sekunden")
            print(f"   ✅ Ergebnisse: {result.output_dir}")

            # Check output files
            html_report = result.output_dir / "buildingTable.htm"
            sql_file = result.output_dir / "building.sql"
            err_file = result.output_dir / "buildingout.err"

            if html_report.exists():
                print(f"\n   📊 Ergebnis-Dateien:")
                print(f"      - HTML-Report: {html_report}")
                if sql_file.exists():
                    print(f"      - SQL-Datenbank: {sql_file}")

                # Check for errors
                if err_file.exists():
                    with open(err_file, 'r', encoding='utf-8', errors='ignore') as f:
                        errors = [line for line in f if 'Severe' in line or 'Fatal' in line]
                    if errors:
                        print(f"\n   ⚠️  {len(errors)} schwere Fehler in Simulation:")
                        for err in errors[:3]:
                            print(f"      {err.strip()}")
                    else:
                        print(f"      - Keine schweren Fehler ✅")

        else:
            print(f"\n   ❌ Simulation fehlgeschlagen")
            print(f"   ❌ Fehler: {result.error_message[:200]}...")
            return False

    except Exception as e:
        print(f"\n   ❌ Fehler bei Simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "=" * 80)
    print("✅ VOLLSTÄNDIGER WORKFLOW ERFOLGREICH")
    print("=" * 80)
    print("\n🎯 Zusammenfassung:")
    print(f"  1. ✅ Gebäude-Geometrie generiert ({zones} Zonen, {windows} Fenster)")
    print(f"  2. ✅ HVAC-Template angewendet (ideal_loads)")
    print(f"  3. ✅ IDF gespeichert ({idf_path})")
    print(f"  4. ✅ Simulation durchgeführt")
    print(f"\n📊 Ergebnisse anschauen:")
    print(f"  explorer.exe {html_report}")
    print()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
