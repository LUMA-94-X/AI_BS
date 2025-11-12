# 🏗️ Architecture Proposal: Modular IDF Generator

## Current Problem
`FiveZoneGenerator.generate()` ist monolithisch:
- ~2000 Zeilen in einer Funktion
- Abhängigkeiten zwischen Objekten unklar
- Schwer zu debuggen (wo genau schlägt was fehl?)
- Template-Loading vermischt mit Object-Creation

## Proposed Solution: Separate Core-Object Functions

### 1. Split into Modular Functions

```python
class FiveZoneGenerator:

    def generate(self) -> IDF:
        """Main orchestrator - calls sub-generators in correct order."""
        idf = IDF()

        # 1. Metadata (no dependencies)
        self._generate_metadata(idf)

        # 2. Materials & Constructions (no dependencies)
        self._generate_materials(idf)

        # 3. Schedules (no dependencies)
        schedules = self._generate_schedules(idf)

        # 4. Zones (needs Metadata)
        zones = self._generate_zones(idf)

        # 5. Surfaces (needs Zones + Constructions)
        surfaces = self._generate_surfaces(idf, zones)

        # 6. Fenestration (needs Surfaces)
        self._generate_fenestration(idf, surfaces)

        # 7. Internal Loads (needs Zones + Schedules)
        self._generate_internal_loads(idf, zones, schedules)

        # 8. HVAC (needs Zones)
        self._generate_hvac(idf, zones)

        return idf

    def _generate_metadata(self, idf: IDF) -> None:
        """Generate BUILDING, SIMULATIONCONTROL, TIMESTEP, etc."""
        pass

    def _generate_materials(self, idf: IDF) -> None:
        """Generate MATERIAL and CONSTRUCTION objects."""
        pass

    def _generate_schedules(self, idf: IDF) -> Dict[str, str]:
        """Generate SCHEDULETYPELIMITS and SCHEDULE:COMPACT objects.
        Returns: Dict mapping schedule type to schedule name.
        """
        pass

    def _generate_zones(self, idf: IDF) -> List[ZoneInfo]:
        """Generate ZONE objects.
        Returns: List of zone information for dependent objects.
        """
        pass

    def _generate_surfaces(self, idf: IDF, zones: List[ZoneInfo]) -> List[SurfaceInfo]:
        """Generate BUILDINGSURFACE:DETAILED objects.
        Returns: List of surface information for fenestration.
        """
        pass

    def _generate_fenestration(self, idf: IDF, surfaces: List[SurfaceInfo]) -> None:
        """Generate FENESTRATIONSURFACE:DETAILED objects."""
        pass

    def _generate_internal_loads(
        self,
        idf: IDF,
        zones: List[ZoneInfo],
        schedules: Dict[str, str]
    ) -> None:
        """Generate PEOPLE, LIGHTS, ELECTRICEQUIPMENT objects.
        Uses template-based approach for consistency.
        """
        pass

    def _generate_hvac(self, idf: IDF, zones: List[ZoneInfo]) -> None:
        """Generate HVACTEMPLATE objects.
        Uses template-based approach for consistency.
        """
        pass
```

### 2. Data Classes for Information Flow

```python
@dataclass
class ZoneInfo:
    """Information about a generated zone."""
    name: str
    floor: int
    area: float
    volume: float
    multiplier: int

@dataclass
class SurfaceInfo:
    """Information about a generated surface."""
    name: str
    zone_name: str
    surface_type: str  # Wall, Floor, Ceiling
    area: float
    orientation: Optional[str]  # North, East, South, West
```

### 3. Benefits

#### ✅ Testability
```python
# Test einzelne Funktionen isoliert
def test_generate_schedules():
    idf = IDF()
    schedules = generator._generate_schedules(idf)
    assert "occupancy" in schedules
    assert len(idf.idfobjects["SCHEDULE:COMPACT"]) > 0
```

#### ✅ Debugging
```python
# Genau wissen wo Fehler auftritt
try:
    surfaces = self._generate_surfaces(idf, zones)
except Exception as e:
    logger.error(f"Failed in _generate_surfaces: {e}")
    # Nur Surfaces müssen gefixt werden, nicht alles!
```

#### ✅ Extensibility
```python
# Neue Load-Types einfach hinzufügen
def _generate_internal_loads(self, idf, zones, schedules):
    self._add_people(idf, zones, schedules)
    self._add_lights(idf, zones, schedules)
    self._add_equipment(idf, zones, schedules)
    self._add_gas_equipment(idf, zones, schedules)  # NEU!
```

#### ✅ Reusability
```python
# Schedules von mehreren Generatoren nutzen
schedules = ScheduleGenerator.generate_residential_schedules(idf)
generator1._generate_internal_loads(idf, zones1, schedules)
generator2._generate_internal_loads(idf, zones2, schedules)
```

#### ✅ Clear Responsibilities
- `_generate_metadata`: Building-level settings
- `_generate_zones`: Thermal zone geometry
- `_generate_surfaces`: Wall/Floor/Ceiling geometry
- `_generate_internal_loads`: PEOPLE/LIGHTS/EQUIPMENT
- `_generate_hvac`: HVAC systems

### 4. Migration Strategy

#### Phase 1: Extract Critical Functions (NOW)
```python
# Extract nur die problematischen Teile:
def _generate_internal_loads_from_templates(self, idf, zones)
def _generate_hvac_from_templates(self, idf, zones)
```

#### Phase 2: Extract Geometry Functions (LATER)
```python
def _generate_zones(self, idf)
def _generate_surfaces(self, idf, zones)
```

#### Phase 3: Full Refactoring (OPTIONAL)
- Alle Funktionen extrahieren
- Data classes einführen
- Unit tests schreiben

## Immediate Action

**JETZT**: Testen ob die aktuellen Fixes funktionieren
**DANACH**: Schrittweise Refactoring mit Phase 1 starten

---

**Vorteile zusammengefasst:**
1. 🔍 Bessere Fehlersuche (genau wissen welche Funktion fehlschlägt)
2. ✅ Einfachere Tests (jede Funktion einzeln testbar)
3. 📦 Klarere Code-Organisation (jede Funktion = eine Verantwortung)
4. 🔄 Bessere Wiederverwendbarkeit (Schedules sharable)
5. 🚀 Einfachere Erweiterung (neue Features isoliert hinzufügen)
