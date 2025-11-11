#!/usr/bin/env python3
"""Test EnergyPlus and capture stdout/stderr."""

import subprocess
from pathlib import Path

# Paths (Windows format for EnergyPlus.exe)
energyplus_exe = Path("/mnt/c/EnergyPlusV25-1-0/energyplus.exe")
idf_file = "C:\\Users\\lugma\\source\\repos\\AI_BS\\output\\energieausweis\\gebaeude_5zone.idf"
weather_file = "C:\\Users\\lugma\\source\\repos\\AI_BS\\data\\weather\\example.epw"
output_dir = "C:\\Users\\lugma\\source\\repos\\AI_BS\\output\\test_stdout"

# Create output dir
Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/test_stdout").mkdir(parents=True, exist_ok=True)

# Build command
cmd = [
    str(energyplus_exe),
    "--weather", weather_file,
    "--output-directory", output_dir,
    "--output-prefix", "eplus",
    idf_file,
]

print("="*80)
print("RUNNING ENERGYPLUS WITH FULL OUTPUT CAPTURE")
print("="*80)
print(f"Command: {' '.join(cmd)}")
print("="*80)
print()

# Run with output capture
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=120,
    cwd="/mnt/c/Users/lugma/source/repos/AI_BS/output/test_stdout"
)

print("="*80)
print("RETURN CODE:", result.returncode)
print("="*80)
print()

print("="*80)
print("STDOUT:")
print("="*80)
print(result.stdout)
print()

print("="*80)
print("STDERR:")
print("="*80)
print(result.stderr)
print()

# Check output files
output_path = Path("/mnt/c/Users/lugma/source/repos/AI_BS/output/test_stdout")
err_file = output_path / "eplusout.err"
sql_file = output_path / "eplusout.sql"

print("="*80)
print("OUTPUT FILES:")
print("="*80)
if err_file.exists():
    err_size = err_file.stat().st_size
    print(f"eplusout.err: {err_size:,} bytes")
    if err_size > 0:
        print("\nFirst 50 lines of err file:")
        with open(err_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= 50:
                    break
                print(f"  {line.rstrip()}")
else:
    print("eplusout.err: NOT FOUND")

if sql_file.exists():
    sql_size = sql_file.stat().st_size
    print(f"\neplusout.sql: {sql_size:,} bytes")
else:
    print("\neplusout.sql: NOT FOUND")

print()
print("="*80)
print("DONE")
print("="*80)
