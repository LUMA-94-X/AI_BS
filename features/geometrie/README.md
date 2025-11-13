# 🏗️ Geometrie-Feature - Architektur & Komponenten

Dieses Feature generiert EnergyPlus-Gebäudemodelle aus Energieausweis-Daten und expliziten Dimensionen.

---

## 📐 Übersicht

Das Geometrie-Feature transformiert **High-Level Building Data** (Energieausweis) in **detaillierte 3D EnergyPlus Modelle** für thermische Gebäudesimulation.

```
Energieausweis-Daten
        ↓
  [Geometry Solver]  ← Rekonstruiert Dimensionen
        ↓
  [Perimeter Calculator]  ← 5-Zonen Layout
        ↓
  [FiveZoneGenerator]  ← Erstellt IDF
        ↓
  EnergyPlus IDF File  → Simulation
```

---

## 🏛️ Layer-Architektur

Das Feature ist in **4 klare Schichten** organisiert:

| Layer | Verzeichnis | Zweck | Beispiele |
|-------|-------------|-------|-----------|
| **1. Input Models** | `models/` | Was der User gibt | `EnergieausweisInput`, `FensterData` |
| **2. Shared Types** | `types/` | Interne Datenstrukturen | `ZoneInfo`, `MetadataConfig` |
| **3. Utilities** | `utils/` | Berechnungen & Algorithmen | `GeometrySolver`, `PerimeterCalculator` |
| **4. Generators** | `generators/` | IDF-Erstellung | `FiveZoneGenerator` + Components |

---

## 📦 Layer 1: Input Models (`models/`)

**Zweck**: Domain-Modelle für User-Input

**Charakteristik**:
- ✅ Was der User **gibt** (Input)
- ✅ Validierung mit Pydantic
- ✅ Wiederverwendbar über Features

### Dateien

#### `energieausweis_input.py`
Zentrale Input-Datenstruktur für Energieausweis-basierte Generierung.

**Hauptklassen**:
```python
@dataclass
class EnergieausweisInput:
    """Gebäudedaten aus Energieausweis."""
    nettoflaeche_m2: float
    anzahl_geschosse: int
    geschosshoehe_m: float
    u_wert_wand: float
    u_wert_dach: float
    u_wert_boden: float
    u_wert_fenster: float
    fenster: FensterData
    gebaeudetyp: GebaeudeTyp
    # Optional: Hüllflächen für exakte Rekonstruktion
    wandflaeche_m2: Optional[float] = None
    dachflaeche_m2: Optional[float] = None
    ...
```

**Enums**:
- `GebaeudeTyp`: EFH, MFH, NWG
- `Orientation`: NORTH, EAST, SOUTH, WEST

**Factory Functions**:
- `create_example_efh()` - Beispiel Einfamilienhaus
- `create_example_mfh()` - Beispiel Mehrfamilienhaus

**Verwendung**:
```python
from features.geometrie.models import EnergieausweisInput, GebaeudeTyp

ea_data = EnergieausweisInput(
    nettoflaeche_m2=200.0,
    anzahl_geschosse=2,
    u_wert_wand=0.30,
    gebaeudetyp=GebaeudeTyp.EFH,
    ...
)
```

---

## 🎯 Layer 2: Shared Types (`types/`)

**Zweck**: Interne Datenstrukturen für Output & State

**Charakteristik**:
- ✅ Was Generatoren **zurückgeben** (Output)
- ✅ Wiederverwendbar über verschiedene Generatoren
- ✅ Typsicherheit für Datenflüsse

### Dateien

#### `generator_types.py`
Alle wiederverwendbaren Types für IDF-Generierung.

**Zone Types**:
```python
@dataclass
class ZoneInfo:
    """Metadaten über erstellte Zone."""
    name: str              # "Perimeter_North_F1"
    floor: int             # 0-basiert
    floor_area: float      # m²
    volume: float          # m³
    z_origin: float        # Z-Koordinate
    idf_object: Any        # eppy ZONE object
```

