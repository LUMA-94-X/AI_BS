# 05 - IDF-Struktur Dokumentation

> **Modul:** EnergyPlus IDF-File Struktur und Parameter-Mapping
> **Zweck:** Welche Daten werden ins IDF übernommen und wie?
> **Zuletzt aktualisiert:** 2025-11-14

---

## Übersicht

Das **IDF (Input Data File)** ist die Haupteingabedatei für EnergyPlus. Diese Dokumentation zeigt:

1. Welche Input-Parameter ins IDF übernommen werden
2. Wie das IDF strukturiert ist
3. Kritische EnergyPlus-Konventionen

---

## 1. Parameter-Mapping: Energieausweis → IDF

### Geometrie-Parameter

| Energieausweis-Parameter | IDF-Verwendung | IDF-Objekt | Kommentar |
|--------------------------|----------------|------------|-----------|
| `length` (berechnet) | Zone X-Koordinaten, Surface Vertices | ZONE, BUILDINGSURFACE | Via GeometrySolver |
| `width` (berechnet) | Zone Y-Koordinaten, Surface Vertices | ZONE, BUILDINGSURFACE | Via GeometrySolver |
| `height` (berechnet) | Zone Z-Koordinaten, Surface Vertices | ZONE, BUILDINGSURFACE | Via GeometrySolver |
| `anzahl_geschosse` | Anzahl Floor-Layouts | ZONE × n_floors | 5 Zonen pro Geschoss |
| `geschosshoehe_m` | Zone Height, Surface Z-Span | ZONE, BUILDINGSURFACE | Geschoss-Spacing |
| `bruttoflaeche_m2` | Zone Volume (pro Geschoss) | ZONE | Aufgeteilt auf 5 Zonen |
| `brutto_volumen_m3` | Zone Volume (gesamt) | ZONE | Zur Validierung |

### Hüllkonstruktionen

| Energieausweis-Parameter | IDF-Verwendung | IDF-Objekt | Aktueller Status |
|--------------------------|----------------|------------|------------------|
| `u_wert_wand` | WallConstruction U-Wert | CONSTRUCTION + MATERIAL | **TODO:** U-basierte Generierung |
| `u_wert_dach` | RoofConstruction U-Wert | CONSTRUCTION + MATERIAL | **TODO:** U-basierte Generierung |
| `u_wert_boden` | FloorConstruction U-Wert | CONSTRUCTION + MATERIAL | **TODO:** U-basierte Generierung |
| `u_wert_fenster` | WindowConstruction U-Wert | WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM | **Aktuell:** Fest 2.7 W/m²K |
| `g_wert_fenster` | SHGC (Solar Heat Gain Coefficient) | WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM | **Aktuell:** Fest 0.7 |

**Aktuell:**
- Standard-Konstruktionen mit **fixen U-Werten** (aus `core/materialien.py`)
- U-Werte aus Energieausweis werden **nicht** ins IDF übernommen

**Geplant:**
- Dämmstoffdicke-Berechnung aus Ziel-U-Wert
- Layer-by-Layer Konstruktions-Generierung
- Validierung gegen Ziel-U-Wert

### Fenster-Parameter

| Energieausweis-Parameter | IDF-Verwendung | IDF-Objekt | Berechnung |
|--------------------------|----------------|------------|------------|
| `fenster.nord_m2` | FENESTRATIONSURFACE:DETAILED (Nord) | Fenster-Vertices | WWR_north × Wandfläche_Nord |
| `fenster.ost_m2` | FENESTRATIONSURFACE:DETAILED (Ost) | Fenster-Vertices | WWR_east × Wandfläche_Ost |
| `fenster.sued_m2` | FENESTRATIONSURFACE:DETAILED (Süd) | Fenster-Vertices | WWR_south × Wandfläche_Süd |
| `fenster.west_m2` | FENESTRATIONSURFACE:DETAILED (West) | Fenster-Vertices | WWR_west × Wandfläche_West |

**Fenster-Größe-Berechnung:**

