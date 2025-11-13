# 📋 Simulation Scenarios

YAML configuration files for reproducible EnergyPlus simulations.

## 🎯 Purpose

This directory contains **simulation scenario configs** - complete building definitions that can be simulated with a single command:

```bash
python scripts/run_from_config.py scenarios/efh_standard.yaml
```

Each YAML file describes:
- ✅ Building geometry and envelope
- ✅ Internal loads and schedules
- ✅ HVAC system configuration
- ✅ Weather data
- ✅ Output requirements

## 📁 Available Scenarios

### 🏗️ Workflow Types

This tool supports **two workflows**:

1. **SimpleBox** - Parametric box model for rapid studies
   - Quick geometry definition (length × width × height)
   - Uniform envelope properties
   - Single-zone or multi-floor models

2. **Energieausweis** ⭐ **NEW!** - 5-zone model from Austrian/German energy certificates
   - Based on certified building data
   - Realistic U-values from energy certificates
   - 5-zone model (North, East, South, West, Core) for orientation effects
   - Geometry reconstructed from envelope areas

### Residential Buildings - SimpleBox

#### `efh_standard.yaml` - Standard Single-Family Home
- **Type:** Einfamilienhaus (EFH)
- **Standard:** Post-2000 construction
- **Size:** 12m × 10m, 2 floors (120m²)
- **Insulation:** Standard (U-wall: 0.35 W/m²K)
- **Expected Energy:** ~80-120 kWh/m²a

```bash
python scripts/run_from_config.py scenarios/efh_standard.yaml
```

#### `efh_passivhaus.yaml` - Passive House
- **Type:** Einfamilienhaus (EFH)
- **Standard:** Passivhaus certified
- **Size:** 12m × 10m, 2 floors (120m²)
- **Insulation:** High-performance (U-wall: 0.10 W/m²K)
- **Expected Energy:** <15 kWh/m²a (heating)

```bash
python scripts/run_from_config.py scenarios/efh_passivhaus.yaml
```

### Commercial Buildings - SimpleBox

#### `office_small.yaml` - Small Office Building
- **Type:** Office
- **Size:** 20m × 15m, 3 floors (900m²)
- **Occupancy:** 0.05 people/m² (typical office density)
- **Internal Loads:** Higher (lighting: 10 W/m², equipment: 8 W/m²)
- **Schedule:** Office hours (8:00-18:00)

```bash
python scripts/run_from_config.py scenarios/office_small.yaml
```

### Residential Buildings - Energieausweis ⭐ **NEW!**

#### `energieausweis_efh_example.yaml` - Energy Certificate Model
- **Type:** Einfamilienhaus (EFH) - 5-Zone Model
- **Standard:** Built 2010
- **Net Floor Area:** 150 m²
- **U-Values:** Wall: 0.28, Roof: 0.20, Window: 1.3 W/m²K
- **Features:**
  - Geometry reconstructed from envelope areas
  - Windows specified by orientation (North, East, South, West)
  - Realistic infiltration from Blower Door test
- **Expected Energy:** ~75-95 kWh/m²a

```bash
python scripts/run_from_config.py scenarios/energieausweis_efh_example.yaml
```

**How to create your own:**
1. Export from Web UI after entering energy certificate data
2. Or copy `energieausweis_efh_example.yaml` and edit U-values and areas

---

## 🚀 Usage

### Basic Simulation

Run a scenario with default settings:

```bash
python scripts/run_from_config.py scenarios/efh_standard.yaml
```

### Custom Output Directory

Override the output location:

```bash
python scripts/run_from_config.py scenarios/efh_passivhaus.yaml --output results/passivhaus_test
```

### Validate Configuration

Check if a config is valid without running:

```bash
python scripts/run_from_config.py scenarios/office_small.yaml --validate-only
```

### Verbose Logging

Enable detailed logging:

```bash
python scripts/run_from_config.py scenarios/efh_standard.yaml --verbose
```

---

## 📝 Creating Custom Scenarios

### 1. Copy Template

Start from an existing scenario:

```bash
cp scenarios/efh_standard.yaml scenarios/my_building.yaml
```

### 2. Edit Configuration

Key sections to modify:

```yaml
name: "My Custom Building"
description: "Description of the building"

building:
  geometry:
    length: 15.0          # Building dimensions
    width: 12.0
    height: 9.0
    num_floors: 3

  envelope:
    wall_u_value: 0.30    # Insulation quality
    roof_u_value: 0.25
    window_u_value: 1.2

  default_zone:
    zone_type: "residential"  # or "office", "retail"
    people_density: 0.02      # People per m²
    lighting_power: 5.0       # W/m²
    equipment_power: 3.0      # W/m²

hvac:
  ideal_loads:
    heating_setpoint: 20.0    # °C
    cooling_setpoint: 26.0    # °C

simulation:
  weather_file: "resources/energyplus/weather/austria/example.epw"
  output:
    output_dir: "output/my_building"
```

### 3. Run Simulation

```bash
python scripts/run_from_config.py scenarios/my_building.yaml
```

---

## 📊 Configuration Schema

### Complete Structure

