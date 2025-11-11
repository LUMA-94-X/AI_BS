"""Test HVAC template with single floor building."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.hvac.template_manager import HVACTemplateManager
from src.simulation.runner import EnergyPlusRunner
from src.utils.config import get_config


def main():
    print("🧪 TEST: HVAC-Template mit 1-Geschoss-Gebäude")
    print("=" * 80)

    config = get_config()
    output_dir = Path("output/test_hvac_single")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Simple single-floor building
    geometry = BuildingGeometry(
        length=10.0,
        width=8.0,
        height=3.0,
        num_floors=1,  # Single floor only
        window_wall_ratio=0.3,
        orientation=0.0,
    )

    print(f"✅ Gebäude: {geometry.length}m x {geometry.width}m x {geometry.height}m")
    print(f"✅ Geschosse: {geometry.num_floors}")

    # Generate geometry
    generator = SimpleBoxGenerator(config)
    idf = generator.create_model(geometry)

    print(f"✅ {len(idf.idfobjects['ZONE'])} Zonen")
    print(f"✅ {len(idf.idfobjects.get('FENESTRATIONSURFACE:DETAILED', []))} Fenster")

    # Apply HVAC
    print("\n🔧 Füge HVAC hinzu...")
    hvac_manager = HVACTemplateManager()
    idf = hvac_manager.apply_template_simple(idf, "ideal_loads")

    hvac_count = len(idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', []))
    print(f"✅ {hvac_count} HVAC-Systeme hinzugefügt")

    # Save
    idf_path = output_dir / "single_floor_with_hvac.idf"
    idf.saveas(str(idf_path), encoding='utf-8')
    print(f"✅ IDF gespeichert: {idf_path}")

    # Simulate
    print("\n🔧 Simuliere...")
    weather_file = Path("data/weather/example.epw")

    if not weather_file.exists():
        print("⚠️  Wetterdatei nicht gefunden")
        return True

    runner = EnergyPlusRunner(config)
    result = runner.run_simulation(
        idf_path=idf_path,
        weather_file=weather_file,
        output_dir=output_dir / "sim",
        output_prefix="single"
    )

    if result.success:
        print(f"✅ Simulation erfolgreich! ({result.execution_time:.2f}s)")
        html = result.output_dir / "singleTable.htm"
        if html.exists():
            print(f"✅ HTML-Report: {html}")
        return True
    else:
        print(f"❌ Simulation fehlgeschlagen")
        print(f"Error: {result.error_message[:300]}")
        # Print error file
        err_file = result.output_dir / "singleout.err"
        if err_file.exists():
            print("\nFehlerlog:")
            print(err_file.read_text(encoding='utf-8', errors='ignore')[:1000])
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
