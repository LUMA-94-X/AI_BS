# Simulation Crash Analysis - 5-Zone Workflow

## Executive Summary

Your simulation is **still crashing** (Return Code 5) during "Initializing Simulation", but we've identified and partially fixed the issues:

✅ **FIXED**: Missing thermostats (committed)
❌ **NOT FIXED**: ZONEHVAC:IDEALLOADSAIRSYSTEM field order error (in progress)

## Problem Timeline

### Your Simulation (simulation_20251111_233258)
- **Return Code**: 5 (Fatal error)
- **Duration**: <1 second
- **SQL Size**: 180 KB (expected >1 MB)
- **Error File**: Empty (0 bytes)
- **Status**: Crashes at "Initializing Simulation"

## Root Cause Analysis

### Issue #1: Missing Thermostats ✅ FIXED

**Diagnosis:**
```
- ZONEHVAC:IDEALLOADSAIRSYSTEM objects: 10 ✓
- ZONEHVAC:EQUIPMENTCONNECTIONS: 10 ✓
- ZONECONTROL:THERMOSTAT: 0 ❌❌❌
```

**Problem:** IdealLoads HVAC requires thermostats to control heating/cooling setpoints. Without thermostats, EnergyPlus doesn't know what temperature to maintain in the zones.

**Fix Applied:**
```python
# features/hvac/ideal_loads.py

# Added to _ensure_schedules():
- HeatingSetpoint schedule (20°C)
- CoolingSetpoint schedule (26°C)

# Added to _add_ideal_loads_to_zone():
- ZONECONTROL:THERMOSTAT for each zone
- THERMOSTATSETPOINT:DUALSETPOINT for each zone
```

**Status:** ✅ Committed (beee67c)

---

### Issue #2: ZONEHVAC:IDEALLOADSAIRSYSTEM Field Order Error ❌ IN PROGRESS

**Diagnosis:**

When testing the thermostat fix, discovered that the ZONEHVAC:IDEALLOADSAIRSYSTEM object has fields in the wrong order:

```
** Severe  ** cooling_sensible_heat_ratio - Got "None" (should be blank or numeric)
** Severe  ** heat_recovery_type - Got "0.65" (should be "None" enum)
** Severe  ** maximum_sensible_heating_capacity - Got "NoLimit" (wrong position)
** Severe  ** maximum_total_cooling_capacity - Got "AlwaysOn" (wrong position)
```

**What this means:** The fields are being shifted around. Values that should go in one field are ending up in different fields. This is a critical error in how the object is being created.

**Root Cause:** The `_add_ideal_loads_to_zone()` method in `ideal_loads.py` is using `idf.newidfobject()` with named parameters, but something is causing the field order to get scrambled when writing to the IDF file.

**Where the bug is:**
```python
# features/hvac/ideal_loads.py:174-201
idf.newidfobject(
    "ZONEHVAC:IDEALLOADSAIRSYSTEM",
    Name=f"{zone_name}_IdealLoads",
    Zone_Supply_Air_Node_Name=f"{zone_name}_Supply_Node",
    # ... more fields ...
    Sensible_Heat_Recovery_Effectiveness=0.70,   # ← This ends up in wrong field!
    Latent_Heat_Recovery_Effectiveness=0.65,     # ← This ends up in wrong field!
)
```

**Status:** ❌ Not fixed yet - needs investigation

---

## Test Results

### Test 1: Path Conversion ✅ PASS
```bash
$ python3 test_path_conversion.py
✅ SUCCESS: IDD file found!
```

### Test 2: Thermostat Addition ✅ PASS
```bash
$ python3 test_hvac_thermostat_fix.py
✅ TEST PASSED: All zones have thermostats and setpoints!
  Zones: 10
  Thermostats: 10 ✓
  Setpoints: 10 ✓
```

### Test 3: Simulation with Thermostats ❌ FAIL
```bash
$ python3 test_simulation_with_thermostats.py
❌ FAILED: Simulation did not produce expected results
   Return code: 5
   Time rows: 0 (expected >8000)

Reason: ZONEHVAC:IDEALLOADSAIRSYSTEM field order errors
```

### Test 4: Minimal IDF ❌ FAIL
```bash
$ python3 test_minimal_idf.py
❌ FAILED: Return code 1

** Severe  ** 15 field order errors in ZONEHVAC:IDEALLOADSAIRSYSTEM
```

---

