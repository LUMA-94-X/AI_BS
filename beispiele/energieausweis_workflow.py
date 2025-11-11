"""
Vollständiges Beispiel: 5-Zone-Gebäudemodell aus Energieausweis-Daten.

Dieses Script demonstriert den kompletten Workflow:
1. Energieausweis-Daten definieren
2. Geometrie automatisch rekonstruieren
3. 5-Zone-IDF generieren
4. HVAC-System hinzufügen
5. Simulation ausführen (optional)
6. Ergebnisse auswerten (optional)
"""

import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

from features.geometrie.models.energieausweis_input import (
    EnergieausweisInput,
    FensterData,
    GebaeudeTyp
)
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from features.geometrie.utils.geometry_solver import (
    GeometrySolver,
    print_solution_summary
)
from features.hvac.ideal_loads import create_building_with_hvac


def main():
    """Hauptfunktion: Vollständiger Workflow."""

    print("\n" + "="*70)
    print("5-ZONE-GEBÄUDEMODELL AUS ENERGIEAUSWEIS")
    print("="*70)

    # ========================================================================
    # SCHRITT 1: ENERGIEAUSWEIS-DATEN DEFINIEREN
    # ========================================================================

    print("\n📋 Schritt 1: Energieausweis-Daten definieren")
    print("-" * 70)

    # Beispiel: Einfamilienhaus Neubau 2010
    ea_data = EnergieausweisInput(
        # ---- GEBÄUDEDATEN ----
        nettoflaeche_m2=150.0,
        gebaeudetyp=GebaeudeTyp.EFH,
        anzahl_geschosse=2,
        geschosshoehe_m=2.8,
        baujahr=2010,

        # ---- HÜLLFLÄCHEN (Optional für bessere Geometrie) ----
        wandflaeche_m2=240.0,
        dachflaeche_m2=80.0,
        bodenflaeche_m2=80.0,

        # ---- U-WERTE ----
        u_wert_wand=0.28,      # Gut gedämmt (EnEV 2009)
        u_wert_dach=0.20,      # Gut gedämmt
        u_wert_boden=0.35,
        u_wert_fenster=1.30,   # Isolierverglasung
        g_wert_fenster=0.60,

        # ---- FENSTER (Exakte Flächen pro Orientierung) ----
        fenster=FensterData(
            nord_m2=8.0,   # Wenig Fenster nach Norden
            ost_m2=12.0,
            sued_m2=20.0,  # Hauptfenster nach Süden
            west_m2=10.0
        ),

        # ---- LÜFTUNG ----
        luftwechselrate_h=0.5,
        infiltration_ach50=3.0,  # Blower-Door-Test (gut gedichtet)

        # ---- GEOMETRIE-HINTS ----
        aspect_ratio_hint=1.3  # Leicht länglich
    )

    print(f"  Gebäudetyp: {ea_data.gebaeudetyp.value}")
    print(f"  Nettofläche: {ea_data.nettoflaeche_m2:.1f} m²")
    print(f"  Geschosse: {ea_data.anzahl_geschosse}")
    print(f"  U-Wand: {ea_data.u_wert_wand:.2f} W/m²K")
    print(f"  Fenster Süd: {ea_data.fenster.sued_m2:.1f} m²")

    # ========================================================================
    # SCHRITT 2: GEOMETRIE REKONSTRUIEREN
    # ========================================================================

    print("\n🔍 Schritt 2: Geometrie automatisch rekonstruieren")
    print("-" * 70)

    solver = GeometrySolver()
    geo_solution = solver.solve(ea_data)

    print_solution_summary(geo_solution)

    # ========================================================================
    # SCHRITT 3: 5-ZONE-IDF GENERIEREN
    # ========================================================================

    print("\n🏗️ Schritt 3: 5-Zone-IDF generieren")
    print("-" * 70)

    output_dir = projekt_root / "output" / "energieausweis_workflow"
    output_dir.mkdir(parents=True, exist_ok=True)
    idf_path = output_dir / "gebaeude_5zone.idf"

    generator = FiveZoneGenerator()

    print("  Erstelle IDF...")
    idf = generator.create_from_energieausweis(
        ea_data=ea_data,
        output_path=idf_path
    )

    # Statistiken
    zones = idf.idfobjects["ZONE"]
    surfaces = idf.idfobjects["BUILDINGSURFACE:DETAILED"]
    windows = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]

    print(f"\n  ✅ IDF erstellt: {idf_path}")
    print(f"\n  📊 Statistiken:")
    print(f"    Zonen: {len(zones)}")
    print(f"    Surfaces: {len(surfaces)}")
    print(f"    Fenster: {len(windows)}")

    # Zonen auflisten
    print(f"\n  🔹 Zonen:")
    for zone in zones:
        print(f"    - {zone.Name}")

    # ========================================================================
    # SCHRITT 4: HVAC-SYSTEM HINZUFÜGEN (Optional)
    # ========================================================================

    print("\n❄️ Schritt 4: HVAC-System hinzufügen")
    print("-" * 70)

    # Füge Ideal Loads HVAC zu allen Zonen hinzu
    idf = create_building_with_hvac(idf)

    # Speichere finales IDF
    idf_final_path = output_dir / "gebaeude_5zone_mit_hvac.idf"
    idf.save(str(idf_final_path))

    print(f"  ✅ HVAC hinzugefügt: {idf_final_path}")

    # ========================================================================
    # SCHRITT 5: SIMULATION (Optional - auskommentiert)
    # ========================================================================

    print("\n▶️ Schritt 5: Simulation (optional)")
    print("-" * 70)

    # Uncomment um Simulation durchzuführen:
    """
    from features.simulation.runner import EnergyPlusRunner

    weather_file = projekt_root / "data" / "weather" / "example.epw"

    if weather_file.exists():
        runner = EnergyPlusRunner()
        result = runner.run_simulation(
            idf_path=idf_final_path,
            weather_file=weather_file,
            output_dir=output_dir
        )

        if result.success:
            print(f"  ✅ Simulation erfolgreich ({result.execution_time:.1f}s)")
            print(f"  📁 Ergebnisse: {result.output_dir}")

            # Auswertung
            from features.auswertung.kpi_rechner import KennzahlenRechner

            rechner = KennzahlenRechner(nettoflaeche_m2=ea_data.nettoflaeche_m2)
            kennzahlen = rechner.berechne_kennzahlen(sql_file=result.sql_file)

            print(f"\n  📊 Ergebnisse:")
            print(f"    Energiekennzahl: {kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m²a")
            print(f"    Effizienzklasse: {kennzahlen.effizienzklasse}")
        else:
            print(f"  ❌ Simulation fehlgeschlagen: {result.error_message}")
    else:
        print(f"  ⚠️  Wetterdatei nicht gefunden: {weather_file}")
        print(f"     Simulation übersprungen.")
    """

    print("  💡 Auskommentiert - Aktiviere Code im Script für Simulation")

    # ========================================================================
    # ZUSAMMENFASSUNG
    # ========================================================================

    print("\n" + "="*70)
    print("✅ WORKFLOW ABGESCHLOSSEN!")
    print("="*70)

    print(f"\nErstellt:")
    print(f"  1. IDF ohne HVAC: {idf_path}")
    print(f"  2. IDF mit HVAC:  {idf_final_path}")

    print(f"\nNächste Schritte:")
    print(f"  - Öffne IDF in EnergyPlus zur Validierung")
    print(f"  - Aktiviere Simulation im Script (Schritt 5)")
    print(f"  - Oder nutze Web-UI: python scripts/ui_starten.py")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
