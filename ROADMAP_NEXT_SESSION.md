# 🚀 Roadmap: Next Session - Tool Improvements & Refactoring

**Status:** Planning
**Priority:** High
**Created:** 2025-11-12
**Session Goal:** Improve code architecture, user experience, and configurability

---

## 📊 Current State (Achievements)

### ✅ What Works Now:
- ✅ **Internal Loads Fixed!** (Issue #5 resolved)
  - Native eppy approach: PEOPLE + LIGHTS + ELECTRICEQUIPMENT
  - 12MB SQL, 0 Severe Errors, 30 objects working
  - Full integration in FiveZoneGenerator
- ✅ **HVAC System:** Native ZONEHVAC:IDEALLOADSAIRSYSTEM
- ✅ **5-Zone Geometry:** Core + 4 Perimeter zones
- ✅ **Multi-floor Support:** Tested with 2 floors
- ✅ **Simulation Pipeline:** End-to-end workflow functional
- ✅ **Web UI:** Geometry → HVAC → Simulation → Results

---

## 🎯 Next Session Goals

### 1. 🏗️ Code Architecture Refactoring

#### 1.1 Split FiveZoneGenerator into Modular Functions
**Problem:** Monolithic ~2000-line class, hard to test and maintain

**Solution:** Extract separate generator functions
```python
# Current (Monolithic)
class FiveZoneGenerator:
    def generate():  # 2000 lines doing everything
        ...

# Proposed (Modular)
class FiveZoneGenerator:
    def generate():
        self._generate_metadata()
        self._generate_materials()
        schedules = self._generate_schedules()
        zones = self._generate_zones()
        surfaces = self._generate_surfaces(zones)
        self._generate_fenestration(surfaces)
        self._generate_internal_loads(zones, schedules)
        self._generate_hvac(zones)
```

**Benefits:**
- ✅ Each function has clear responsibility
- ✅ Easy to test individually
- ✅ Better error localization
- ✅ Reusable components

**Reference:** See `ARCHITECTURE_PROPOSAL.md`

**Tasks:**
- [ ] Extract `_generate_metadata()` (Building-level settings)
- [ ] Extract `_generate_materials()` (Constructions, Materials)
- [ ] Extract `_generate_schedules()` (already done via NativeInternalLoadsManager)
- [ ] Extract `_generate_zones()` (Zone geometry)
- [ ] Extract `_generate_surfaces()` (Walls, Floors, Ceilings)
- [ ] Extract `_generate_fenestration()` (Windows)
- [ ] Extract `_generate_internal_loads()` (already done)
- [ ] Extract `_generate_hvac()` (HVAC systems)
- [ ] Add data classes for information flow (ZoneInfo, SurfaceInfo)

---

### 2. 📁 Restructure Template & Data Directories

#### 2.1 Current Problem
**Multiple scattered template directories:**
```
templates/
  hvac/
  internal_loads/
  schedules/
data/
  weather/
  (other templates?)
```

**Issues:**
- ❌ Templates in multiple locations
- ❌ Unclear organization
- ❌ Hard to find resources
- ❌ Duplication risk

#### 2.2 Proposed Structure
```
resources/
  energyplus/
    templates/
      hvac/
        ideal_loads.idf
        thermostat_shared.idf

      internal_loads/
        # Residential
        people_residential_0.02.idf      # 1 person per 50m²
        lights_residential_5w.idf        # 5 W/m²
        equipment_residential_4w.idf     # 4 W/m²

        # Office
        people_office_0.05.idf           # 1 person per 20m²
        lights_office_10w.idf            # 10 W/m²
        equipment_office_8w.idf          # 8 W/m²

        # Retail (future)
        people_retail_0.08.idf
        lights_retail_15w.idf

      schedules/
        # Residential
        occupancy_residential.idf
        occupancy_residential_weekend.idf

        # Office
        occupancy_office_8_18.idf
        occupancy_office_7_19.idf

        # Common
        activity_level_120w.idf
        activity_level_150w.idf  # standing work

      materials/
        walls/
          wall_insulated_u0.3.idf      # EnEV 2016
          wall_insulated_u0.5.idf      # Older standard
          wall_uninsulated_u2.0.idf    # Pre-1980

        roofs/
          roof_insulated_u0.2.idf
          roof_insulated_u0.4.idf

        floors/
          floor_ground_u0.5.idf
          floor_slab_u0.3.idf

        windows/
          window_double_u2.5.idf
          window_triple_u1.1.idf
          window_triple_u0.8.idf

      constructions/
        construction_set_efh_new.idf     # EFH nach EnEV 2016
        construction_set_efh_old.idf     # EFH unsaniert
        construction_set_mfh_new.idf
        construction_set_nwg_office.idf

  weather/
    germany/
      DEU_Berlin_IWEC.epw
      DEU_Munich_IWEC.epw
      DEU_Hamburg_IWEC.epw
    austria/
      AUT_Wien_IWEC.epw
      AUT_Salzburg_IWEC.epw
    example.epw
```

**Tasks:**
- [ ] Create `resources/energyplus/` structure
- [ ] Move existing templates to new structure
- [ ] Update all Path references in code
- [ ] Add README.md in each subfolder explaining contents
- [ ] Version control: Add `.template_version` files

---

### 3. 🔧 Enhance Internal Loads Configuration

#### 3.1 Current Limitations
- ❌ Hardcoded values in `NativeInternalLoadsManager`
- ❌ Only 2 building types (office, residential)
- ❌ No user control over densities

#### 3.2 Proposed Improvements

**3.2.1 Expand Building Types:**
```python
BUILDING_TYPES = {
    "residential_efh": {
        "people_per_area": 0.02,
        "lights_watts_per_area": 5.0,
        "equipment_watts_per_area": 4.0,
        "activity_level": 100.0,
    },
    "residential_mfh": {
        "people_per_area": 0.025,
        "lights_watts_per_area": 6.0,
        "equipment_watts_per_area": 5.0,
        "activity_level": 100.0,
    },
    "office_small": {
        "people_per_area": 0.05,
        "lights_watts_per_area": 10.0,
        "equipment_watts_per_area": 8.0,
        "activity_level": 120.0,
    },
    "office_large": {
        "people_per_area": 0.08,
        "lights_watts_per_area": 12.0,
        "equipment_watts_per_area": 10.0,
        "activity_level": 120.0,
    },
    "retail": {
        "people_per_area": 0.10,
        "lights_watts_per_area": 15.0,
        "equipment_watts_per_area": 5.0,
        "activity_level": 150.0,
    },
}
```

**3.2.2 Per-Zone Overrides:**
```python
# Allow different loads per zone
zone_overrides = {
    "Core_F1": {
        "people_per_area": 0.08,  # Server room = empty
        "equipment_watts_per_area": 50.0,  # High equipment
    },
    "Perimeter_North_F1": {
        "lights_watts_per_area": 15.0,  # More lights needed (North)
    },
}
```

**Tasks:**
- [ ] Expand `BUILDING_TYPES` dictionary
- [ ] Add DIN/ASHRAE standard values as presets
- [ ] Support custom user values via UI or config
- [ ] Document typical values in README

---

### 4. 📊 Results Tab: Input Summary & Zone Details

#### 4.1 Problem
**Current Results Tab:**
- ✅ Shows simulation outputs (temperatures, energy)
- ❌ **Missing:** Input parameters used
- ❌ **Missing:** Zone-by-zone breakdown
- ❌ **Hard to reproduce** simulations

#### 4.2 Proposed: "Input Summary" Sub-Tab

**Layout:**
```
Results
  ├─ Input Summary  ← NEW!
  ├─ Zone Temperatures
  ├─ Energy Balance
  └─ ...
```

**Input Summary Content:**
```
📋 Simulation Input Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 Building Information
  Name:              5Zone_Building_From_Energieausweis
  Type:              EFH (Einfamilienhaus)
  Floors:            2
  Total Floor Area:  200 m²
  Volume:            600 m³
  A/V Ratio:         0.42 m⁻¹

📐 Geometry
  Length:            11.50 m
  Width:             12.34 m
  Height per Floor:  3.00 m
  Orientation:       0° (North)

🪟 Windows
  Total Area:        40 m²
  WWR Overall:       20%
  WWR North:         15%
  WWR East:          25%
  WWR South:         25%
  WWR West:          15%

👥 Internal Loads (per Zone)
┌─────────────────────┬────────┬─────────┬───────────┬────────────┐
│ Zone                │ People │ Lights  │ Equipment │ Activity   │
│                     │ [p/m²] │ [W/m²]  │ [W/m²]    │ [W/person] │
├─────────────────────┼────────┼─────────┼───────────┼────────────┤
│ Perimeter_North_F1  │ 0.020  │ 5.0     │ 4.0       │ 100        │
│ Perimeter_East_F1   │ 0.020  │ 5.0     │ 4.0       │ 100        │
│ Perimeter_South_F1  │ 0.020  │ 5.0     │ 4.0       │ 100        │
│ Perimeter_West_F1   │ 0.020  │ 5.0     │ 4.0       │ 100        │
│ Core_F1             │ 0.020  │ 5.0     │ 4.0       │ 100        │
│ ... (F2)            │ ...    │ ...     │ ...       │ ...        │
└─────────────────────┴────────┴─────────┴───────────┴────────────┘

💨 Infiltration
  Air Changes:       0.6 ACH

🌡️ HVAC System
  Type:              Ideal Loads Air System
  Heating Setpoint:  20°C
  Cooling Setpoint:  26°C
  Max Heating Temp:  50°C
  Min Cooling Temp:  13°C

🏗️ Constructions
  Walls:             WallConstruction (U=0.50 W/m²K)
  Roof:              RoofConstruction (U=0.40 W/m²K)
  Floor:             FloorConstruction (U=0.60 W/m²K)
  Windows:           SimpleGlazing (U=2.50 W/m²K, SHGC=0.7)

☀️ Simulation Settings
  Weather:           Salzburg, AUT IWEC
  Timestep:          4 per hour (15 min)
  Run Period:        01/01 - 12/31 (Full year)
  Design Days:       Yes (Heating: -10°C, Cooling: 32°C)

📁 Files
  IDF:               building.idf (180 KB)
  Weather:           example.epw
  Output:            simulation_20251112_220239
```

**Implementation:**
- [ ] Create `InputSummaryGenerator` class
- [ ] Extract data from BuildingModel
- [ ] Format as markdown table
- [ ] Add to Results Tab as first sub-tab
- [ ] Export as PDF option

---

### 5. ⚙️ Simulation Settings UI

#### 5.1 Problem
**Current:**
- ❌ No user control over simulation parameters
- ❌ No control over output variables
- ❌ Hardcoded timestep (4 per hour)
- ❌ Hardcoded output variables

#### 5.2 Proposed: "Settings" Expander in Simulation Tab

**UI Mock:**
```
Simulation
  ▼ Basis-Parameter
    Timestep:              [4] per hour (15 min intervals)
    Run Period:            [01/01] - [12/31]
    Include Design Days:   [✓]
    Warmup Days:           [25]

  ▼ Output Variables
    Temperature:
      [✓] Zone Mean Air Temperature
      [✓] Zone Operative Temperature
      [ ] Zone Air Humidity Ratio
      [ ] Surface Inside Temperature

    Energy:
      [✓] Zone Ideal Loads Heating Energy
      [✓] Zone Ideal Loads Cooling Energy
      [✓] Zone Lights Electric Energy
      [✓] Zone Electric Equipment Electric Energy
      [ ] Zone People Sensible Heating Energy

    Comfort:
      [ ] Zone Thermal Comfort Fanger PMV
      [ ] Zone Thermal Comfort Fanger PPD

    HVAC:
      [ ] Zone Air System Sensible Heating Rate
      [ ] Zone Air System Sensible Cooling Rate

    Presets:
      [Minimal] [Standard] [Detailed] [All]
```

**Benefits:**
- ✅ User sees what's possible
- ✅ Reduce SQL size for faster simulations (only needed outputs)
- ✅ Educational (shows available metrics)
- ✅ Flexible for research vs. quick checks

**Tasks:**
- [ ] Create `SimulationSettings` dataclass
- [ ] Add settings UI in Simulation Tab
- [ ] Map settings to EnergyPlus `OUTPUT:VARIABLE` objects
- [ ] Create presets (Minimal, Standard, Detailed, All)
- [ ] Save user preferences to session state

---

### 6. 📄 Configuration Files (YAML/JSON)

#### 6.1 Problem
**Current:**
- ❌ UI only (no scriptable workflows)
- ❌ Hard to batch-process multiple buildings
- ❌ Hard to version-control simulation setups

#### 6.2 Proposed: Config File Support

**Structure:**
```yaml
# simulation_config.yaml
building:
  name: "EFH_Mustermann_Berlin"
  type: "residential_efh"
  floors: 2
  floor_area: 200  # m²

geometry:
  aspect_ratio: 1.5  # L/W
  floor_height: 3.0  # m
  window_wall_ratio:
    north: 0.15
    east: 0.25
    south: 0.30
    west: 0.15

internal_loads:
  people_density: 0.02      # people/m² (or "auto" for building type default)
  lights_density: 5.0       # W/m² (or "auto")
  equipment_density: 4.0    # W/m² (or "auto")
  activity_level: 100.0     # W/person

  # Optional: Per-zone overrides
  zone_overrides:
    Core_F1:
      people_density: 0.0
      equipment_density: 20.0  # Home office

hvac:
  type: "ideal_loads"
  heating_setpoint: 20.0  # °C
  cooling_setpoint: 26.0  # °C

simulation:
  weather: "resources/weather/germany/DEU_Berlin_IWEC.epw"
  timestep: 4  # per hour
  run_period:
    start: "01/01"
    end: "12/31"
  design_days: true

  output_variables:
    - "Zone Mean Air Temperature"
    - "Zone Ideal Loads Heating Energy"
    - "Zone Ideal Loads Cooling Energy"
```

**Usage:**
```bash
# CLI mode
python scripts/run_simulation_from_config.py --config simulation_config.yaml

# UI mode: Load config button
```

**Benefits:**
- ✅ Reproducible simulations
- ✅ Version control friendly
- ✅ Batch processing
- ✅ Parameterized studies (sweep over configs)

**Tasks:**
- [ ] Create `SimulationConfig` dataclass with `from_yaml()` method
- [ ] Add "Load Config" button in UI
- [ ] Add "Export Config" button (save current UI state)
- [ ] Create CLI script `run_simulation_from_config.py`
- [ ] Add validation (Pydantic)
- [ ] Documentation with examples

---

### 7. 🌟 Additional Improvements (Ideas)

#### 7.1 Error Reporting & Logging
- [ ] Structured logging (JSON logs for analysis)
- [ ] Error categorization (Geometry, HVAC, Simulation)
- [ ] Suggestions for common errors
- [ ] "Debug Mode" toggle in UI

#### 7.2 Performance Optimizations
- [ ] Cache IDF templates (don't reload every time)
- [ ] Parallel simulation runs (batch processing)
- [ ] Incremental re-simulation (only changed zones)

#### 7.3 Validation & Quality Checks
- [ ] Pre-simulation validation (check IDF completeness)
- [ ] Geometry validation (enclosed zones, surface matching)
- [ ] Post-simulation validation (reasonable results?)
- [ ] Comparison to benchmarks (ASHRAE, PHPP)

#### 7.4 Advanced Features
- [ ] Parametric studies (sweep over WWR, insulation, etc.)
- [ ] Optimization (find best insulation thickness)
- [ ] Cost estimation (energy savings vs. investment)
- [ ] Export to other formats (gbXML, IFC)

#### 7.5 User Experience
- [ ] Progress indicators for long operations
- [ ] Tooltips with explanations
- [ ] Tutorial mode (guided workflow)
- [ ] Example buildings library

#### 7.6 Testing & CI/CD
- [ ] Unit tests for each generator function
- [ ] Integration tests (full simulation)
- [ ] Regression tests (compare outputs)
- [ ] GitHub Actions for automated testing

#### 7.7 Documentation
- [ ] User manual (PDF/Web)
- [ ] Developer guide (API docs)
- [ ] Video tutorials
- [ ] FAQ

---

## 📝 Implementation Priority

### Phase 1: Foundation (High Priority)
1. ✅ **FiveZoneGenerator Refactoring** (enables all other work)
2. ✅ **Template Restructuring** (clean foundation)
3. ✅ **Input Summary Tab** (user visibility)

### Phase 2: Flexibility (Medium Priority)
4. ✅ **Simulation Settings UI** (user control)
5. ✅ **Config File Support** (reproducibility)
6. ✅ **Expand Building Types** (real-world usage)

### Phase 3: Quality (Low Priority)
7. Validation & Testing
8. Performance Optimizations
9. Documentation

---

## 🎯 Success Metrics

**Phase 1:**
- [ ] FiveZoneGenerator split into <300 lines per function
- [ ] All templates in single `resources/` tree
- [ ] Input Summary shows 100% of simulation params

**Phase 2:**
- [ ] User can control 5+ simulation parameters via UI
- [ ] Config file can reproduce any UI simulation
- [ ] 5+ building type presets available

**Phase 3:**
- [ ] 80% code coverage with tests
- [ ] Simulation <10s for standard building
- [ ] User manual complete

---

## 🤝 Feedback Welcome!

Questions to consider:
1. Is the proposed structure clear and maintainable?
2. Are there other pain points we should address?
3. Should we prioritize differently?
4. What features would have most impact for users?

---

**Next Steps:**
1. Review this roadmap
2. Adjust priorities if needed
3. Start with Phase 1, Task 1 (FiveZoneGenerator refactoring)
4. Iterate!
