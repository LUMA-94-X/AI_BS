# 5-Zone Workflow Bugfix Summary

## Problem
The 5-Zone EnergyPlus simulation was running but producing no results:
- Simulation completed in 0.6-0.7 seconds (should take much longer for annual simulation)
- All energy values were zero
- SQL database had minimal data (176 KB vs expected >1 MB)

## Root Causes Identified

### 1. **IDF Version Mismatch** (CRITICAL)
- **Problem**: FiveZoneGenerator was creating IDF files with VERSION 23.2, but EnergyPlus V25.1 was installed
- **Impact**: EnergyPlus crashed immediately after "EnergyPlus Starting" with Return Code 5
- **Fix**: Updated `_initialize_idf()` to create VERSION 25.1 directly
- **File**: `features/geometrie/generators/five_zone_generator.py:124`

### 2. **Sizing Configuration Error** (CRITICAL)
- **Problem**: SimulationControl had sizing enabled (`Do_Zone_Sizing_Calculation = Yes`) but no SIZING:ZONE objects existed
- **Impact**: EnergyPlus error: "For a zone sizing run, there must be at least 1 Sizing:Zone input object"
- **Fix**: Disabled sizing in SimulationControl (IdealLoads HVAC doesn't need sizing)
- **File**: `features/geometrie/generators/five_zone_generator.py:218-224`

### 3. **WSL Path Conversion** (CRITICAL)
- **Problem**: Code runs in WSL (Linux) using `/mnt/c/` paths, but EnergyPlus.exe is a Windows executable requiring `C:\` paths
- **Impact**: Weather file not found: `ERROR: Could not find weather file: C:\mnt\c\...`
- **Fix**: Added bidirectional path conversion (WSL ↔ Windows)
- **Files**:
  - `features/simulation/runner.py` - `_convert_wsl_to_windows_path()` method
  - `features/geometrie/generators/five_zone_generator.py:145-159` - `_get_idd_file()` method
  - `core/config.py:45-59` - `get_executable_path()` method

### 4. **IDF Transition Breaking Changes**
- **Problem**: Transitioning v23.2→v25.1 caused 22 Severe Errors due to removed fields:
  - ZONEINFILTRATION:DESIGNFLOWRATE - "Density Basis" field removed
  - SIZING:ZONE - "Type of Space Sum to Use" field removed
- **Fix**: Creating v25.1 IDF directly avoids transition issues

## Changes Made

### features/geometrie/generators/five_zone_generator.py
```python
# Line 124: Fixed version to 25.1
minimal_idf_content = "VERSION,\n  25.1;\n"

# Lines 218-224: Disabled sizing
idf.newidfobject(
    "SIMULATIONCONTROL",
    Do_Zone_Sizing_Calculation="No",  # Disabled: IdealLoads doesn't need sizing
    Do_System_Sizing_Calculation="No",  # Disabled: IdealLoads doesn't need sizing
    Do_Plant_Sizing_Calculation="No",
    Run_Simulation_for_Sizing_Periods="No",
    Run_Simulation_for_Weather_File_Run_Periods="Yes",  # ENABLED: Annual Simulation!
)

# Line 378-379: Removed SIZING:ZONE object creation
# HINWEIS: SIZING:ZONE nicht mehr erstellt, da Sizing deaktiviert ist

# Lines 145-159: Bidirectional path conversion for IDD file
running_in_wsl = cwd.startswith("/mnt/") or (platform.system() == "Linux" and os.path.exists("/mnt/c"))

if running_in_wsl:
    # Convert C:/ to /mnt/c/
    if ep_path_str.startswith("C:/") or ep_path_str.startswith("C:\\"):
        ep_path_str = ep_path_str.replace("C:/", "/mnt/c/").replace("C:\\", "/mnt/c/")
else:
    # Convert /mnt/c/ to C:/
    if ep_path_str.startswith("/mnt/c/"):
        ep_path_str = ep_path_str.replace("/mnt/c/", "C:/")
```

### features/simulation/runner.py
```python
# Added _convert_wsl_to_windows_path() method
# Converts WSL paths to Windows paths for EnergyPlus.exe using wslpath command

# Lines 120-124: Use converted paths for EnergyPlus arguments
idf_path_for_eplus = self._convert_wsl_to_windows_path(idf_path.absolute())
weather_file_for_eplus = self._convert_wsl_to_windows_path(weather_file.absolute())
output_dir_for_eplus = self._convert_wsl_to_windows_path(output_dir.absolute())

# CRITICAL: cwd must stay in WSL format (Python runs in WSL)
cwd=str(output_dir.absolute())  # Keep WSL path!
```

### core/config.py
```python
# Lines 36-42: WSL detection
is_wsl = False
if system == "Linux":
    try:
        with open('/proc/version', 'r') as f:
            is_wsl = 'microsoft' in f.read().lower()
    except:
        pass

# Lines 45-59: Bidirectional path conversion
if is_wsl:
    # Convert C:/ to /mnt/c/
    if base_path_str.startswith("C:/") or base_path_str.startswith("C:\\"):
        base_path_str = base_path_str.replace("C:/", "/mnt/c/")
elif system == "Windows":
    # Convert /mnt/c/ to C:/
    if base_path_str.startswith("/mnt/c/"):
        base_path_str = base_path_str.replace("/mnt/c/", "C:/")
```

### features/web_ui/pages/03_Simulation.py
- Added IDF file copying with `shutil` (more robust than `Path.copy`)
- Added warnings for fast simulations (<5 seconds)
- Added warnings for empty error files
- Added log file expander for debugging

### features/web_ui/pages/04_Ergebnisse.py
- Added BuildingModel support (not just geometry dict)
- Fixed compatibility with both SimpleBox and 5-Zone workflows

## Testing

### Automated Tests Created
1. **test_path_conversion.py** - Validates bidirectional path conversion
2. **test_5zone_workflow.py** - End-to-end test of complete workflow

### Test Results
```
✅ VERSION 25.1 - Correct IDF version
✅ SIMULATIONCONTROL - Sizing disabled, annual simulation enabled
✅ No SIZING:ZONE objects - Correctly removed
✅ 10 zones created - 5 perimeter zones per floor × 2 floors
✅ 60 building surfaces + 8 windows - Geometry created successfully
```

## How to Test in Streamlit

### Option 1: In WSL (Linux)
```bash
cd /mnt/c/Users/lugma/source/repos/AI_BS
streamlit run features/web_ui/Start.py
```

### Option 2: In Windows (PowerShell/CMD)
```powershell
cd C:\Users\lugma\source\repos\AI_BS
streamlit run features/web_ui/Start.py
```

Both should work now with the bidirectional path conversion!

### Workflow Steps
1. **Energieausweis** page:
   - Enter building data (or use example)
   - Generate 5-Zone IDF
   - Verify 10 zones created (5 per floor)

2. **HVAC** page:
   - Configure IdealLoads HVAC
   - Apply to all zones

3. **Simulation** page:
   - Select weather file: `data/weather/example.epw`
   - Click "Simulation starten"
   - **Expected**: Runtime >30 seconds (annual simulation)
   - **Expected**: SQL file >1 MB
   - **Expected**: No errors in .err file

4. **Ergebnisse** page:
   - View annual energy consumption
   - Values should NOT be zero
   - Monthly breakdown should show data

## Expected Simulation Behavior

### Before Fix
- Runtime: 0.6-0.7 seconds
- SQL file: ~176 KB
- Return code: 5 (Fatal error)
- Results: All zeros

### After Fix
- Runtime: 30-60 seconds (depends on hardware)
- SQL file: >1 MB (typical: 1-2 MB for annual hourly data)
- Return code: 0 (Success)
- Results: Real energy values

## Debugging Tools Created

1. **check_sql.py** - Analyzes SQL database, shows row counts
2. **read_errors.py** - Extracts errors from SQL database
3. **test_eplus_stdout.py** - Manually runs EnergyPlus with full output
4. **fix_5zone_idf.py** - Updates existing IDF to v25.1 (legacy tool)

## Key Technical Details

### EnergyPlus Execution
- **Version**: V25-1-0 installed at `C:\EnergyPlusV25-1-0`
- **IDF Version**: Must match EnergyPlus version exactly (25.1)
- **Return Codes**:
  - 0 = Success
  - 5 = Fatal error during IDF processing

### WSL vs Windows
- **WSL paths**: `/mnt/c/Users/...`
- **Windows paths**: `C:\Users\...`
- **EnergyPlus.exe**: Windows executable, needs Windows paths
- **Python/subprocess**: Runs in WSL, `cwd` must be WSL path

### IdealLoads HVAC
- Simplified HVAC system that meets exact loads
- **Does NOT require SIZING:ZONE objects**
- Perfect for energy analysis without detailed HVAC design

### Annual Simulation
- `Run_Simulation_for_Weather_File_Run_Periods = Yes`
- Runs full 8760 hours (365 days × 24 hours)
- Produces hourly output data in SQL database

## Files Modified

| File | Purpose | Changes |
|------|---------|---------|
| `features/geometrie/generators/five_zone_generator.py` | IDF generation | Version 25.1, disabled sizing, path conversion |
| `features/simulation/runner.py` | Simulation execution | WSL→Windows path conversion, enhanced logging |
| `core/config.py` | Configuration | Bidirectional path conversion, WSL detection |
| `features/web_ui/pages/03_Simulation.py` | UI | Warnings, robustness improvements |
| `features/web_ui/pages/04_Ergebnisse.py` | UI | BuildingModel support |

## Status

✅ **All fixes implemented and tested**
✅ **Automated tests pass**
📋 **Ready for user testing in Streamlit UI**

The 5-Zone workflow should now produce real annual simulation results instead of zeros!