**Surface Types**:
```python
@dataclass
class SurfaceInfo:
    """Metadaten über erstellte Surface."""
    name: str
    zone_name: str
    surface_type: str      # Wall, Floor, Ceiling, Roof
    outside_boundary_condition: str
    boundary_object: Optional[str]
    area: float
    has_window: bool

@dataclass
class WindowInfo:
    """Metadaten über erstelltes Fenster."""
    name: str
    parent_surface: str
    area: float
    wwr: float
    orientation: str
```

**Configuration Types**:
```python
@dataclass
class MetadataConfig:
    """Simulation-Settings Konfiguration."""
    timestep: int = 4
    run_period_start: str = "01/01"
    run_period_end: str = "12/31"
    include_design_days: bool = True
    warmup_days: int = 25
    building_name: str = "5Zone_Building_From_Energieausweis"
    terrain: str = "Suburbs"

@dataclass
class OutputConfig:
    """Output-Variablen Konfiguration."""
    variables: List[OutputVariable]
    include_sqlite: bool = True
    include_html: bool = False

    @classmethod
    def standard_outputs(cls) -> 'OutputConfig':
        """Temperature + Energy."""

    @classmethod
    def minimal_outputs(cls) -> 'OutputConfig':
        """Nur Temperature."""

    @classmethod
    def detailed_outputs(cls) -> 'OutputConfig':
        """Inkl. Humidity, Surface Temps."""
```

**Location Types**:
```python
@dataclass
class LocationData:
    """Geografische Standort-Daten."""
    name: str = "Salzburg"
    latitude: float = 47.8
    longitude: float = 13.05
    time_zone: float = 1.0
    elevation: float = 430.0
```

**Result Types**:
```python
@dataclass
class GenerationResult:
    """Ergebnis einer IDF-Generierung."""
    idf: Any
    zones: List[ZoneInfo]
    num_surfaces: int
    num_windows: int
    warnings: List[str]
    output_path: Optional[Path]
```

**Verwendung**:
```python
from features.geometrie.types import (
    ZoneInfo,
    MetadataConfig,
    OutputConfig
)

# Generator gibt ZoneInfo zurück:
zone_infos: List[ZoneInfo] = zone_gen.add_zones(idf, layouts)

# Konfiguration übergeben:
config = MetadataConfig(timestep=6, building_name="My_Building")
metadata_gen = MetadataGenerator(config)
```

---

## 🧮 Layer 3: Utilities (`utils/`)

**Zweck**: Wiederverwendbare Berechnungen & Algorithmen

**Charakteristik**:
- ✅ Stateless (Pure Functions wo möglich)
- ✅ Unabhängig von Generator-Typ
- ✅ Gut testbar

### Dateien

#### `geometry_solver.py`
**Zweck**: Rekonstruiert 3D-Gebäudedimensionen aus Energieausweis-Daten

**Methoden**: Exact, Heuristic, Fallback (nach Daten-Verfügbarkeit)

**Klassen**:
```python
class GeometrySolver:
    def solve(self, ea_data: EnergieausweisInput) -> GeometrySolution:
        """Berechnet Länge, Breite, Höhe aus Nettofläche + Hüllflächen."""
```

**Output**:
```python
@dataclass
class GeometrySolution:
    length: float          # Gebäudelänge
    width: float           # Gebäudebreite
    height: float          # Gesamt-Höhe
    num_floors: int
    confidence: float      # 0-1 (1 = exakte Daten)
    method: SolutionMethod # EXACT, HEURISTIC, FALLBACK
    warnings: List[str]

    # Berechnete Properties:
    floor_height: float
    floor_area: float
    aspect_ratio: float
    av_ratio: float        # A/V-Verhältnis (Kompaktheit)
```

**Verwendung**:
```python
solver = GeometrySolver()
solution = solver.solve(ea_data)

print(f"Gebäude: {solution.length}m × {solution.width}m × {solution.height}m")
print(f"Konfidenz: {solution.confidence:.0%}")
```

---

#### `perimeter_calculator.py`
**Zweck**: Erstellt 5-Zonen Perimeter+Core Layout

**Konzept**: Adaptive Perimeter-Tiefe basierend auf Window-Wall-Ratio

