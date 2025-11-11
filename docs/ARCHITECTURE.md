# Architektur-Dokumentation

## Übersicht

Das EnergyPlus Automation Tool ist modular aufgebaut und folgt dem Prinzip der Trennung von Belangen (Separation of Concerns). Die Architektur ermöglicht einfache Erweiterungen und Wartung.

## System-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│  (CLI, Scripts, Jupyter Notebooks, API - zukünftig)        │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────┐
│                    Core Modules                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Geometry   │  │  Materials   │  │    HVAC      │      │
│  │  Generator  │  │  & Construc. │  │  Generator   │      │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └─────────────────┴──────────────────┘               │
│                           │                                  │
│                  ┌────────▼────────┐                        │
│                  │  IDF Builder    │                        │
│                  │  (eppy/geomeppy)│                        │
│                  └────────┬────────┘                        │
│                           │                                  │
│         ┌─────────────────┴─────────────────┐               │
│         │                                    │               │
│  ┌──────▼──────┐                  ┌─────────▼────────┐     │
│  │ Simulation  │                  │  Configuration   │     │
│  │   Runner    │◄─────────────────┤    Manager       │     │
│  └──────┬──────┘                  └──────────────────┘     │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│               EnergyPlus Engine                              │
│  (External Process - energyplus.exe)                         │
└─────────┬────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│            Post-Processing Layer                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ SQL Parser │  │  CSV Parser│  │  Report    │            │
│  │            │  │            │  │  Generator │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└──────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│        Output Layer                                          │
│  (Results, Visualizations, Exports)                          │
└──────────────────────────────────────────────────────────────┘
```

## Modul-Beschreibungen

### 1. Geometry Module (`src/geometry/`)

**Zweck**: Automatisierte Erstellung von Gebäudegeometrien

**Komponenten**:
- `simple_box.py`: Generator für einfache quaderförmige Gebäude
- *Zukünftig*: `complex_shapes.py`, `ifc_import.py`, `gbxml_import.py`

**Abhängigkeiten**: eppy, geomeppy

**Schnittstellen**:
```python
class SimpleBoxGenerator:
    def create_model(geometry: BuildingGeometry) -> IDF
```

### 2. Materials Module (`src/materials/`)

**Zweck**: Verwaltung von Materialien und Konstruktionen

**Komponenten**:
- `standard_constructions.py`: Basis-Materialien und Konstruktionen
- *Zukünftig*: `tabula_database.py`, `iso_13790.py`, `custom_materials.py`

**Datenquellen**:
- TABULA WebTool
- ISO 13790 / EN 15459
- ASHRAE Standards
- Benutzerdefinierte Datenbanken

### 3. HVAC Module (`src/hvac/`)

**Zweck**: Generierung von HVAC-Systemen

**Status**: Aktuell nur IdealLoadsAirSystem

**Zukünftige Komponenten**:
- `templates/`: Vordefinierte HVAC-Templates
- `heat_pump.py`: Wärmepumpen-Systeme
- `ventilation.py`: Lüftungssysteme
- `radiator.py`: Heizkörper-Systeme

### 4. Simulation Module (`src/simulation/`)

**Zweck**: Verwaltung der EnergyPlus-Simulationen

**Komponenten**:
- `runner.py`: Haupt-Simulations-Engine

**Features**:
- Einzelne Simulation
- Batch-Simulationen (parallel)
- Error-Handling
- Progress-Tracking
- Ergebnis-Sammlung

**Workflow**:
```
IDF + EPW → Validation → EnergyPlus Process → Result Collection
```

### 5. Post-Processing Module (`src/postprocessing/`)

**Status**: In Entwicklung

**Geplante Komponenten**:
- `sql_parser.py`: SQLite-Ergebnis-Parser
- `kpi_calculator.py`: Kennzahlen-Berechnung
- `visualization.py`: Grafiken und Plots
- `report_generator.py`: Automatische Berichtserstellung

### 6. Utils Module (`src/utils/`)

**Komponenten**:
- `config.py`: Konfigurationsmanagement mit Pydantic

**Features**:
- YAML-basierte Konfiguration
- Validierung
- Umgebungsvariablen
- Auto-Erkennung von EnergyPlus

## Datenfluss

### Typischer Workflow

```
1. User Input
   ↓
2. BuildingGeometry Definition
   ↓
3. SimpleBoxGenerator.create_model()
   ├─ Materials & Constructions
   ├─ Zones & Surfaces
   ├─ Internal Loads
   └─ HVAC System
   ↓
4. IDF File Output
   ↓
5. EnergyPlusRunner.run_simulation()
   ├─ Validation
   ├─ EnergyPlus Process
   └─ Output Collection
   ↓
6. SimulationResult
   ↓
7. Post-Processing (optional)
   ↓
8. Results & Reports
```

### Batch-Simulation Workflow

```
1. Parameter Definition
   ↓
2. Model Generation Loop
   ├─ Variant 1 → IDF 1
   ├─ Variant 2 → IDF 2
   └─ Variant N → IDF N
   ↓