```python
# 1. WWR pro Orientierung berechnen
WWR_north = fenster_nord_m2 / wandflaeche_nord_m2

# 2. Fenster-Dimensionen
wall_height = zone.height
wall_width = zone.length_or_width

# Proportional scaling
window_height = wall_height * sqrt(WWR_north)
window_width = wall_width * sqrt(WWR_north)

# Constraints
sill_height = 0.9  # m
head_clearance = 0.3  # m
max_window_height = wall_height - sill_height - head_clearance

window_height = min(window_height, max_window_height)

# 3. Positionierung (horizontal zentriert)
window_x_start = (wall_width - window_width) / 2
```

### Klimadaten

| Energieausweis-Parameter | IDF-Verwendung | IDF-Objekt | Kommentar |
|--------------------------|----------------|------------|-----------|
| `klimaregion` | Dokumentation | - | Nicht direkt ins IDF |
| `heizgradtage_kd` | Dokumentation | - | Für OIB-Bewertung, nicht Simulation |
| `norm_aussentemp_c` | Design Day (Heating) | SIZINGPERIOD:DESIGNDAY | Winter-Auslegung |
| EPW-Datei | Wetterdaten | - | Via `--weather` Parameter |

**Design Days:**

```python
# Winter Design Day (für Heizlast-Auslegung)
idf.newidfobject(
    "SIZINGPERIOD:DESIGNDAY",
    Name="Winter Design Day",
    Month=1,
    Day_of_Month=21,
    Day_Type="WinterDesignDay",
    Maximum_Dry_Bulb_Temperature=norm_aussentemp_c,  # z.B. -12°C
    # ...
)

# Summer Design Day (für Kühllast-Auslegung)
idf.newidfobject(
    "SIZINGPERIOD:DESIGNDAY",
    Name="Summer Design Day",
    Month=7,
    Day_of_Month=21,
    Day_Type="SummerDesignDay",
    Maximum_Dry_Bulb_Temperature=32.0,  # Annahme
    # ...
)
```

### Lüftung & Infiltration

| Energieausweis-Parameter | IDF-Verwendung | IDF-Objekt | Kommentar |
|--------------------------|----------------|------------|-----------|
| `luftwechselrate_h` | Air Changes/Hour | ZONEINFILTRATION:DESIGNFLOWRATE | Pro Zone |
| `art_lueftung` | Dokumentation | - | **TODO:** Mechanische Lüftung implementieren |

**Infiltration:**

```python
idf.newidfobject(
    "ZONEINFILTRATION:DESIGNFLOWRATE",
    Name=f"{zone.name}_Infiltration",
    Zone_or_ZoneList_Name=zone.name,
    Schedule_Name="AlwaysOn",
    Design_Flow_Rate_Calculation_Method="AirChanges/Hour",
    Air_Changes_per_Hour=0.6  # luftwechselrate_h
)
```

### HVAC-Parameter

| HVAC-Config-Parameter | IDF-Verwendung | IDF-Objekt | Kommentar |
|----------------------|----------------|------------|-----------|
| `heating_setpoint` | Constant_Heating_Setpoint | HVACTEMPLATE:THERMOSTAT | Shared für alle Zonen |
| `cooling_setpoint` | Constant_Cooling_Setpoint | HVACTEMPLATE:THERMOSTAT | Shared für alle Zonen |
| `heating_enabled` | HeatingAvailability Schedule | SCHEDULE:CONSTANT | 1.0=ON, 0.0=OFF |
| `cooling_enabled` | CoolingAvailability Schedule | SCHEDULE:CONSTANT | 1.0=ON, 0.0=OFF |
| `heating_system` | **NICHT im IDF** | - | Nur für PEB/CO₂-Berechnung! |

**Wichtig:** `heating_system` (z.B. "Wärmepumpe") wird **NICHT** ins IDF übernommen!
→ Simulation nutzt **immer** Ideal Loads Air System
→ `heating_system` nur für **Post-Processing** (PEB/CO₂-Berechnung)

---

## 2. IDF-Struktur (5-Zonen-Modell)

### Haupt-Abschnitte