**Klassen**:
```python
@dataclass
class ZoneGeometry:
    """3D-Geometrie einer Zone."""
    name: str
    x_origin: float
    y_origin: float
    z_origin: float
    length: float
    width: float
    height: float

    # Properties:
    floor_area: float
    volume: float
    vertices_2d: List[Tuple[float, float]]

@dataclass
class ZoneLayout:
    """5-Zonen Layout für ein Geschoss."""
    perimeter_north: ZoneGeometry
    perimeter_east: ZoneGeometry
    perimeter_south: ZoneGeometry
    perimeter_west: ZoneGeometry
    core: ZoneGeometry
    all_zones: Dict[str, ZoneGeometry]

    perimeter_depth: float
    perimeter_fraction: float  # Anteil Perimeter vs Core
    total_floor_area: float

class PerimeterCalculator:
    def create_zone_layout(
        self,
        building_length: float,
        building_width: float,
        floor_height: float,
        floor_number: int,
        wwr: float
    ) -> ZoneLayout:
        """Erstellt 5-Zonen Layout für ein Geschoss."""

    def create_multi_floor_layout(
        self, ..., num_floors: int
    ) -> Dict[int, ZoneLayout]:
        """Erstellt Layouts für mehrere Geschosse."""
```

**Perimeter-Tiefe Regel**:
```python
# Adaptive basierend auf WWR (Window-Wall-Ratio):
# WWR 10% → 3.0m Tiefe (wenig Tageslicht)
# WWR 30% → 4.5m Tiefe (Standard)
# WWR 50% → 6.0m Tiefe (viel Tageslicht)
```

**Verwendung**:
```python
calc = PerimeterCalculator()

layouts = calc.create_multi_floor_layout(
    building_length=12.0,
    building_width=10.0,
    floor_height=3.0,
    num_floors=2,
    wwr=0.30
)

# layouts = {0: ZoneLayout, 1: ZoneLayout}
for floor, layout in layouts.items():
    print(f"Floor {floor}: {len(layout.all_zones)} zones")
```

---

#### `fenster_distribution.py`
**Zweck**: Verteilt Fensterflächen auf Orientierungen

**Klassen**:
```python
@dataclass
class OrientationWWR:
    """Window-Wall-Ratio pro Orientierung."""
    north: float
    east: float
    south: float
    west: float
    average: float  # Property

class FensterDistribution:
    # Heuristiken für Gebäudetypen:
    HEURISTIC_DISTRIBUTIONS = {
        GebaeudeTyp.EFH: {
            "north": 0.15,   # Weniger Fenster
            "east": 0.30,
            "south": 0.45,   # Meiste Fenster (Süd-Orientierung)
            "west": 0.25
        },
        GebaeudeTyp.MFH: {...},
        GebaeudeTyp.NWG: {...}
    }

    def calculate_orientation_wwr(
        self,
        fenster_data: FensterData,
        wall_areas: Dict[str, float],
        gebaeudetyp: GebaeudeTyp
    ) -> OrientationWWR:
        """Berechnet WWR pro Orientierung."""
```

**Modi**:
1. **Exakt**: Wenn `fenster_data.nord_m2` etc. gegeben
2. **Heuristisch**: Wenn nur `window_wall_ratio` gegeben (nutzt Typ-Verteilung)

**Verwendung**:
```python
dist = FensterDistribution()

orientation_wwr = dist.calculate_orientation_wwr(
    fenster_data=ea_data.fenster,
    wall_areas={"north": 50, "east": 40, "south": 50, "west": 40},
    gebaeudetyp=GebaeudeTyp.EFH
)

print(f"Süd-WWR: {orientation_wwr.south:.0%}")  # z.B. 45%
```

---

## 🏭 Layer 4: Generators (`generators/`)

**Zweck**: Erstellt EnergyPlus IDF-Dateien

**Charakteristik**:
- ✅ Orchestriert Utilities
- ✅ Nutzt Components für Modularität
- ✅ Public API für User

### Struktur