3. Parallel Execution
   ├─ Worker 1 ──► Simulation 1,4,7...
   ├─ Worker 2 ──► Simulation 2,5,8...
   └─ Worker N ──► Simulation 3,6,9...
   ↓
4. Result Aggregation
   ↓
5. Comparative Analysis
```

## Konfiguration

### Hierarchie

1. **Default Config** (`config/default_config.yaml`)
2. **User Config** (optional, z.B. `config/user_config.yaml`)
3. **Environment Variables** (optional, z.B. `ENERGYPLUS_INSTALL_DIR`)
4. **Runtime Parameters** (über Code)

### Pydantic Models

Alle Konfigurationen werden als Pydantic Models validiert:
- Type-Safety
- Automatische Validierung
- Dokumentation durch Type Hints

## Erweiterbarkeit

### 1. Neue Geometrie-Typen hinzufügen

```python
# src/geometry/l_shape.py
class LShapeGenerator:
    def create_model(self, geometry: LShapeGeometry) -> IDF:
        # Implementation
        pass
```

### 2. Neue Material-Datenbank

```python
# src/materials/tabula_database.py
class TABULADatabase:
    def load_building_type(self, country: str, type: str, age: str):
        # Load from TABULA
        pass

    def apply_to_idf(self, idf: IDF):
        # Apply materials
        pass
```

### 3. HVAC-Templates

```python
# src/hvac/heat_pump_template.py
def add_air_source_heat_pump(idf: IDF, zones: List[str]):
    # Add heat pump system
    pass
```

### 4. Co-Simulation (zukünftig)

```python
# src/cosimulation/fmu_interface.py
class FMUCosimulator:
    def connect_fmu(self, fmu_path: str):
        pass

    def run_cosimulation(self, idf_path: str):
        # FMI-basierte Co-Simulation
        pass
```

## Design-Patterns

### 1. Factory Pattern
Geometrie-Generatoren verwenden Factory Pattern für verschiedene Gebäudetypen.

### 2. Strategy Pattern
Verschiedene HVAC-Systeme als austauschbare Strategien.

### 3. Builder Pattern
IDF-Erstellung erfolgt schrittweise durch Builder.

### 4. Observer Pattern (zukünftig)
Für Progress-Updates und Event-Handling.

## Performance-Überlegungen

### Parallelisierung

- **Batch-Simulationen**: ProcessPoolExecutor für CPU-intensive Tasks
- **Anzahl Workers**: Standardmäßig 4, konfigurierbar
- **Memory Management**: Separate Prozesse vermeiden Memory-Leaks

### Optimierungen

1. **IDF-Caching**: Template-basierte Generierung
2. **Lazy Loading**: Ergebnisse nur bei Bedarf laden
3. **Streaming**: Große CSV-Dateien streamen statt vollständig laden

## Testing-Strategie

### Unit Tests
```python
# tests/test_geometry.py
def test_simple_box_creation():
    geometry = BuildingGeometry(...)
    generator = SimpleBoxGenerator()
    idf = generator.create_model(geometry)
    assert idf is not None
```

### Integration Tests
```python
# tests/test_simulation.py
def test_full_simulation_workflow():
    # Create model
    # Run simulation
    # Verify results
    pass
```

### Fixture-basiert
- Vordefinierte Test-IDFs
- Mock-Wetterdateien
- Erwartete Ergebnisse

## Security

### Subprocess-Sicherheit
- Validierung aller Pfade
- Timeout-Protection
- Sandboxing (optional, für Web-Deployment)

### Input-Validierung
- Pydantic für alle Inputs
- Range-Checks für physikalische Parameter
- Path-Validation

## Deployment

### Standalone
```bash
python examples/01_simple_box_simulation.py
```

### Docker (zukünftig)
```dockerfile
FROM python:3.10
# Install EnergyPlus
# Install dependencies
# ...
```

### Web-API (zukünftig)
```python
# FastAPI-based REST API
@app.post("/simulate")
async def simulate(building: BuildingGeometry):
    # Run simulation
    return results
```

## Roadmap

### Phase 1 (Aktuell) ✓
- Basis-Infrastruktur
- Simple Box Generator
- Simulation Runner
- Batch-Processing

### Phase 2 (Q1 2025)
- Post-Processing Module
- Erweiterte Geometrien (L-Form, U-Form)
- TABULA-Integration
- Detaillierte HVAC-Templates

### Phase 3 (Q2 2025)
- IFC/gbXML Import
- Co-Simulation (FMI/FMU)
- ML-Integration (Surrogate Models)
- Web-GUI

### Phase 4 (Q3 2025)
- Hardware-in-the-Loop
- Echtzeit-Simulation
- Optimierungs-Algorithmen
- Cloud-Deployment

## Weiterführende Ressourcen

- EnergyPlus Engineering Reference
- eppy Documentation
- TABULA WebTool
- FMI Standard
- ISO 13790 / ISO 52016