```idf
! ============ VERSION ============
VERSION, 25.1;

! ============ GLOBAL SETTINGS ============
GLOBALGEOMETRYRULES, ...
SIMULATIONCONTROL, ...
BUILDING, ...
SITE:LOCATION, ...

! ============ TIME SETTINGS ============
TIMESTEP, 4;
RUNPERIOD, 1, 1, 12, 31;

! ============ DESIGN DAYS ============
SIZINGPERIOD:DESIGNDAY, Winter Design Day, ...
SIZINGPERIOD:DESIGNDAY, Summer Design Day, ...

! ============ SCHEDULES ============
SCHEDULETYPELIMITS, ...
SCHEDULE:CONSTANT, AlwaysOn, ...
SCHEDULE:CONSTANT, HeatingSetpoint, ...
SCHEDULE:CONSTANT, CoolingSetpoint, ...
SCHEDULE:CONSTANT, HeatingAvailability, ...
SCHEDULE:CONSTANT, CoolingAvailability, ...
SCHEDULE:COMPACT, OccupancySchedule, ...
SCHEDULE:COMPACT, LightsSchedule, ...

! ============ MATERIALS & CONSTRUCTIONS ============
MATERIAL, Concrete, ...
MATERIAL, Insulation, ...
MATERIAL, GypsumBoard, ...
MATERIAL, Brick, ...
MATERIAL, Plywood, ...
WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM, WindowConstruction, ...

CONSTRUCTION, WallConstruction, ...
CONSTRUCTION, RoofConstruction, ...
CONSTRUCTION, FloorConstruction, ...
CONSTRUCTION, CeilingConstruction, ...

! ============ ZONES (5 × n_floors) ============
ZONE, Perimeter_North_F1, ...
ZONE, Perimeter_East_F1, ...
ZONE, Perimeter_South_F1, ...
ZONE, Perimeter_West_F1, ...
ZONE, Core_F1, ...
ZONE, Perimeter_North_F2, ...
... (5 Zonen pro Geschoss)

! ============ ZONE SIZING ============
SIZING:ZONE, Perimeter_North_F1, ...
... (Pro Zone)

! ============ SURFACES ============
! Floors, Ceilings, Walls (Exterior + Interior), Windows
BUILDINGSURFACE:DETAILED, Perimeter_North_F1_Floor, ...
BUILDINGSURFACE:DETAILED, Perimeter_North_F1_Ceiling, ...
BUILDINGSURFACE:DETAILED, Perimeter_North_F1_Wall_North, ...
FENESTRATIONSURFACE:DETAILED, Perimeter_North_F1_Wall_North_Window, ...
BUILDINGSURFACE:DETAILED, Perimeter_North_F1_Wall_To_Core, ...
... (Pro Zone ca. 10-20 Surfaces)

! ============ INTERNAL LOADS ============
PEOPLE, Perimeter_North_F1_People, ...
LIGHTS, Perimeter_North_F1_Lights, ...
ELECTRICEQUIPMENT, Perimeter_North_F1_Equipment, ...

! ============ INFILTRATION ============
ZONEINFILTRATION:DESIGNFLOWRATE, Perimeter_North_F1_Infiltration, ...

! ============ HVAC SYSTEM (TEMPLATES) ============
HVACTEMPLATE:THERMOSTAT, All Zones, ...
HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM, Perimeter_North_F1, ...
HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM, Perimeter_East_F1, ...
... (Pro Zone)

! ============ OUTPUT VARIABLES ============
OUTPUT:VARIABLE, *, Zone Mean Air Temperature, Timestep;
OUTPUT:VARIABLE, *, Zone Air System Sensible Heating Energy, Hourly;
...

OUTPUT:TABLE:SUMMARYREPORTS, AllSummary;
OUTPUT:SQLITE, SimpleAndTabular;
```

---

## 3. Kritische EnergyPlus-Konventionen

### 3.1 Vertex-Ordering

**CRITICAL:** EnergyPlus bestimmt Surface-Normale aus Vertex-Reihenfolge!

#### Floors (Normal NACH UNTEN)

```python
# REVERSED Order [3,2,1,0]!
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_Floor",
    Surface_Type="Floor",
    Construction_Name="FloorConstruction",
    Zone_Name="Zone_Name",
    Outside_Boundary_Condition="Ground",  # Oder "Surface" für Inter-Floor
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=x3,  # REVERSED!
    Vertex_1_Ycoordinate=y3,
    Vertex_1_Zcoordinate=z0,
    Vertex_2_Xcoordinate=x2,
    Vertex_2_Ycoordinate=y2,
    Vertex_2_Zcoordinate=z0,
    Vertex_3_Xcoordinate=x1,
    Vertex_3_Ycoordinate=y1,
    Vertex_3_Zcoordinate=z0,
    Vertex_4_Xcoordinate=x0,
    Vertex_4_Ycoordinate=y0,
    Vertex_4_Zcoordinate=z0
)
```