```
generators/
├── five_zone_generator.py      # Hauptgenerator (Orchestrator)
│
└── components/                  # Wiederverwendbare Bausteine
    ├── eppy_workarounds.py      # EppyBugFixer
    ├── metadata.py              # MetadataGenerator
    ├── zones.py                 # ZoneGenerator
    ├── materials.py             # MaterialsGenerator
    └── surfaces.py              # SurfaceGenerator (Phase 3)
```

---

### `five_zone_generator.py`

**Zweck**: Hauptgenerator - 5-Zonen Perimeter+Core Modell

**Public API**:
```python
class FiveZoneGenerator:
    def create_from_energieausweis(
        self,
        ea_data: EnergieausweisInput,
        output_path: Optional[Path] = None
    ) -> IDF:
        """Erstellt IDF aus Energieausweis-Daten."""

    def create_from_explicit_dimensions(
        self,
        building_length: float,
        building_width: float,
        floor_height: float,
        num_floors: int,
        ea_data: EnergieausweisInput,
        output_path: Optional[Path] = None
    ) -> IDF:
        """Erstellt IDF mit expliziten Dimensionen (umgeht Solver)."""
```

**Interner Workflow** (`create_from_energieausweis`):
```python
def create_from_energieausweis(self, ea_data, output_path):
    # 1. Geometrie rekonstruieren
    geo_solution = self.geometry_solver.solve(ea_data)
    layouts = self.perimeter_calc.create_multi_floor_layout(...)
    orientation_wwr = self.fenster_dist.calculate_orientation_wwr(...)

    # 2. IDF initialisieren
    idf = self._initialize_idf()

    # 3. DELEGIERT an Components:
    self.materials_gen.add_constructions_from_u_values(idf, ea_data)
    self.metadata_gen.add_simulation_settings(idf, geo_solution)
    self.metadata_gen.add_site_location(idf)

    zone_infos = self.zone_gen.add_zones(idf, layouts)

    # 4. Surfaces (noch nicht extrahiert - Phase 3)
    self._add_surfaces_5_zone(idf, layouts, geo_solution, orientation_wwr)

    # 5. Loads & HVAC
    schedules = self._add_schedules(idf, ea_data.gebaeudetyp)
    self._add_internal_loads(idf, layouts, ea_data.gebaeudetyp, schedules)
    self._add_infiltration(idf, layouts, ea_data.effective_infiltration)
    self._add_hvac_system(idf)

    self.metadata_gen.add_output_variables(idf)

    # 6. Save mit eppy Bug-Fix
    if output_path:
        boundary_map = self.eppy_fixer.collect_boundary_map(idf)
        idf.save(str(output_path))
        self.eppy_fixer.fix_eppy_boundary_objects(boundary_map, output_path)

    return idf
```

**Verwendung**:
```python
from features.geometrie.generators import FiveZoneGenerator
from features.geometrie.models import create_example_efh

ea_data = create_example_efh()

generator = FiveZoneGenerator()
idf = generator.create_from_energieausweis(
    ea_data=ea_data,
    output_path=Path("output/building.idf")
)

# IDF ist ready für EnergyPlus Simulation!
```

---

### Components (`generators/components/`)

Wiederverwendbare Bausteine für IDF-Generierung.

**Siehe**: `components/README.md` für Details

#### 1. **EppyBugFixer** (`eppy_workarounds.py`)
- Korrigiert bekannte eppy Bugs
- **Kritisch** für inter-zone thermal coupling
- Wiederverwendbar für JEDEN IDF-Generator

#### 2. **MetadataGenerator** (`metadata.py`)
- Simulation Settings (Timestep, RunPeriod, Design Days)
- Site:Location
- Output Variables (mit Presets)

#### 3. **ZoneGenerator** (`zones.py`)
- Erstellt ZONE-Objekte aus ZoneLayout
- Returns `List[ZoneInfo]` für Tracking

#### 4. **MaterialsGenerator** (`materials.py`)
- Phase 1: Wrapper um Standard-Konstruktionen
- Phase 2+: U-Wert → Dämmstoffdicke Berechnung (geplant)

#### 5. **SurfaceGenerator** (`surfaces.py`) - **Phase 3 - TODO**
- Erstellt Walls, Floors, Ceilings, Roofs, Windows
- Komplex: 615 Zeilen, Vertex-Ordering, Boundary-Pairs