```yaml
name: "Scenario Name"
description: "Detailed description"
version: "1.0"

building:
  name: "Building ID"
  building_type: "residential"  # or "office", "retail", "mixed"

  geometry:
    length: 12.0              # meters
    width: 10.0               # meters
    height: 6.0               # total height
    num_floors: 2
    floor_height: 3.0         # per floor (optional)
    window_wall_ratio: 0.25   # 0.0 - 1.0
    orientation: 0.0          # degrees (0 = North)

  envelope:
    wall_construction: "medium_insulated"
    wall_u_value: 0.35        # W/m²K
    roof_construction: "insulated_roof"
    roof_u_value: 0.25
    floor_construction: "slab_on_grade"
    floor_u_value: 0.40
    window_type: "double_glazed"
    window_u_value: 1.3
    window_shgc: 0.6          # Solar Heat Gain Coefficient

  default_zone:
    zone_type: "residential"  # "residential", "office", "retail", "other"

    # Internal loads
    people_density: 0.02      # people per m²
    lighting_power: 5.0       # W/m²
    equipment_power: 3.0      # W/m²

    # Schedules
    occupancy_schedule: "residential"  # or "office"
    lighting_schedule: "residential"
    equipment_schedule: "residential"

    # Infiltration
    infiltration_rate: 0.5    # ACH (air changes per hour)

hvac:
  system_type: "ideal_loads"  # Currently only ideal_loads supported

  ideal_loads:
    heating_setpoint: 20.0    # °C
    cooling_setpoint: 26.0    # °C
    outdoor_air_flow_rate: 0.0
    economizer: false

simulation:
  weather_file: "resources/energyplus/weather/austria/example.epw"

  period:
    start_month: 1
    start_day: 1
    end_month: 12
    end_day: 31

  output:
    output_dir: "output/scenario_name"
    save_idf: true
    save_sql: true

    output_variables:
      - "Zone Mean Air Temperature"
      - "Zone Air System Sensible Heating Energy"
      - "Zone Air System Sensible Cooling Energy"

    reporting_frequency: "Hourly"  # Timestep, Hourly, Daily, Monthly, Annual

  timeout: 3600  # seconds
```

---

## 🔧 Configuration Tips

### Typical U-Values (W/m²K)

**Walls:**
- Old building (pre-1980): 1.0 - 1.5
- Standard (1980-2000): 0.5 - 0.8
- Modern (post-2000): 0.25 - 0.35
- Low-energy: 0.15 - 0.20
- Passivhaus: ≤ 0.15

**Roof:**
- Old: 0.8 - 1.2
- Standard: 0.3 - 0.5
- Modern: 0.15 - 0.25
- Passivhaus: ≤ 0.15

**Windows:**
- Single glazed: 5.0 - 6.0
- Double glazed: 2.5 - 3.0
- Modern double: 1.1 - 1.4
- Triple glazed: 0.8 - 1.0
- Passivhaus: ≤ 0.8

### Typical Internal Loads

**Residential:**
- People: 0.02 people/m² (2 per 100m²)
- Lighting: 3-5 W/m²
- Equipment: 2-4 W/m²

**Office:**
- People: 0.05 people/m² (5 per 100m²)
- Lighting: 8-12 W/m²
- Equipment: 6-10 W/m²

**Retail:**
- People: 0.1 people/m² (10 per 100m²)
- Lighting: 15-25 W/m²
- Equipment: 5-8 W/m²

### Infiltration Rates (ACH)

- **Very tight** (Passivhaus): 0.1 - 0.2
- **Tight** (modern): 0.3 - 0.5
- **Average**: 0.5 - 0.8
- **Leaky** (old buildings): 1.0 - 2.0

---

## ✅ Validation

The config system validates:
- ✅ All numeric values in valid ranges
- ✅ Required files exist (weather data)
- ✅ Building dimensions are positive
- ✅ Ratios are between 0 and 1
- ✅ YAML syntax is correct

**Validate before running:**

```bash
python scripts/run_from_config.py scenarios/my_config.yaml --validate-only
```

---

## 📂 Results

After simulation, results are saved to the `output/` directory:

```
output/
└── scenario_name/
    ├── building.idf           # Generated IDF model
    ├── eplusout.sql           # Simulation results database
    ├── eplusout.err           # Error/warning log
    ├── eplusout.end           # Completion status
    └── *.csv                  # Hourly/monthly reports
```

---

## 🔄 Workflow Example

**1. Choose or create scenario:**
```bash
cp scenarios/efh_standard.yaml scenarios/my_house.yaml
```

**2. Customize building parameters:**
```bash
nano scenarios/my_house.yaml  # Edit geometry, envelope, etc.
```

**3. Validate configuration:**
```bash
python scripts/run_from_config.py scenarios/my_house.yaml --validate-only
```

**4. Run simulation:**
```bash
python scripts/run_from_config.py scenarios/my_house.yaml
```

**5. Check results:**
```
Results saved to: output/my_house/
Energy Performance: 85.3 kWh/m²a
Efficiency Class: B
```

---

## 🆚 Comparison: Config vs. Interactive

### YAML Config (Recommended for Production)
✅ Reproducible (version control)
✅ Scriptable (batch processing)
✅ Documented (self-describing)
✅ Fast (single command)

### Web UI (Great for Exploration)
✅ Interactive
✅ Visual feedback
✅ Learning tool
✅ Quick prototyping

**Best Practice:** Use Web UI to explore, then convert to YAML config for production use.

---

**Created:** 2025-11-13
**Format:** YAML (Simulation Scenario Configuration)
**Tool:** `run_from_config.py`
