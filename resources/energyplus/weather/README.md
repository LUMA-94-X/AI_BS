# 🌦️ Weather Data (EPW Files)

EnergyPlus Weather Format (EPW) files for building simulations.

## 📁 Organization

Weather files are organized by country in subdirectories:

```
weather/
├── germany/
├── austria/
└── switzerland/
```

---

## 📍 Available Locations

### Austria 🇦🇹

| File | Location | Dataset | Description |
|------|----------|---------|-------------|
| `example.epw` | Salzburg | IWEC | International Weather for Energy Calculations |

### Germany 🇩🇪

*No files yet - ready for expansion*

**Suggested locations:**
- Berlin
- Munich
- Hamburg
- Frankfurt
- Cologne

### Switzerland 🇨🇭

*No files yet - ready for expansion*

**Suggested locations:**
- Zurich
- Geneva
- Basel
- Bern

---

## 📥 Adding Weather Files

### 1. Download EPW Files

**Sources:**
- **EnergyPlus:** https://energyplus.net/weather
- **Climate.OneBuilding.Org:** https://climate.onebuilding.org/
- **PVGIS:** https://re.jrc.ec.europa.eu/pvg_tools/en/

### 2. File Naming Convention

```
{COUNTRY}_{CITY}_{DATASET}.epw

Examples:
- AUT_Vienna_IWEC.epw
- DEU_Berlin_IWEC.epw
- DEU_Munich_TMY.epw
- CHE_Zurich_IWEC.epw
```

**Abbreviations:**
- `AUT` = Austria
- `DEU` = Germany (Deutschland)
- `CHE` = Switzerland (Confoederatio Helvetica)

**Datasets:**
- `IWEC` = International Weather for Energy Calculations
- `TMY` = Typical Meteorological Year
- `AMY` = Actual Meteorological Year

### 3. Save to Correct Directory

```bash
# Austria
resources/energyplus/weather/austria/AUT_Vienna_IWEC.epw

# Germany
resources/energyplus/weather/germany/DEU_Berlin_IWEC.epw

# Switzerland
resources/energyplus/weather/switzerland/CHE_Zurich_IWEC.epw
```

---

## 🔧 Usage in Code

### Python

```python
from pathlib import Path

# Specific file
weather = Path("resources/energyplus/weather/austria/example.epw")

# Find all EPW files recursively
weather_dir = Path("resources/energyplus/weather")
all_files = list(weather_dir.glob("**/*.epw"))

# Filter by country
austria_files = list(weather_dir.glob("austria/*.epw"))
```

### Config (YAML)

```yaml
simulation:
  weather: "resources/energyplus/weather/austria/example.epw"
```

---

## 📊 EPW File Format

EPW files contain hourly weather data for a full year (8760 hours):

**Data includes:**
- ☀️ Dry Bulb Temperature
- 💧 Relative Humidity
- 🌤️ Direct/Diffuse Solar Radiation
- 💨 Wind Speed & Direction
- ☁️ Cloud Cover
- 🌧️ Precipitation
- 🌡️ Atmospheric Pressure

**File Structure:**
- Header: 8 lines with location metadata
- Data: 8760 lines (1 per hour)

---

## 🎯 Quality Recommendations

### Preferred Datasets:

1. **IWEC** - Best for energy simulations
   - Compiled from 18+ years of data
   - Quality-controlled
   - Recommended by EnergyPlus

2. **TMY** - Good for typical conditions
   - Compiled from 15-30 years
   - Representative of typical weather

3. **AMY** - Use for specific years
   - Actual year data
   - Good for validation

### Avoid:
- ❌ Non-official sources without validation
- ❌ Truncated files (< 8760 hours)
- ❌ Files with many missing values

---

## 🔄 Migration Notes

**Previous location:** `data/weather/`
**New location:** `resources/energyplus/weather/`

**Changes:**
- Organized by country in subdirectories
- Supports recursive search in Web UI
- Better scalability for multiple locations

---

**Created:** 2025-11-13
**Format:** EPW (EnergyPlus Weather Format)
**Standard:** EnergyPlus 9.x - 25.x compatible
