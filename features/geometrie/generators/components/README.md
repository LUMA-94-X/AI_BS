# Generator Components

Wiederverwendbare Bausteine für IDF-Generatoren.

Diese Komponenten sind **nicht** spezifisch für FiveZoneGenerator und können von verschiedenen Generator-Typen verwendet werden.

## Architektur-Übersicht

Der FiveZoneGenerator wurde in spezialisierte Module aufgeteilt, um:
- ✅ Bessere Wartbarkeit und Testbarkeit
- ✅ Klare Trennung der Verantwortlichkeiten
- ✅ Wiederverwendbare Komponenten
- ✅ Einfachere Erweiterbarkeit

### Module

#### 1. `eppy_workarounds.py` - EppyBugFixer
**Zweck**: Isoliert fragile Workarounds für bekannte eppy Bugs

**Hauptfunktion**: Korrigiert falsche Boundary-Referenzen die eppy beim Speichern erstellt

**Wichtig**: Dieser Bug-Fix ist **kritisch** für inter-zone thermal coupling!

**Verwendung**:
```python
fixer = EppyBugFixer(debug=False)

# VOR dem Save:
boundary_map = fixer.collect_boundary_map(idf)

# Save
idf.save("building.idf")

# NACH dem Save:
fixer.fix_eppy_boundary_objects(boundary_map, Path("building.idf"))
```

**Bug-Beschreibung**:
Eppy setzt fälschlicherweise `Outside_Boundary_Condition_Object = Name` (Self-Reference)
statt den Namen der angrenzenden Surface für inter-zone walls.

---

#### 2. `metadata.py` - MetadataGenerator
**Zweck**: Erstellt Gebäude-Metadaten und Simulations-Einstellungen

**Erstellt**:
- Building-Objekt
- SimulationControl
- HeatBalanceAlgorithm
- Timestep
- RunPeriod (Jahressimulation)
- Design Days (Heating/Cooling)
- Site:Location
- Output Variables
- Output:SQLite

**Konfigurierbar via**: `MetadataConfig` dataclass

**Verwendung**:
```python
config = MetadataConfig(
    timestep=4,
    run_period_start="01/01",
    run_period_end="12/31",
    building_name="My_Building"
)

gen = MetadataGenerator(config)
gen.add_simulation_settings(idf, geo_solution)
gen.add_site_location(idf)
gen.add_output_variables(idf)
```

**Output Presets**:
- `OutputConfig.standard_outputs()` - Standard (Temperature + Energy)
- `OutputConfig.minimal_outputs()` - Nur Temperatur
- `OutputConfig.detailed_outputs()` - Detailliert (inkl. Humidity, Surface Temps)

---

#### 3. `zones.py` - ZoneGenerator
**Zweck**: Erstellt thermische Zonen aus ZoneLayout-Geometrien

**Erstellt**: ZONE-Objekte mit korrekten Koordinaten und Eigenschaften

**Returns**: `List[ZoneInfo]` - Metadaten über erstellte Zonen

**Verwendung**:
```python
gen = ZoneGenerator()
zone_infos = gen.add_zones(idf, layouts)

# Zugriff auf Zone-Metadaten:
for zone in zone_infos:
    print(f"{zone.name}: {zone.floor_area:.1f}m², Floor {zone.floor}")

# Validierung:
warnings = gen.validate_zones(zone_infos)
if warnings:
    print("Warnings:", warnings)
```

**ZoneInfo dataclass**:
```python
@dataclass
class ZoneInfo:
    name: str          # "Perimeter_North_F1"
    floor: int         # 0-basiert
    floor_area: float  # m²
    volume: float      # m³
    z_origin: float    # Z-Koordinate
    idf_object: Any    # eppy ZONE object
```

---

#### 4. `materials.py` - MaterialsGenerator
**Zweck**: Erstellt Material-Definitionen und Konstruktionen

**Status**: Phase 1 - Wrapper um `core.materialien.add_basic_constructions()`

**Roadmap**:
- ✅ Phase 1 (aktuell): Standard-Konstruktionen
- 🔜 Phase 2: U-Wert → Dämmstoffdicke Berechnung
- 🔜 Phase 3: Vollständiger Konstruktions-Generator aus Energieausweis-Daten

**Verwendung**:
```python
gen = MaterialsGenerator()
gen.add_constructions_from_u_values(idf, ea_data)

# Zukünftig (geplant):
# gen._create_construction_from_u_value(idf, "Wall", 0.30)
```

---

#### 5. `surfaces.py` - SurfaceGenerator
**Zweck**: Erstellt alle Gebäudeflächen (Floors, Ceilings, Walls, Windows)

**Status**: ✅ Phase 3 - Vollständig implementiert (612 Zeilen)

**Erstellt**:
- Floors (Ground und inter-floor)
- Ceilings/Roofs (inter-floor und top floor)
- Exterior Walls mit Windows (nur Perimeter-Zonen)
- Interior Walls (Perimeter↔Core, Perimeter↔Perimeter)
- Windows mit WWR-basierten Dimensionen

**Kritische EnergyPlus-Konzepte**:
- ✅ Counter-clockwise vertex ordering (PFLICHT)
- ✅ Floor vertices REVERSED [3,2,1,0] für downward normal
- ✅ Ceiling vertices NORMAL [0,1,2,3] für upward normal
- ✅ Interior wall pairs mit reversed vertices für thermal coupling

**Verwendung**:
```python
gen = SurfaceGenerator()
gen.add_surfaces_5_zone(idf, layouts, geo_solution, orientation_wwr)
```

