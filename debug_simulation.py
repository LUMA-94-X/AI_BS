"""Debug-Skript für Simulation-Probleme."""

import sys
from pathlib import Path

# Finde das letzte Simulationsverzeichnis
output_dir = Path("output")
sim_dirs = sorted(output_dir.glob("simulation_*"))
if not sim_dirs:
    print("❌ Keine Simulationen gefunden in output/")
    sys.exit(1)

latest_sim = sim_dirs[-1]
print(f"🔍 Analysiere: {latest_sim.name}\n")

# Check files
files = {
    "building.idf": latest_sim / "building.idf",
    "in.idf": latest_sim / "in.idf",
    "expanded.idf": latest_sim / "expanded.idf",
    "eplusout.sql": latest_sim / "eplusout.sql",
    "eplusout.err": latest_sim / "eplusout.err",
}

print("📁 Files:")
for name, path in files.items():
    if path.exists():
        size = path.stat().st_size
        print(f"  ✅ {name}: {size:,} bytes")
    else:
        print(f"  ❌ {name}: NOT FOUND")

print()

# Check expanded.idf content
expanded_idf = files["expanded.idf"]
if expanded_idf.exists():
    content = expanded_idf.read_text(encoding='utf-8', errors='ignore')

    hvactemplate_count = content.upper().count('HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM')
    zonehvac_count = content.upper().count('ZONEHVAC:IDEALLOADSAIRSYSTEM')

    print("🔧 expanded.idf Analysis:")
    print(f"  HVACTEMPLATE objects: {hvactemplate_count}")
    print(f"  ZONEHVAC objects: {zonehvac_count}")

    if hvactemplate_count > 0:
        print("  ❌ ERROR: HVACTEMPLATE still present (not expanded!)")
    elif zonehvac_count > 0:
        print("  ✅ OK: HVACTEMPLATE converted to ZONEHVAC")
    else:
        print("  ⚠️  WARNING: No HVAC objects found!")

print()

# Check SQL
sql_file = files["eplusout.sql"]
if sql_file.exists():
    import sqlite3

    conn = sqlite3.connect(str(sql_file))
    c = conn.cursor()

    # Time rows
    c.execute("SELECT COUNT(*) FROM Time")
    time_rows = c.fetchone()[0]

    # Errors
    c.execute("SELECT COUNT(*) FROM Errors")
    error_count = c.fetchone()[0]

    # Completed flag
    c.execute("SELECT Completed FROM Simulations LIMIT 1")
    completed = c.fetchone()

    print("📊 SQL Analysis:")
    print(f"  Time rows: {time_rows}")
    print(f"  Error count: {error_count}")
    print(f"  Completed: {completed[0] if completed else 'NULL'}")

    if time_rows == 0:
        print("\n❌ CRITICAL: Simulation did NOT run (0 timesteps)")
        print("   This means EnergyPlus failed during initialization\n")

        # Show errors
        c.execute("SELECT ErrorMessage FROM Errors LIMIT 10")
        print("  Top Errors:")
        for i, (msg,) in enumerate(c.fetchall(), 1):
            print(f"    {i}. {msg[:100]}")

    conn.close()

print()

# Check err file
err_file = files["eplusout.err"]
if err_file.exists():
    size = err_file.stat().st_size
    print(f"📄 eplusout.err: {size} bytes")

    if size == 0:
        print("  ❌ ERROR: err file is EMPTY!")
        print("     This is unusual - EnergyPlus should always write errors/warnings")
        print("     Possible causes:")
        print("     1. EnergyPlus crashed before writing")
        print("     2. File permissions issue")
        print("     3. EnergyPlus was not actually executed")
    else:
        content = err_file.read_text(encoding='utf-8', errors='ignore')
        severe_count = content.count('** Severe  **')
        fatal_count = content.count('**  Fatal  **')

        print(f"  Severe errors: {severe_count}")
        print(f"  Fatal errors: {fatal_count}")

        if severe_count > 0 or fatal_count > 0:
            print("\n  Last 20 lines of err file:")
            lines = content.split('\n')
            for line in lines[-20:]:
                if line.strip():
                    print(f"    {line}")

print("\n" + "="*80)
print("💡 Recommendations:")

if expanded_idf.exists():
    content = expanded_idf.read_text(encoding='utf-8', errors='ignore')
    if 'HVACTEMPLATE:ZONE' in content.upper():
        print("  1. ExpandObjects did NOT work properly")
        print("     → Check if ExpandObjects.exe is in EnergyPlus directory")
        print("     → Check runner.py logs for ExpandObjects errors")
    elif time_rows == 0:
        print("  1. expanded.idf is correct but simulation didn't run")
        print("     → Check for severe errors in IDF (missing objects, etc.)")
        print("     → Run EnergyPlus manually to see full output:")
        print(f"        energyplus -w weather.epw {expanded_idf}")
