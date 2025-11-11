"""Tests für Sprint 2: Perimeter-Berechnung und Fensterverteilung."""

import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

from features.geometrie.utils.perimeter_calculator import (
    PerimeterCalculator,
    print_zone_layout_summary
)
from features.geometrie.utils.fenster_distribution import (
    FensterDistribution,
    print_window_distribution,
    create_example_distributions
)
from features.geometrie.models.energieausweis_input import (
    FensterData,
    GebaeudeTyp
)


def test_perimeter_calculation():
    """Test: Adaptive Perimeter-Tiefe-Berechnung."""
    print("\n" + "="*70)
    print("TEST 1: ADAPTIVE PERIMETER-TIEFE")
    print("="*70)

    calc = PerimeterCalculator()

    # Testfälle mit verschiedenen WWR
    test_cases = [
        (0.10, "Niedriger WWR (10%)"),
        (0.30, "Mittlerer WWR (30%)"),
        (0.50, "Hoher WWR (50%)"),
        (0.70, "Sehr hoher WWR (70%, wird auf 60% begrenzt)")
    ]

    building_length = 20.0
    building_width = 12.0

    print(f"\nGebäude: {building_length}m × {building_width}m")
    print(f"{'WWR':<10} {'Beschreibung':<40} {'Perimeter-Tiefe':>15}")
    print("-" * 70)

    for wwr, desc in test_cases:
        p_depth = calc.calculate_perimeter_depth(wwr, building_length, building_width)
        print(f"{wwr*100:3.0f}%     {desc:<40} {p_depth:12.2f} m")

        # Validierung
        assert calc.P_MIN <= p_depth <= calc.P_MAX * 1.1, f"Perimeter-Tiefe außerhalb Grenzen: {p_depth}"

    print("\n✅ Adaptive Perimeter-Tiefe funktioniert!")


def test_zone_layout_creation():
    """Test: 5-Zonen-Layout-Erstellung."""
    print("\n" + "="*70)
    print("TEST 2: 5-ZONEN-LAYOUT-ERSTELLUNG")
    print("="*70)

    calc = PerimeterCalculator()

    # Erstelle Layout für ein Stockwerk
    layout = calc.create_zone_layout(
        building_length=20.0,
        building_width=12.0,
        floor_height=3.0,
        floor_number=0,  # Erdgeschoss
        wwr=0.35
    )

    print_zone_layout_summary(layout)

    # Validierungen
    assert len(layout.all_zones) == 5, "Sollte 5 Zonen haben"
    assert 0.3 <= layout.perimeter_fraction <= 0.8, "Perimeter-Fraktion unrealistisch"
    assert abs(layout.total_floor_area - (20.0 * 12.0)) < 0.1, "Gesamt-Fläche stimmt nicht"

    # Prüfe dass Kern-Zone existiert und > 0
    assert layout.core.floor_area > 0, "Kern-Zone sollte Fläche haben"

    print("✅ 5-Zonen-Layout korrekt erstellt!")


def test_multi_floor_layout():
    """Test: Multi-Floor Layout."""
    print("\n" + "="*70)
    print("TEST 3: MULTI-FLOOR LAYOUT (3 Geschosse)")
    print("="*70)

    calc = PerimeterCalculator()

    layouts = calc.create_multi_floor_layout(
        building_length=16.0,
        building_width=10.0,
        floor_height=2.8,
        num_floors=3,
        wwr=0.28
    )

    print(f"\nAnzahl Stockwerke: {len(layouts)}")

    for floor_num, layout in layouts.items():
        print(f"\nGeschoss {floor_num + 1}:")
        print(f"  Z-Koordinate: {layout.core.z_origin:.1f} m")
        print(f"  Grundfläche: {layout.total_floor_area:.1f} m²")
        print(f"  Anzahl Zonen: {len(layout.all_zones)}")

    # Validierungen
    assert len(layouts) == 3, "Sollte 3 Stockwerke haben"

    # Prüfe Z-Koordinaten
    assert layouts[0].core.z_origin == 0.0, "EG sollte bei Z=0 sein"
    assert layouts[1].core.z_origin == 2.8, "OG1 sollte bei Z=2.8 sein"
    assert layouts[2].core.z_origin == 5.6, "OG2 sollte bei Z=5.6 sein"

    print("\n✅ Multi-Floor Layout korrekt!")