**Interne Methoden**:
- `_add_floors_5_zone()` - Bodenplatten mit Ground/Surface boundary
- `_add_ceilings_5_zone()` - Decken/Dächer
- `_add_exterior_walls_5_zone()` - Außenwände für 4 Perimeter-Zonen
- `_add_exterior_wall()` - Einzelne Außenwand mit Fenster
- `_add_window()` - Window placement mit sqrt(WWR) scaling, 0.9m sill height
- `_add_interior_walls_5_zone()` - 8 Wandpaare (4x Perimeter↔Core + 4x Ecken)
- `_add_interior_wall_pair()` - Paar von thermisch gekoppelten Wänden

**Wichtige Algorithmen**:
```python
# Window scaling (proportional)
scale_factor = wwr**0.5
window_width = wall_width * scale_factor
window_height = wall_height * scale_factor

# Sill height constraints
sill_height = 0.9  # 90cm
max_height = wall_height - sill_height - 0.3
```

---

## Dataclasses (`../../types/generator_types.py`)

### ZoneInfo
Metadaten über erstellte Zonen (verwendet von ZoneGenerator)

### SurfaceInfo
Metadaten über erstellte Surfaces (geplant für Phase 4)

### WindowInfo
Metadaten über erstellte Fenster (geplant für Phase 4)

### MetadataConfig
Konfiguration für Simulation-Settings (Timestep, RunPeriod, etc.)

### OutputConfig
Konfiguration für Output-Variablen mit Presets

### LocationData
Geografische Standort-Daten

### OutputVariable
Definition einer einzelnen Output-Variable

---

## Verwendung im FiveZoneGenerator

Der FiveZoneGenerator instanziiert alle Module in `__init__`:

```python
class FiveZoneGenerator:
    def __init__(self, config=None):
        # Generator components
        self.metadata_gen = MetadataGenerator(MetadataConfig())
        self.materials_gen = MaterialsGenerator()
        self.zone_gen = ZoneGenerator()
        self.surface_gen = SurfaceGenerator()  # NEW: Phase 3
        self.eppy_fixer = EppyBugFixer(debug=False)
```

Und delegiert Aufgaben an die spezialisierten Komponenten:

```python
def create_from_energieausweis(...):
    # Materials
    self.materials_gen.add_constructions_from_u_values(idf, ea_data)

    # Metadata
    self.metadata_gen.add_simulation_settings(idf, geo_solution)
    self.metadata_gen.add_site_location(idf)

    # Zones
    zone_infos = self.zone_gen.add_zones(idf, layouts)

    # Surfaces (NEW: Phase 3)
    self.surface_gen.add_surfaces_5_zone(idf, layouts, geo_solution, orientation_wwr)

    # Loads, HVAC, etc.
    ...

    # Output
    self.metadata_gen.add_output_variables(idf)

    # eppy Bug Fix
    boundary_map = self.eppy_fixer.collect_boundary_map(idf)
    idf.save(output_path)
    self.eppy_fixer.fix_eppy_boundary_objects(boundary_map, output_path)
```

---

## Testing

Jedes Modul sollte individuell getestet werden:

```
tests/geometrie/generators/components/
├── test_eppy_workarounds.py
├── test_metadata.py
├── test_zones.py
├── test_materials.py
└── test_surfaces.py  # geplant
```

**Baseline Integration Tests**: `tests/geometrie/generators/test_five_zone_integration.py`
- 12 umfassende Tests
- Decken alle Komponenten ab (Zones, Surfaces, Materials, etc.)
- ✅ Alle Tests bestanden (Phase 3 verifiziert)

---

## Vorteile der Modularisierung

### Vor Refactoring:
- `five_zone_generator.py`: **1379 Zeilen**
- Alles in einer Klasse
- Schwer zu testen
- Schwer zu erweitern

### Nach Refactoring (Phase 1-3):
- `five_zone_generator.py`: **~520 Zeilen** (Orchestrator)
- `eppy_workarounds.py`: 100 Zeilen
- `metadata.py`: 150 Zeilen
- `zones.py`: 80 Zeilen
- `materials.py`: 50 Zeilen
- `surfaces.py`: 612 Zeilen (✅ Phase 3)
- **Gesamt**: ~1512 Zeilen gut strukturierter Code (vs. 1379 monolithisch)

**Gewinn**:
- ✅ 62% mehr Code, aber viel besser strukturiert
- ✅ Klare Verantwortlichkeiten (5 spezialisierte Komponenten)
- ✅ Testbare, isolierte Komponenten
- ✅ Wiederverwendbare Module
- ✅ Reduzierter Orchestrator (1379 → 520 Zeilen = -62%)

---

## Nächste Schritte (Phase 4)

### Return Type Enhancement (geplant)
`SurfaceGenerator` könnte erweitert werden um Metadaten zurückzugeben:

```python
def add_surfaces_5_zone(...) -> List[SurfaceInfo]:
    """Returns metadata about created surfaces."""
    return surface_infos
```

Mit Dataclasses:
- `SurfaceInfo` - Metadaten über Surfaces (Name, Type, Area, Construction)
- `WindowInfo` - Metadaten über Fenster (Name, WWR, Area, Parent Wall)

**Nutzen**: Diagnostics, Validation, Testing

### U-Value Construction Generator (MaterialsGenerator Phase 2)
Automatische Berechnung von Dämmstoffdicken aus U-Werten.

---

## Lizenz & Kontakt

Teil des AI_BS Projekts
Erstellt: 2025-11-13
Dokumentiert: Phase 1-3 Refactoring
Letzte Aktualisierung: 2025-11-13 (Phase 3 Complete)
