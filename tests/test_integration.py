"""Integrations-Test für den kompletten Workflow."""

import sys
from pathlib import Path
import tempfile
import pytest

# Projekt-Root zum Python-Path hinzufügen
projekt_root = Path(__file__).parent.parent
sys.path.insert(0, str(projekt_root))

from features.geometrie.box_generator import SimpleBoxGenerator, BuildingGeometry
from features.hvac.ideal_loads import create_building_with_hvac
from features.simulation.runner import EnergyPlusRunner
from features.auswertung.kpi_rechner import KennzahlenRechner
from features.auswertung.sql_parser import EnergyPlusSQLParser
from features.auswertung.visualisierung import ErgebnisVisualisierer


@pytest.fixture
def test_geometrie():
    """Test-Geometrie für Simulationen."""
    return BuildingGeometry(
        length=10.0,
        width=8.0,
        height=3.0,
        num_floors=1,
        window_wall_ratio=0.2,
        orientation=0.0,
    )


@pytest.fixture
def test_output_dir():
    """Temporäres Ausgabeverzeichnis."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_complete_workflow(test_geometrie, test_output_dir):
    """Teste den kompletten Workflow von Geometrie bis Auswertung."""

    # Nur wenn EnergyPlus verfügbar ist
    try:
        # 1. Gebäudemodell erstellen
        generator = SimpleBoxGenerator()
        idf_path = test_output_dir / "test_building.idf"
        idf = generator.create_model(test_geometrie, idf_path)

        assert idf_path.exists(), "IDF-Datei wurde nicht erstellt"

        # 2. HVAC hinzufügen
        idf = create_building_with_hvac(idf, "ideal_loads")
        idf.save(str(idf_path))

        # 3. Simulation ausführen
        runner = EnergyPlusRunner()

        # Prüfe ob Wetterdatei existiert
        weather_file = projekt_root / "data" / "weather" / "example.epw"
        if not weather_file.exists():
            pytest.skip("Wetterdatei nicht gefunden")

        result = runner.run_simulation(
            idf_path=idf_path,
            weather_file=weather_file,
            output_dir=test_output_dir / "simulation",
        )

        assert result.success, f"Simulation fehlgeschlagen: {result.error_message}"
        assert result.sql_file is not None, "SQL-Datei nicht gefunden"
        assert result.sql_file.exists(), "SQL-Datei existiert nicht"

        # 4. Ergebnisse parsen
        parser = EnergyPlusSQLParser(result.sql_file)
        ergebnis = parser.get_ergebnis_uebersicht()

        assert ergebnis.gesamtenergiebedarf_kwh > 0, "Gesamtenergiebedarf sollte > 0 sein"
        assert ergebnis.mittlere_raumtemperatur_c > 0, "Temperatur sollte > 0 sein"

        # 5. KPIs berechnen
        rechner = KennzahlenRechner(test_geometrie.total_floor_area)
        kennzahlen = rechner.berechne_kennzahlen(sql_file=result.sql_file)

        assert kennzahlen.effizienzklasse in ['A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'], \
            "Ungültige Effizienzklasse"
        assert kennzahlen.energiekennzahl_kwh_m2a > 0, "Energiekennzahl sollte > 0 sein"

        # 6. Visualisierung erstellen
        viz = ErgebnisVisualisierer()
        fig = viz.erstelle_energiebilanz_chart(kennzahlen)
        assert fig is not None, "Chart sollte erstellt werden"

        print(f"\n[OK] Integration-Test erfolgreich!")
        print(f"   Effizienzklasse: {kennzahlen.effizienzklasse}")
        print(f"   Energiekennzahl: {kennzahlen.energiekennzahl_kwh_m2a:.1f} kWh/m2a")

    except FileNotFoundError as e:
        pytest.skip(f"EnergyPlus nicht verfügbar: {e}")


def test_geometry_validation():
    """Teste Geometrie-Validierung."""

    # Gültige Geometrie
    geom = BuildingGeometry(length=10, width=8, height=3)
    assert geom.length == 10

    # Ungültige Geometrie
    with pytest.raises(ValueError):
        BuildingGeometry(length=-5, width=8, height=3)

    with pytest.raises(ValueError):
        BuildingGeometry(length=10, width=8, height=3, num_floors=0)

    with pytest.raises(ValueError):
        BuildingGeometry(length=10, width=8, height=3, window_wall_ratio=1.5)


def test_kpi_calculation():
    """Teste KPI-Berechnung ohne Simulation."""
    from features.auswertung.sql_parser import ErgebnisUebersicht

    # Mock-Ergebnisse
    ergebnis = ErgebnisUebersicht(
        gesamtenergiebedarf_kwh=5000,
        heizbedarf_kwh=3000,
        kuehlbedarf_kwh=1500,
        beleuchtung_kwh=300,
        geraete_kwh=200,
        spitzenlast_heizung_kw=15,
        spitzenlast_kuehlung_kw=10,
        mittlere_raumtemperatur_c=22,
        min_raumtemperatur_c=20,
        max_raumtemperatur_c=26,
    )

    rechner = KennzahlenRechner(nettoflaeche_m2=100)
    kennzahlen = rechner.berechne_kennzahlen(ergebnisse=ergebnis)

    assert kennzahlen.energiekennzahl_kwh_m2a == 50.0  # 5000 / 100
    assert kennzahlen.heizkennzahl_kwh_m2a == 30.0     # 3000 / 100
    assert kennzahlen.effizienzklasse == 'A'           # 50 kWh/m²a -> Klasse A
    assert kennzahlen.thermische_behaglichkeit == "Gut"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
