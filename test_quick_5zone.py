#!/usr/bin/env python3
"""Quick test: 5-Zone SINGLE FLOOR"""
from pathlib import Path
from features.geometrie.generators.five_zone_generator import FiveZoneGenerator
from features.geometrie.models.energieausweis_input import EnergieausweisInput, FensterData, GebaeudeTyp

print("Testing 5-Zone SINGLE FLOOR...")

ea_data = EnergieausweisInput(
    nettoflaeche_m2=300,  # Single floor
    anzahl_geschosse=1,  # SINGLE FLOOR
    geschosshoehe_m=3.0,
    u_wert_wand=0.5,
    u_wert_dach=0.4,
    u_wert_boden=0.6,
    u_wert_fenster=2.5,
    fenster=FensterData(window_wall_ratio=0.3),
    gebaeudetyp=GebaeudeTyp.NWG,
)

generator = FiveZoneGenerator()
output_path = Path("test_quick_5zone.idf")

idf = generator.create_from_explicit_dimensions(
    building_length=20.0,
    building_width=15.0,
    floor_height=3.0,
    num_floors=1,  # SINGLE FLOOR!
    ea_data=ea_data,
    output_path=output_path  # Pass output_path so the fix is applied
)

print(f"✅ Created: {output_path}")
print("Now test with simulation...")

from features.simulation.runner import EnergyPlusRunner

runner = EnergyPlusRunner()
result = runner.run_simulation(
    idf_path=output_path,
    weather_file=Path("data/weather/example.epw"),
    output_dir=Path("test_quick_5zone_sim"),
    output_prefix="quick5",
)

print(f"\nResult: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
print(f"Execution Time: {result.execution_time:.2f}s")

if result.sql_file and result.sql_file.exists():
    import sqlite3
    conn = sqlite3.connect(str(result.sql_file))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Time")
    time_count = cursor.fetchone()[0]
    conn.close()
    print(f"Timesteps: {time_count:,}")
