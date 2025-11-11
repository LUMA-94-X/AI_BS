"""Einfaches Beispiel für eine Gebäudesimulation."""

import sys
from pathlib import Path

# Projekt-Root zum Python-Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

from features.geometrie.box_generator import SimpleBoxGenerator, BuildingGeometry
from features.hvac.ideal_loads import create_building_with_hvac
from features.simulation.runner import EnergyPlusRunner
from features.auswertung.kpi_rechner import KennzahlenRechner
from features.auswertung.visualisierung import ErgebnisVisualisierer


def main():
    """Führe einfache Simulation durch."""

    print("🏢 Einfache Gebäudesimulation")
    print("=" * 50)

    # 1. Gebäudegeometrie definieren
    print("\n1️⃣ Erstelle Gebäudegeometrie...")
    geometrie = BuildingGeometry(
        length=20.0,        # 20m lang
        width=12.0,         # 12m breit
        height=6.0,         # 6m hoch (2 Stockwerke)
        num_floors=2,
        window_wall_ratio=0.3,  # 30% Fensterflächenanteil
        orientation=0.0,    # Nach Norden ausgerichtet
    )

    print(f"   ✅ Gebäude: {geometrie.length}m x {geometrie.width}m x {geometrie.height}m")
    print(f"   📐 Nettofläche: {geometrie.total_floor_area:.0f} m²")

    # 2. IDF-Modell erstellen
    print("\n2️⃣ Generiere IDF-Modell...")
    generator = SimpleBoxGenerator()
    idf_path = projekt_root / "output" / "einfaches_gebaeude.idf"
    idf_path.parent.mkdir(parents=True, exist_ok=True)

    idf = generator.create_model(geometrie, idf_path)
    print(f"   ✅ IDF erstellt: {idf_path.name}")

    # 3. HVAC-System hinzufügen
    print("\n3️⃣ Füge HVAC-System hinzu...")
    idf = create_building_with_hvac(idf, "ideal_loads")
    idf.save(str(idf_path))
    print("   ✅ HVAC-System hinzugefügt (Ideal Loads)")

    # 4. Simulation ausführen
    print("\n4️⃣ Führe Simulation aus...")
    weather_file = projekt_root / "data" / "weather" / "example.epw"

    if not weather_file.exists():
        print(f"   ❌ Wetterdatei nicht gefunden: {weather_file}")
        print("   💡 Bitte example.epw in data/weather/ ablegen")
        return

    runner = EnergyPlusRunner()
    output_dir = projekt_root / "output" / "einfache_simulation"

    result = runner.run_simulation(
        idf_path=idf_path,
        weather_file=weather_file,
        output_dir=output_dir,
    )

    if not result.success:
        print(f"   ❌ Simulation fehlgeschlagen: {result.error_message}")
        return

    print(f"   ✅ Simulation erfolgreich! ({result.execution_time:.1f}s)")

    # 5. Ergebnisse auswerten
    print("\n5️⃣ Werte Ergebnisse aus...")
    rechner = KennzahlenRechner(nettoflaeche_m2=geometrie.total_floor_area)
    kennzahlen = rechner.berechne_kennzahlen(sql_file=result.sql_file)

    print(f"\n📊 Ergebnisse:")
    print(f"   Energiekennzahl: {kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a")
    print(f"   Effizienzklasse: {kennzahlen.effizienzklasse}")
    print(f"   Heizbedarf: {kennzahlen.heizkennzahl_kwh_m2a:.1f} kWh/m²a")
    print(f"   Kühlbedarf: {kennzahlen.kuehlkennzahl_kwh_m2a:.1f} kWh/m²a")
    print(f"   Thermischer Komfort: {kennzahlen.thermische_behaglichkeit}")
    print(f"\n💡 Bewertung: {kennzahlen.bewertung}")

    # 6. Visualisierungen erstellen
    print("\n6️⃣ Erstelle Visualisierungen...")
    viz = ErgebnisVisualisierer()

    # Dashboard speichern
    dashboard = viz.erstelle_dashboard(kennzahlen, result.sql_file)
    dashboard_path = output_dir / "dashboard.html"
    dashboard.write_html(str(dashboard_path))

    print(f"   ✅ Dashboard gespeichert: {dashboard_path}")
    print(f"\n🎉 Fertig! Öffne {dashboard_path} im Browser.")


if __name__ == "__main__":
    main()