def test_fenster_distribution_exact():
    """Test: Fensterverteilung mit exakten Flächen."""
    print("\n" + "="*70)
    print("TEST 4: FENSTERVERTEILUNG (Exakte Flächen)")
    print("="*70)

    dist = FensterDistribution()

    # Beispiel: Exakte Fensterflächenangaben
    fenster_data = FensterData(
        nord_m2=10.0,
        ost_m2=15.0,
        sued_m2=25.0,
        west_m2=12.0
    )

    # Wandflächen
    wall_areas = {
        "north": 60.0,
        "east": 42.0,
        "south": 60.0,
        "west": 42.0
    }

    orientation_wwr = dist.calculate_orientation_wwr(
        fenster_data,
        wall_areas,
        gebaeudetyp=GebaeudeTyp.EFH
    )

    print_window_distribution(orientation_wwr, wall_areas)

    # Validierungen
    assert 0.15 < orientation_wwr.north < 0.20, "Nord-WWR inkorrekt"
    assert 0.35 < orientation_wwr.east < 0.40, "Ost-WWR inkorrekt"
    assert 0.40 < orientation_wwr.south < 0.45, "Süd-WWR inkorrekt"

    print("✅ Exakte Fensterverteilung korrekt!")


def test_fenster_distribution_heuristic():
    """Test: Fensterverteilung mit Heuristik."""
    print("\n" + "="*70)
    print("TEST 5: FENSTERVERTEILUNG (Heuristik)")
    print("="*70)

    examples = create_example_distributions()

    print("\nHeuristische Verteilungen (30% Gesamt-WWR):\n")

    for typ, orientation_wwr in examples.items():
        print(f"{typ.value} - {FensterDistribution.HEURISTIC_DISTRIBUTIONS[typ]['description']}")
        print(f"  N: {orientation_wwr.north*100:4.1f}%  |  "
              f"E: {orientation_wwr.east*100:4.1f}%  |  "
              f"S: {orientation_wwr.south*100:4.1f}%  |  "
              f"W: {orientation_wwr.west*100:4.1f}%")

        # Validierung: Summe sollte WWR_total entsprechen (nicht 4*WWR!)
        total = orientation_wwr.north + orientation_wwr.east + orientation_wwr.south + orientation_wwr.west
        assert abs(total - 0.30) < 0.01, f"Summe ({total:.3f}) stimmt nicht für {typ}, sollte 0.30 sein"

    print("\n✅ Heuristische Verteilung korrekt!")


def test_small_building_fallback():
    """Test: Zu kleines Gebäude für 5-Zone."""
    print("\n" + "="*70)
    print("TEST 6: EDGE CASE - Zu kleines Gebäude")
    print("="*70)

    calc = PerimeterCalculator()

    # Sehr kleines Gebäude (6m × 6m)
    try:
        layout = calc.create_zone_layout(
            building_length=6.0,
            building_width=6.0,
            floor_height=2.8,
            floor_number=0,
            wwr=0.40
        )

        # Falls es funktioniert, prüfe Constraints
        print(f"Layout erstellt für 6m × 6m:")
        print(f"  Perimeter-Tiefe: {calc.calculate_perimeter_depth(0.4, 6.0, 6.0):.2f} m")
        print(f"  Kern-Fläche: {layout.core.floor_area:.2f} m²")

        assert layout.core.floor_area > 0, "Kern sollte existieren"

    except ValueError as e:
        print(f"❌ Erwarteter Fehler: {e}")
        print("→ Gebäude zu klein für 5-Zone-Modell")

    print("\n✅ Edge Case korrekt behandelt!")


def run_all_tests():
    """Führt alle Sprint 2 Tests aus."""
    print("\n" + "#"*70)
    print("# SPRINT 2 TEST-SUITE: Perimeter & Fenster")
    print("#"*70)

    try:
        test_perimeter_calculation()
        test_zone_layout_creation()
        test_multi_floor_layout()
        test_fenster_distribution_exact()
        test_fenster_distribution_heuristic()
        test_small_building_fallback()

        print("\n" + "="*70)
        print("✅ SPRINT 2: ALLE TESTS ERFOLGREICH!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FEHLGESCHLAGEN: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ FEHLER: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