#### Ceilings/Roofs (Normal NACH OBEN)

```python
# NORMAL Order [0,1,2,3]
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_Ceiling",
    Surface_Type="Ceiling",  # Oder "Roof"
    Construction_Name="CeilingConstruction",
    Zone_Name="Zone_Name",
    Outside_Boundary_Condition="Surface",  # Oder "Outdoors" für Roof
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=x0,  # NORMAL!
    Vertex_1_Ycoordinate=y0,
    Vertex_1_Zcoordinate=z1,
    Vertex_2_Xcoordinate=x1,
    Vertex_2_Ycoordinate=y1,
    Vertex_2_Zcoordinate=z1,
    Vertex_3_Xcoordinate=x2,
    Vertex_3_Ycoordinate=y2,
    Vertex_3_Zcoordinate=z1,
    Vertex_4_Xcoordinate=x3,
    Vertex_4_Ycoordinate=y3,
    Vertex_4_Zcoordinate=z1
)
```

#### Walls (Normal NACH AUSSEN)

```python
# Counter-Clockwise wenn von außen betrachtet
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_Wall_North",
    Surface_Type="Wall",
    Construction_Name="WallConstruction",
    Zone_Name="Zone_Name",
    Outside_Boundary_Condition="Outdoors",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=0,   # Unten links
    Vertex_1_Ycoordinate=W,
    Vertex_1_Zcoordinate=z0,
    Vertex_2_Xcoordinate=L,   # Unten rechts
    Vertex_2_Ycoordinate=W,
    Vertex_2_Zcoordinate=z0,
    Vertex_3_Xcoordinate=L,   # Oben rechts
    Vertex_3_Ycoordinate=W,
    Vertex_3_Zcoordinate=z1,
    Vertex_4_Xcoordinate=0,   # Oben links
    Vertex_4_Ycoordinate=W,
    Vertex_4_Zcoordinate=z1
)
```

---

### 3.2 Boundary Objects (Inter-Zone Walls)

**CRITICAL:** Inter-Zone Walls müssen **paarweise** definiert werden!

#### Wall A → Wall B

```python
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Core_Wall_To_North",
    Surface_Type="Wall",
    Construction_Name="WallConstruction",
    Zone_Name="Core_F1",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="North_Wall_To_Core",  # Paar!
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=p,
    Vertex_1_Ycoordinate=W-p,
    Vertex_1_Zcoordinate=z0,
    Vertex_2_Xcoordinate=L-p,
    Vertex_2_Ycoordinate=W-p,
    Vertex_2_Zcoordinate=z0,
    Vertex_3_Xcoordinate=L-p,
    Vertex_3_Ycoordinate=W-p,
    Vertex_3_Zcoordinate=z1,
    Vertex_4_Xcoordinate=p,
    Vertex_4_Ycoordinate=W-p,
    Vertex_4_Zcoordinate=z1
)
```

#### Wall B → Wall A (VERTICES REVERSED!)

```python
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="North_Wall_To_Core",
    Surface_Type="Wall",
    Construction_Name="WallConstruction",
    Zone_Name="Perimeter_North_F1",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Core_Wall_To_North",  # Back-Reference!
    Sun_Exposure="NoSun",
    Wind_Exposure="NoWind",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=L-p,  # REVERSED!
    Vertex_1_Ycoordinate=W-p,
    Vertex_1_Zcoordinate=z0,
    Vertex_2_Xcoordinate=p,
    Vertex_2_Ycoordinate=W-p,
    Vertex_2_Zcoordinate=z0,
    Vertex_3_Xcoordinate=p,
    Vertex_3_Ycoordinate=W-p,
    Vertex_3_Zcoordinate=z1,
    Vertex_4_Xcoordinate=L-p,
    Vertex_4_Ycoordinate=W-p,
    Vertex_4_Zcoordinate=z1
)
```