---

## 🔄 Datenfluss-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INPUT (Layer 1)                        │
│  EnergieausweisInput (models/energieausweis_input.py)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              GEOMETRY RECONSTRUCTION (Layer 3)                  │
│  ┌──────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │ GeometrySolver   │→ │PerimeterCalc    │→ │FensterDist     │ │
│  │ solve()          │  │ create_layouts()│  │ calc_wwr()     │ │
│  └──────────────────┘  └─────────────────┘  └────────────────┘ │
│         ↓                      ↓                     ↓          │
│  GeometrySolution    Dict[int, ZoneLayout]   OrientationWWR    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              IDF GENERATION (Layer 4)                           │
│                  FiveZoneGenerator                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Components (generators/components/):                     │  │
│  │  • MaterialsGenerator    → Materials/Constructions       │  │
│  │  • MetadataGenerator     → Settings/Location/Outputs     │  │
│  │  • ZoneGenerator         → ZONE objects → ZoneInfo       │  │
│  │  • SurfaceGenerator      → Walls/Floors/Windows          │  │
│  │  • EppyBugFixer          → Post-Save Corrections         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   OUTPUT (Layer 2 Types)                        │
│  • IDF File (EnergyPlus)                                        │
│  • List[ZoneInfo] (Metadaten)                                   │
│  • GenerationResult (Optional)                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing

### Test-Strategie

| Test-Typ | Wo | Was |
|----------|-----|-----|
| **Unit Tests** | `tests/geometrie/utils/` | GeometrySolver, PerimeterCalc einzeln |
| **Component Tests** | `tests/geometrie/generators/components/` | Jede Component isoliert |
| **Integration Tests** | `tests/geometrie/generators/` | Vollständige IDF-Generierung |

### Bestehende Tests

- `test_geometry_solver.py` - GeometrySolver (5 Tests)
- `test_sprint2_modules.py` - PerimeterCalc, FensterDist (6 Tests)
- `test_five_zone_integration.py` - **FiveZoneGenerator (12 Tests)** ✅

**Beispiel Integration Test**:
```python
def test_single_floor_efh_generation():
    generator = FiveZoneGenerator()
    ea_data = EnergieausweisInput(...)

    idf = generator.create_from_energieausweis(ea_data, output_path)

    # Validierungen:
    assert output_path.exists()
    assert len(idf.idfobjects['ZONE']) == 5
    assert len(idf.idfobjects['BUILDINGSURFACE:DETAILED']) > 0
    assert len(idf.idfobjects['PEOPLE']) == 5
    ...
```

---

## 📊 Metriken & Performance

### Code-Größe (nach Phase 1-2 Refactoring)

| Komponente | Zeilen | Zweck |
|------------|--------|-------|
| `five_zone_generator.py` | ~400 | Orchestrator |
| `components/eppy_workarounds.py` | 100 | Bug-Fixes |
| `components/metadata.py` | 150 | Settings |
| `components/zones.py` | 80 | Zonen |
| `components/materials.py` | 50 | Materials |
| `types/generator_types.py` | 250 | Dataclasses |
| **GESAMT** | **~1030** | (vorher: 1379) |

**Reduktion**: -25% durch Deduplizierung & Modularität

### Performance

| Operation | Zeit | Bemerkung |
|-----------|------|-----------|
| GeometrySolver.solve() | <10ms | Analytisch |
| PerimeterCalculator (5 zones) | <5ms | Geometrie-Calc |
| FiveZoneGenerator (1 floor) | ~300ms | IDF Creation |
| FiveZoneGenerator (10 floors) | ~1.5s | Linear scaling |

---

## 🚀 Erweiterbarkeit

### Neue Generatoren hinzufügen

**Beispiel**: SimpleBoxGenerator (single thermal zone)

