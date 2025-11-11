"""Tests für Geometrie-Solver."""

import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

from features.geometrie.models.energieausweis_input import (
    create_example_efh,
    create_example_mfh,
    EnergieausweisInput,
    FensterData
)
from features.geometrie.utils.geometry_solver import (
    GeometrySolver,
    print_solution_summary
)


def test_exact_solution():
    """Test: Exakte Lösung mit vollständigen Hüllflächen-Daten."""
    print("\n" + "="*70)
    print("TEST 1: EXAKTE LÖSUNG (Vollständige Hüllflächen-Daten)")
    print("="*70)

    # Nutze Beispiel-EFH mit allen Daten
    ea_data = create_example_efh()

    solver = GeometrySolver()
    solution = solver.solve(ea_data)

    print_solution_summary(solution)

    # Validierungen
    assert solution.method.value == "exact", "Sollte exakte Methode verwenden"
    assert solution.confidence > 0.9, "Konfidenz sollte hoch sein"
    assert 2.5 < solution.floor_height < 3.5, "Geschosshöhe unrealistisch"
    assert solution.num_floors == 2, "Sollte 2 Geschosse haben"

    print("✅ Test bestanden!")


def test_heuristic_solution():
    """Test: Heuristische Lösung mit Teil-Informationen."""
    print("\n" + "="*70)
    print("TEST 2: HEURISTISCHE LÖSUNG (Nur Dachfläche gegeben)")
    print("="*70)

    # Erstelle Input ohne Wandfläche
    ea_data = EnergieausweisInput(
        nettoflaeche_m2=200.0,
        dachflaeche_m2=110.0,  # Gegeben
        # wandflaeche_m2 fehlt!
        anzahl_geschosse=2,
        geschosshoehe_m=2.9,
        u_wert_wand=0.30,
        u_wert_dach=0.22,
        u_wert_boden=0.40,
        u_wert_fenster=1.4,
        fenster=FensterData(window_wall_ratio=0.35),
        aspect_ratio_hint=1.4
    )

    solver = GeometrySolver()
    solution = solver.solve(ea_data)

    print_solution_summary(solution)

    # Validierungen
    assert solution.method.value == "heuristic", "Sollte heuristische Methode verwenden"
    assert 0.5 < solution.confidence < 0.9, "Konfidenz sollte mittel sein"
    assert solution.floor_area > 100, "Grundfläche zu klein"

    print("✅ Test bestanden!")


def test_fallback_solution():
    """Test: Fallback-Lösung mit minimalen Daten."""
    print("\n" + "="*70)
    print("TEST 3: FALLBACK-LÖSUNG (Nur Nettofläche)")
    print("="*70)

    # Nur Pflichtfelder
    ea_data = EnergieausweisInput(
        nettoflaeche_m2=500.0,
        anzahl_geschosse=3,
        u_wert_wand=0.45,
        u_wert_dach=0.30,
        u_wert_boden=0.50,
        u_wert_fenster=2.0,
        # Keine Hüllflächen-Daten!
    )

    solver = GeometrySolver()
    solution = solver.solve(ea_data)

    print_solution_summary(solution)

    # Validierungen
    assert solution.method.value == "fallback", "Sollte Fallback verwenden"
    assert solution.confidence < 0.7, "Konfidenz sollte niedrig sein"
    assert len(solution.warnings) > 0, "Sollte Warnungen geben"

    print("✅ Test bestanden!")


def test_mfh_example():
    """Test: Realistisches MFH-Beispiel."""
    print("\n" + "="*70)
    print("TEST 4: MEHRFAMILIENHAUS (Realistisches Beispiel)")
    print("="*70)

    ea_data = create_example_mfh()

    solver = GeometrySolver()
    solution = solver.solve(ea_data)

    print_solution_summary(solution)

    # Validierungen
    assert solution.total_floor_area > 700, "MFH sollte > 700m² haben"
    assert solution.num_floors == 3, "Sollte 3 Geschosse haben"
    assert 0.3 < solution.av_ratio < 1.0, "A/V-Verhältnis unrealistisch"

    print("✅ Test bestanden!")


def test_edge_cases():
    """Test: Grenzfälle und Validierung."""
    print("\n" + "="*70)
    print("TEST 5: GRENZFÄLLE")
    print("="*70)

    # Sehr kompaktes Gebäude (würfelförmig)
    print("\n5a) Sehr kompaktes Gebäude (AR = 1.0):")
    ea_data_compact = EnergieausweisInput(
        nettoflaeche_m2=240.0,
        dachflaeche_m2=100.0,
        bodenflaeche_m2=100.0,
        wandflaeche_m2=120.0,
        anzahl_geschosse=2,
        u_wert_wand=0.25,
        u_wert_dach=0.20,
        u_wert_boden=0.35,
        u_wert_fenster=1.1,
        aspect_ratio_hint=1.0  # Quadratisch
    )

    solver = GeometrySolver()
    solution = solver.solve(ea_data_compact)
    print(f"  L/W = {solution.aspect_ratio:.2f} (sollte ~1.0 sein)")
    print(f"  A/V = {solution.av_ratio:.2f}")
    assert 0.9 < solution.aspect_ratio < 1.1, "Sollte fast quadratisch sein"

    # Langgestrecktes Gebäude
    print("\n5b) Langgestrecktes Gebäude (AR = 3.0):")
    ea_data_long = EnergieausweisInput(
        nettoflaeche_m2=300.0,
        dachflaeche_m2=150.0,
        bodenflaeche_m2=150.0,
        wandflaeche_m2=280.0,
        anzahl_geschosse=2,
        u_wert_wand=0.30,
        u_wert_dach=0.22,
        u_wert_boden=0.40,
        u_wert_fenster=1.3,
        aspect_ratio_hint=3.0  # Sehr lang
    )

    solution = solver.solve(ea_data_long)
    print(f"  L/W = {solution.aspect_ratio:.2f} (sollte ~3.0 sein)")
    print(f"  A/V = {solution.av_ratio:.2f} (wird höher sein)")
    assert 2.8 < solution.aspect_ratio < 3.2, "Sollte langgestreckt sein"
    # AR=3.0 ist noch akzeptabel (Reihenhaus, langes Bürogebäude)
    # Warnung erst bei AR > 4.0

    print("\n✅ Alle Grenzfälle bestanden!")


def run_all_tests():
    """Führt alle Tests aus."""
    print("\n" + "#"*70)
    print("# GEOMETRIE-SOLVER TEST-SUITE")
    print("#"*70)

    try:
        test_exact_solution()
        test_heuristic_solution()
        test_fallback_solution()
        test_mfh_example()
        test_edge_cases()

        print("\n" + "="*70)
        print("✅ ALLE TESTS ERFOLGREICH!")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FEHLGESCHLAGEN: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ FEHLER: {e}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