**Eppy Bug:**
- eppy schreibt manchmal `Outside_Boundary_Condition_Object` falsch
- **Lösung:** `EppyBugFixer.fix_boundary_objects(idf_path)` nach `idf.save()`

---

### 3.3 HVAC-Thermostat (eppy Bug)

**Problem:** Manuelle `ZONECONTROL:THERMOSTAT` verursachen eppy field-order bugs.

**Lösung:** HVACTEMPLATE-Objekte verwenden statt manuelle HVAC-Objekte!

```python
# ✗ FALSCH (verursacht Bugs):
idf.newidfobject("ZONECONTROL:THERMOSTAT", ...)
idf.newidfobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", ...)

# ✓ RICHTIG (via Templates):
idf.newidfobject("HVACTEMPLATE:THERMOSTAT", ...)  # Shared!
idf.newidfobject("HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM", ...)
```

**ExpandObjects:**
- HVACTEMPLATE-Objekte werden von `ExpandObjects.exe` in vollständige HVAC-Objekte konvertiert
- Automatisch erkannt und ausgeführt von `EnergyPlusRunner`
- Benötigt `Energy+.idd` im Working Directory!

---

## 4. IDF-Beispiel (Komplett für 1 Zone)

```idf
VERSION, 25.1;

! ============ GLOBAL SETTINGS ============
GLOBALGEOMETRYRULES,
  UpperLeftCorner,
  Counterclockwise,
  Relative,
  Relative,
  Relative;

SIMULATIONCONTROL,
  Yes,  ! Do Zone Sizing Calculation
  Yes,  ! Do System Sizing Calculation
  No,   ! Do Plant Sizing Calculation
  Yes,  ! Run Simulation for Sizing Periods
  Yes;  ! Run Simulation for Weather File Run Periods

BUILDING,
  Building,
  0.0,                        ! North Axis {deg}
  City,                       ! Terrain
  0.04,                       ! Loads Convergence Tolerance Value
  0.4,                        ! Temperature Convergence Tolerance Value
  FullExterior,               ! Solar Distribution
  25,                         ! Maximum Number of Warmup Days
  6;                          ! Minimum Number of Warmup Days

SITE:LOCATION,
  Vienna,                     ! Name
  48.2,                       ! Latitude {deg}
  16.4,                       ! Longitude {deg}
  1.0,                        ! Time Zone {hr}
  156.0;                      ! Elevation {m}

TIMESTEP, 4;

RUNPERIOD,
  Annual,                     ! Name
  1,                          ! Begin Month
  1,                          ! Begin Day of Month
  12,                         ! End Month
  31,                         ! End Day of Month
  UseWeatherFile,             ! Day of Week for Start Day
  Yes,                        ! Use Weather File Holidays and Special Days
  Yes,                        ! Use Weather File Daylight Saving Period
  No,                         ! Apply Weekend Holiday Rule
  Yes,                        ! Use Weather File Rain Indicators
  Yes;                        ! Use Weather File Snow Indicators

! ============ DESIGN DAYS ============
SIZINGPERIOD:DESIGNDAY,
  Winter Design Day,
  1,                          ! Month
  21,                         ! Day of Month
  WinterDesignDay,            ! Day Type
  -12.0,                      ! Maximum Dry-Bulb Temperature {C}
  0.0,                        ! Daily Dry-Bulb Temperature Range {deltaC}
  DefaultMultipliers,         ! Dry-Bulb Temperature Range Modifier Type
  ,                           ! Dry-Bulb Temperature Range Modifier Day Schedule Name
  Wetbulb,                    ! Humidity Condition Type
  -12.0,                      ! Wetbulb or DewPoint at Maximum Dry-Bulb {C}
  ,                           ! Humidity Condition Day Schedule Name
  ,                           ! Humidity Ratio at Maximum Dry-Bulb {kgWater/kgDryAir}
  ,                           ! Enthalpy at Maximum Dry-Bulb {J/kg}
  ,                           ! Daily Wet-Bulb Temperature Range {deltaC}
  101325.,                    ! Barometric Pressure {Pa}
  4.0,                        ! Wind Speed {m/s}
  0.0,                        ! Wind Direction {deg}
  No,                         ! Rain Indicator
  No,                         ! Snow Indicator
  No,                         ! Daylight Saving Time Indicator
  ASHRAEClearSky,             ! Solar Model Indicator
  ,                           ! Beam Solar Day Schedule Name
  ,                           ! Diffuse Solar Day Schedule Name
  ,                           ! ASHRAE Clear Sky Optical Depth for Beam Irradiance (taub) {dimensionless}
  ,                           ! ASHRAE Clear Sky Optical Depth for Diffuse Irradiance (taud) {dimensionless}
  0.0;                        ! Sky Clearness

! ============ SCHEDULES ============
SCHEDULETYPELIMITS,
  Temperature,
  -60,
  200,
  CONTINUOUS;

SCHEDULETYPELIMITS,
  Control Type,
  0,
  4,
  DISCRETE;

SCHEDULE:CONSTANT,
  AlwaysOn,
  Control Type,
  4.0;

SCHEDULE:CONSTANT,
  HeatingSetpoint,
  Temperature,
  20.0;

SCHEDULE:CONSTANT,
  CoolingSetpoint,
  Temperature,
  26.0;

SCHEDULE:CONSTANT,
  HeatingAvailability,
  Control Type,
  1.0;

SCHEDULE:CONSTANT,
  CoolingAvailability,
  Control Type,
  1.0;

SCHEDULE:COMPACT,
  OccupancySchedule,
  Fraction,
  Through: 12/31,
  For: Weekdays,
  Until: 8:00, 0.0,
  Until: 18:00, 1.0,
  Until: 24:00, 0.0,
  For: AllOtherDays,
  Until: 24:00, 0.0;

! ============ MATERIALS & CONSTRUCTIONS ============
MATERIAL,
  Concrete,
  MediumRough,
  0.2,                        ! Thickness {m}
  1.95,                       ! Conductivity {W/m-K}
  2400,                       ! Density {kg/m3}
  900;                        ! Specific Heat {J/kg-K}

MATERIAL,
  Insulation,
  Rough,
  0.10,
  0.04,
  30,
  840;

MATERIAL,
  GypsumBoard,
  Smooth,
  0.0127,
  0.16,
  800,
  1090;

WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM,
  WindowConstruction,
  2.7,                        ! U-Factor {W/m2-K}
  0.7;                        ! Solar Heat Gain Coefficient

CONSTRUCTION,
  WallConstruction,
  GypsumBoard,
  Insulation,
  Concrete,
  GypsumBoard;

CONSTRUCTION,
  FloorConstruction,
  Concrete,
  Insulation,
  Concrete;

! ============ ZONES ============
ZONE,
  Perimeter_North_F1,
  0,                          ! Direction of Relative North {deg}
  0, 4.43, 0,                 ! X, Y, Z Origin {m}
  1,                          ! Type
  1,                          ! Multiplier
  2.7,                        ! Ceiling Height {m}
  191.43;                     ! Volume {m3}

SIZING:ZONE,
  Perimeter_North_F1,
  SupplyAirTemperature,       ! Zone Cooling Design Supply Air Temperature Input Method
  14.0,                       ! Zone Cooling Design Supply Air Temperature {C}
  ,                           ! Zone Cooling Design Supply Air Temperature Difference {deltaC}
  SupplyAirTemperature,       ! Zone Heating Design Supply Air Temperature Input Method
  50.0,                       ! Zone Heating Design Supply Air Temperature {C}
  ,                           ! Zone Heating Design Supply Air Temperature Difference {deltaC}
  0.008,                      ! Zone Cooling Design Supply Air Humidity Ratio {kgWater/kgDryAir}
  0.008,                      ! Zone Heating Design Supply Air Humidity Ratio {kgWater/kgDryAir}
  SumOrMaximum,               ! Zone Heating Sizing Factor
  ,                           ! Zone Cooling Sizing Factor
  DesignDay,                  ! Cooling Design Air Flow Method
  0,                          ! Cooling Design Air Flow Rate {m3/s}
  ,                           ! Cooling Minimum Air Flow per Zone Floor Area {m3/s-m2}
  ,                           ! Cooling Minimum Air Flow {m3/s}
  ,                           ! Cooling Minimum Air Flow Fraction
  DesignDay,                  ! Heating Design Air Flow Method
  0,                          ! Heating Design Air Flow Rate {m3/s}
  ,                           ! Heating Maximum Air Flow per Zone Floor Area {m3/s-m2}
  ,                           ! Heating Maximum Air Flow {m3/s}
  ;                           ! Heating Maximum Air Flow Fraction

! ============ SURFACES ============
BUILDINGSURFACE:DETAILED,
  Perimeter_North_F1_Floor,
  Floor,
  FloorConstruction,
  Perimeter_North_F1,
  Ground,
  ,
  NoSun,
  NoWind,
  autocalculate,
  4,
  11.82, 6.57, 0.0,           ! REVERSED ORDER!
  11.82, 4.43, 0.0,
  0.0, 4.43, 0.0,
  0.0, 6.57, 0.0;

BUILDINGSURFACE:DETAILED,
  Perimeter_North_F1_Wall_North,
  Wall,
  WallConstruction,
  Perimeter_North_F1,
  Outdoors,
  ,
  SunExposed,
  WindExposed,
  autocalculate,
  4,
  0.0, 6.57, 0.0,
  11.82, 6.57, 0.0,
  11.82, 6.57, 2.7,
  0.0, 6.57, 2.7;

FENESTRATIONSURFACE:DETAILED,
  Perimeter_North_F1_Wall_North_Window,
  Window,
  WindowConstruction,
  Perimeter_North_F1_Wall_North,
  ,
  autocalculate,
  ,
  1,
  4,
  2.0, 6.57, 0.9,             ! Window vertices
  9.82, 6.57, 0.9,
  9.82, 6.57, 2.4,
  2.0, 6.57, 2.4;

! ============ INTERNAL LOADS ============
PEOPLE,
  Perimeter_North_F1_People,
  Perimeter_North_F1,
  OccupancySchedule,
  People/Area,
  ,
  0.05,                       ! People per Zone Floor Area {person/m2}
  ,
  0.3,
  AUTOSIZE,                   ! Activity Level Schedule Name
  3.82E-8,
  ,
  ,
  ,
  AdaptiveASH55;

LIGHTS,
  Perimeter_North_F1_Lights,
  Perimeter_North_F1,
  OccupancySchedule,
  LightingLevel,
  ,
  ,
  709.8,                      ! Lighting Level {W} = 10 W/m² × Area
  0.0,
  0.2,
  0.0,
  General;

ELECTRICEQUIPMENT,
  Perimeter_North_F1_Equipment,
  Perimeter_North_F1,
  OccupancySchedule,
  EquipmentLevel,
  ,
  ,
  354.9;                      ! Equipment Level {W} = 5 W/m² × Area

! ============ INFILTRATION ============
ZONEINFILTRATION:DESIGNFLOWRATE,
  Perimeter_North_F1_Infiltration,
  Perimeter_North_F1,
  AlwaysOn,
  AirChanges/Hour,
  ,
  ,
  ,
  0.6,                        ! Air Changes per Hour
  1.0,
  0.0,
  0.0,
  0.0;

! ============ HVAC SYSTEM ============
HVACTEMPLATE:THERMOSTAT,
  All Zones,
  ,
  20.0,
  ,
  26.0;

HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM,
  Perimeter_North_F1,
  All Zones,
  ,
  50.0,
  13.0,
  0.015,
  0.009,
  NoLimit,
  ,
  ,
  NoLimit,
  ,
  ,
  HeatingAvailability,
  CoolingAvailability,
  ConstantSupplyHumidityRatio,
  ,
  ConstantSupplyHumidityRatio;

! ============ OUTPUT VARIABLES ============
OUTPUT:VARIABLE, *, Zone Mean Air Temperature, Timestep;
OUTPUT:VARIABLE, *, Zone Air System Sensible Heating Energy, Hourly;
OUTPUT:VARIABLE, *, Zone Air System Sensible Cooling Energy, Hourly;

OUTPUT:TABLE:SUMMARYREPORTS, AllSummary;
OUTPUT:SQLITE, SimpleAndTabular;
```

---

**Letzte Änderung:** 2025-11-14
**Changelog:** Initial creation - IDF-Struktur vollständig dokumentiert
