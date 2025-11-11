"""Beispiel: 5-Zone-Modell aus Energieausweis-Daten erstellen."""

import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

from features.geometrie.models.energieausweis_input import (
    create_example_efh,
    create_example_mfh
)
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from features.geometrie.utils.geometry_solver import print_solution_summary


def test_efh_5_zone():
    """Test: Einfamilienhaus als 5-Zone-Modell."""
    print("\n" + "="*70)
    print("TEST: EINFAMILIENHAUS 5-ZONE-MODELL")
    print("="*70)

    # 1. Energieausweis-Daten
    ea_data = create_example_efh()

    print("\nInput:")
    print(f"  Nettofläche: {ea_data.nettoflaeche_m2:.1f} m²")
    print(f"  Wandfläche: {ea_data.wandflaeche_m2:.1f} m²")
    print(f"  U-Wand: {ea_data.u_wert_wand:.2f} W/m²K")
    print(f"  U-Fenster: {ea_data.u_wert_fenster:.2f} W/m²K")
    print(f"  Fenster Nord: {ea_data.fenster.nord_m2:.1f} m²")
    print(f"  Fenster Süd: {ea_data.fenster.sued_m2:.1f} m²")

    # 2. Generator erstellen
    generator = FiveZoneGenerator()

    # 3. IDF erstellen
    output_path = projekt_root / "output" / "test_efh_5zone.idf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n⏳ Erstelle 5-Zone-IDF...")

    try:
        idf = generator.create_from_energieausweis(
            ea_data=ea_data,
            output_path=output_path
        )

        print(f"✅ IDF erstellt: {output_path}")

        # 4. Statistiken
        zones = idf.idfobjects["ZONE"]
        surfaces = idf.idfobjects["BUILDINGSURFACE:DETAILED"]
        windows = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]

        print(f"\n📊 IDF-Statistiken:")
        print(f"  Zonen: {len(zones)}")
        print(f"  Surfaces: {len(surfaces)}")
        print(f"  Fenster: {len(windows)}")

        # Zonen-Namen auflisten
        print(f"\n  Zonen-Namen:")
        for i, zone in enumerate(zones[:10]):  # Max 10 anzeigen
            print(f"    {i+1}. {zone.Name}")
        if len(zones) > 10:
            print(f"    ... und {len(zones)-10} weitere")

        # Fenster-Verteilung
        print(f"\n  Fenster-Verteilung:")
        window_count = {}
        for window in windows:
            wall_name = window.Building_Surface_Name
            # Extrahiere Orientierung aus Wall-Name
            if "North" in wall_name:
                orient = "Nord"
            elif "South" in wall_name:
                orient = "Süd"
            elif "East" in wall_name:
                orient = "Ost"
            elif "West" in wall_name:
                orient = "West"
            else:
                orient = "Unbekannt"

            window_count[orient] = window_count.get(orient, 0) + 1

        for orient, count in sorted(window_count.items()):
            print(f"    {orient}: {count} Fenster")

        return True

    except Exception as e:
        print(f"❌ Fehler beim Erstellen: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mfh_5_zone():
    """Test: Mehrfamilienhaus als 5-Zone-Modell."""
    print("\n" + "="*70)
    print("TEST: MEHRFAMILIENHAUS 5-ZONE-MODELL")
    print("="*70)

    # 1. Energieausweis-Daten
    ea_data = create_example_mfh()

    print("\nInput:")
    print(f"  Nettofläche: {ea_data.nettoflaeche_m2:.1f} m²")
    print(f"  Geschosse: {ea_data.anzahl_geschosse}")
    print(f"  Gebäudetyp: {ea_data.gebaeudetyp.value}")

    # 2. Generator erstellen
    generator = FiveZoneGenerator()

    # 3. IDF erstellen
    output_path = projekt_root / "output" / "test_mfh_5zone.idf"

    print("\n⏳ Erstelle 5-Zone-IDF...")

    try:
        idf = generator.create_from_energieausweis(
            ea_data=ea_data,
            output_path=output_path
        )

        print(f"✅ IDF erstellt: {output_path}")

        # Statistiken
        zones = idf.idfobjects["ZONE"]
        surfaces = idf.idfobjects["BUILDINGSURFACE:DETAILED"]

        print(f"\n📊 IDF-Statistiken:")
        print(f"  Zonen: {len(zones)} (sollte 15 sein: 5 Zonen × 3 Geschosse)")
        print(f"  Surfaces: {len(surfaces)}")

        # Prüfe ob alle Stockwerke da sind
        floors_found = set()
        for zone in zones:
            # Extrahiere Floor-Nummer aus Namen (z.B. "Perimeter_North_F1")
            if "_F" in zone.Name:
                floor_part = zone.Name.split("_F")[1]
                floor_num = int(floor_part)
                floors_found.add(floor_num)

        print(f"  Stockwerke gefunden: {sorted(floors_found)}")

        assert len(zones) == 15, f"Sollte 15 Zonen haben, hat aber {len(zones)}"
        assert len(floors_found) == 3, f"Sollte 3 Stockwerke haben, hat aber {len(floors_found)}"

        print("\n✅ MFH-Test erfolgreich!")
        return True

    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führt alle Tests aus."""
    print("\n" + "#"*70)
    print("# 5-ZONE-GENERATOR TEST-SUITE")
    print("#"*70)

    success_count = 0
    total_tests = 2

    # Test 1: EFH
    if test_efh_5_zone():
        success_count += 1

    # Test 2: MFH
    if test_mfh_5_zone():
        success_count += 1

    # Zusammenfassung
    print("\n" + "="*70)
    if success_count == total_tests:
        print(f"✅ ALLE TESTS ERFOLGREICH! ({success_count}/{total_tests})")
    else:
        print(f"⚠️  EINIGE TESTS FEHLGESCHLAGEN ({success_count}/{total_tests})")
    print("="*70 + "\n")

    return success_count == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
