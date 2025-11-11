#!/usr/bin/env python3
"""Test simulation with thermostats."""

import subprocess
from pathlib import Path

# Paths
idf_file = Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/building_with_thermostats.idf")
weather_file = Path("/mnt/c/Users/lugma/source/repos/AI_BS/data/weather/example.epw")
output_dir = Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/test_with_thermostats")

# Create output dir
output_dir.mkdir(parents=True, exist_ok=True)

# Convert paths to Windows format
result_idf = subprocess.run(['wslpath', '-w', str(idf_file.absolute())],
                           capture_output=True, text=True)
result_weather = subprocess.run(['wslpath', '-w', str(weather_file.absolute())],
                               capture_output=True, text=True)
result_output = subprocess.run(['wslpath', '-w', str(output_dir.absolute())],
                              capture_output=True, text=True)

idf_win = result_idf.stdout.strip()
weather_win = result_weather.stdout.strip()
output_win = result_output.stdout.strip()

print("=" * 80)
print("SIMULATION TEST WITH THERMOSTATS")
print("=" * 80)
print(f"IDF:     {idf_win}")
print(f"Weather: {weather_win}")
print(f"Output:  {output_win}")
print("=" * 80)

# Run EnergyPlus
cmd = [
    "/mnt/c/EnergyPlusV25-1-0/energyplus.exe",
    "--weather", weather_win,
    "--output-directory", output_win,
    "--output-prefix", "sim",
    idf_win
]

print("\nRunning EnergyPlus...")
print("(This should take 30-60 seconds for annual simulation)")
print()

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=180,
    cwd=str(output_dir.absolute())
)

print(f"Return Code: {result.returncode}")

# Check output files
print("\n" + "=" * 80)
print("OUTPUT FILES:")
print("=" * 80)

for file in sorted(output_dir.glob("*")):
    size = file.stat().st_size
    print(f"  {file.name}: {size:,} bytes")

# Check SQL database
sql_file = output_dir / "simout.sql"
if sql_file.exists():
    import sqlite3
    conn = sqlite3.connect(str(sql_file))
    cursor = conn.cursor()

    # Count time rows
    cursor.execute("SELECT COUNT(*) FROM Time")
    time_count = cursor.fetchone()[0]

    # Count data rows
    cursor.execute("SELECT COUNT(*) FROM ReportData")
    data_count = cursor.fetchone()[0]

    # Count errors
    cursor.execute("SELECT COUNT(*) FROM Errors WHERE ErrorType > 1")
    error_count = cursor.fetchone()[0]

    conn.close()

    print("\n" + "=" * 80)
    print("SQL DATABASE ANALYSIS:")
    print("=" * 80)
    print(f"  Time rows: {time_count:,}")
    print(f"  Data rows: {data_count:,}")
    print(f"  Fatal Errors: {error_count}")

    sql_size_mb = sql_file.stat().st_size / 1_000_000

    print("\n" + "=" * 80)
    if result.returncode == 0 and time_count > 0 and sql_size_mb > 1.0:
        print("✅ SUCCESS: Simulation completed with real data!")
        print(f"   SQL file size: {sql_size_mb:.2f} MB")
        print(f"   Timesteps: {time_count:,}")
        print(f"   Data points: {data_count:,}")
        print("=" * 80)
    else:
        print("❌ FAILED: Simulation did not produce expected results")
        print(f"   Return code: {result.returncode}")
        print(f"   SQL size: {sql_size_mb:.2f} MB (expected >1 MB)")
        print(f"   Time rows: {time_count:,} (expected >8000)")
        print("\n   STDOUT:")
        print(result.stdout)
        print("=" * 80)