```python
from features.geometrie.types import ZoneInfo, MetadataConfig
from features.geometrie.generators.components import (
    MetadataGenerator,
    MaterialsGenerator,
    EppyBugFixer
)

class SimpleBoxGenerator:
    """Single-Zone Box Generator."""

    def __init__(self):
        # REUSE existing components! ✅
        self.metadata_gen = MetadataGenerator(MetadataConfig())
        self.materials_gen = MaterialsGenerator()
        self.eppy_fixer = EppyBugFixer()

    def create_model(self, geometry: BuildingGeometry) -> IDF:
        idf = IDF()

        # Reuse components:
        self.materials_gen.add_constructions_from_u_values(idf, ea_data)
        self.metadata_gen.add_simulation_settings(idf, None)

        # Custom zone logic:
        zone = idf.newidfobject("ZONE", Name="SingleZone", ...)

        # ...custom surfaces...

        # Reuse eppy fix:
        boundary_map = self.eppy_fixer.collect_boundary_map(idf)
        idf.save(path)
        self.eppy_fixer.fix_eppy_boundary_objects(boundary_map, path)

        return idf
```

**Wiederverwendete Components**:
- ✅ EppyBugFixer (kritisch!)
- ✅ MetadataGenerator
- ✅ MaterialsGenerator

**Eigene Logik**:
- Zones (1 statt 5)
- Surfaces (Simple Box)

---

### Neue Building Types hinzufügen

**In** `models/energieausweis_input.py`:
```python
class GebaeudeTyp(str, Enum):
    EFH = "residential_efh"
    MFH = "residential_mfh"
    NWG = "non_residential"
    OFFICE = "office"  # ← NEU
```

**In** `features/internal_loads/native_loads.py`:
```python
BUILDING_TYPES = {
    GebaeudeTyp.OFFICE: {
        "people_density": 0.05,    # people/m² (höher als residential)
        "lights_density": 12.0,     # W/m²
        "equipment_density": 15.0,  # W/m² (Computer, etc.)
        ...
    }
}
```

**In** `utils/fenster_distribution.py`:
```python
HEURISTIC_DISTRIBUTIONS = {
    GebaeudeTyp.OFFICE: {
        "north": 0.40,  # Büros: Viel Tageslicht
        "east": 0.40,
        "south": 0.40,
        "west": 0.40    # Gleichmäßig verteilt
    }
}
```

---

## 📚 Dependencies

### External
- `eppy` - EnergyPlus IDF manipulation
- `pydantic` - Data validation (models/)

### Internal
- `core.config` - Global configuration
- `core.materialien` - Standard construction library
- `features.internal_loads.native_loads` - Internal loads manager
- `features.hvac.ideal_loads` - HVAC templates

---

## 🛣️ Roadmap

### ✅ Phase 1-2 (Abgeschlossen)
- Baseline Tests (12 Tests)
- Dataclasses (types/)
- Components extracted: EppyBugFixer, MetadataGenerator, ZoneGenerator, MaterialsGenerator
- Refactored Orchestrator

### 🚧 Phase 3 (Geplant)
- **SurfaceGenerator** extrahieren (~615 Zeilen)
- `SurfaceInfo`, `WindowInfo` dataclasses
- Unit-Tests für:
  - Vertex ordering validation
  - Boundary pair consistency
  - Window placement algorithm

### 🔮 Phase 4+ (Zukunft)
- U-Wert → Construction Generator (MaterialsGenerator Phase 2)
- Template Library (YAML-based)
- Parametric Studies Support
- Validation Framework
- Performance Optimizations (Template caching)

---

## 🤝 Contributions

### Code-Style
- **Imports**: Absolute imports bevorzugt
- **Type Hints**: Pflicht für Public API
- **Docstrings**: Google-Style für Klassen/Methoden
- **Tests**: Für jede neue Component/Feature

### Adding Components
1. Create in `generators/components/`
2. Add to `components/__init__.py`
3. Update `components/README.md`
4. Write unit tests
5. Update this README (Datenfluss-Diagramm)

---

## 📞 Support & Fragen

**Issues**: GitHub Issues für Bugs/Features
**Dokumentation**: Siehe `components/README.md` für Details zu Components
**Tests**: `pytest tests/geometrie/ -v` für alle Tests

---

**Letzte Aktualisierung**: 2025-11-13
**Version**: Phase 1-2 Refactoring
**Status**: ✅ Production Ready