## What Works vs. What Doesn't

### ✅ What's Working:
1. **IDF Version 25.1** - Matches EnergyPlus V25-1-0
2. **Path Conversion** - WSL ↔ Windows paths work correctly
3. **5-Zone Geometry** - 10 zones, 60 surfaces, 8 windows created
4. **SIMULATIONCONTROL** - Sizing disabled, annual simulation enabled
5. **Thermostats** - Now being created for all zones
6. **Schedules** - HeatingSetpoint, CoolingSetpoint, AlwaysOn

### ❌ What's Broken:
1. **ZONEHVAC:IDEALLOADSAIRSYSTEM** - Field order errors prevent simulation
2. **Simulation execution** - Crashes before any timesteps run
3. **Results** - No data being written (Time table empty)

---

## Next Steps

### OPTION 1: Fix Field Order in ideal_loads.py (Recommended)

Need to debug why `idf.newidfobject()` is producing incorrect field order. Possible solutions:

1. **Check eppy version** - May be a bug in eppy library
2. **Use field indices instead of names** - More reliable but less readable
3. **Create IDF text directly** - Bypass eppy for this object

### OPTION 2: Use Simple HVACTemplate Objects

Instead of creating ZONEHVAC:IDEALLOADSAIRSYSTEM directly, use:
```
HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM
```

These are simpler objects that EnergyPlus's ExpandObjects program converts to full HVAC objects. This is how the old code worked.

### OPTION 3: Copy from Working Example

Find a working EnergyPlus example IDF with IdealLoads, extract the exact object definition, and use that template.

---

## Files Modified

| File | Status | Description |
|------|--------|-------------|
| `features/hvac/ideal_loads.py` | ✅ Committed | Added thermostats + setpoint schedules |
| `features/geometrie/generators/five_zone_generator.py` | ✅ Committed | Fixed version 25.1, disabled sizing |
| `core/config.py` | ✅ Committed | WSL↔Windows path conversion |
| `features/simulation/runner.py` | ✅ Committed | WSL path conversion for EnergyPlus |

---

## How to Test

### Quick Test (After Fix):
```bash
# Apply HVAC and test
python3 test_hvac_thermostat_fix.py
python3 test_simulation_with_thermostats.py
```

### Full Workflow Test:
```bash
# In Windows PowerShell or WSL:
streamlit run features/web_ui/Start.py

# Then:
1. Go to Energieausweis page
2. Enter building data
3. Go to HVAC page → Apply IdealLoads
4. Go to Simulation page → Run simulation
5. Check: Runtime should be 30-60 seconds (not <1s!)
6. Check: SQL file should be >1 MB
```

---

## Debugging Commands

```bash
# Check IDF for thermostat objects
grep -i "ZONECONTROL:THERMOSTAT" output/simulation_*/building.idf

# Check IDF for HVAC objects
grep -A 20 "ZONEHVAC:IDEALLOADSAIRSYSTEM" output/simulation_*/building.idf

# Analyze SQL database
python3 check_sql.py output/simulation_*/eplusout.sql

# Read errors from SQL
python3 read_errors.py output/simulation_*/eplusout.sql

# Manual EnergyPlus run with full output
python3 test_manual_simulation.py
```

---

## Critical Insight

**The simulation was NEVER running successfully - it has been crashing since the beginning!**

The symptoms we saw:
- 0.6-0.7 second runtime ❌
- 180 KB SQL file ❌
- All energy values = 0 ❌
- Empty error file ❌

**These are all symptoms of EnergyPlus crashing during initialization, NOT a successful simulation with no loads.**

A successful annual simulation would show:
- 30-60 second runtime ✓
- >1 MB SQL file ✓
- 8760+ time rows ✓
- Real energy data ✓

---

## Recommendation

**DO NOT use the UI workflow yet!** The HVAC application is broken.

**Next action:** Debug the ZONEHVAC:IDEALLOADSAIRSYSTEM field order issue in `ideal_loads.py`. Once that's fixed, the complete workflow should work.

---

## Questions to Investigate

1. Why is `idf.newidfobject()` producing wrong field order?
2. Is this a known issue with eppy library?
3. Should we use HVACTEMPLATE objects instead of direct ZONEHVAC objects?
4. Can we validate field order before saving IDF?

---

**Last Updated**: 2025-11-11 23:45
**Status**: 🔴 Simulation still broken - Field order issue unresolved
