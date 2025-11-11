#!/usr/bin/env python3
"""Manually run EnergyPlus simulation to capture full output."""

import subprocess
from pathlib import Path

# Paths
idf_file = Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/simulation_20251111_233258/building.idf")
weather_file = Path("/mnt/c/Users/lugma/source/repos/AI_BS/data/weather/example.epw")
output_dir = Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/test_manual")

# Create output dir
output_dir.mkdir(parents=True, exist_ok=True)

# Convert paths to Windows format using wslpath
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
print("MANUAL ENERGYPLUS RUN")
print("=" * 80)
print(f"IDF (WSL):     {idf_file}")
print(f"IDF (Windows): {idf_win}")
print(f"Weather (WSL):     {weather_file}")
print(f"Weather (Windows): {weather_win}")
print(f"Output (WSL):     {output_dir}")
print(f"Output (Windows): {output_win}")
print("=" * 80)

# Run EnergyPlus
cmd = [
    "/mnt/c/EnergyPlusV25-1-0/energyplus.exe",
    "--weather", weather_win,
    "--output-directory", output_win,
    "--output-prefix", "manual",
    idf_win
]

print("\nCommand:")
print(" ".join(cmd))
print("\n" + "=" * 80)
print("RUNNING ENERGYPLUS...")
print("=" * 80)

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=120,
    cwd=str(output_dir.absolute())
)

print(f"\nReturn Code: {result.returncode}")
print("\n" + "=" * 80)
print("STDOUT:")
print("=" * 80)
print(result.stdout)

print("\n" + "=" * 80)
print("STDERR:")
print("=" * 80)
print(result.stderr)

print("\n" + "=" * 80)
print("OUTPUT FILES:")
print("=" * 80)

for file in sorted(output_dir.glob("*")):
    size = file.stat().st_size
    print(f"  {file.name}: {size:,} bytes")

print("\n" + "=" * 80)
