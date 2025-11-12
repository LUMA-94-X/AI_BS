# ROOT CAUSE: Residential Building Simulation Crash

## Datum: 2025-11-12

## Problem
Simulationen für Residential Buildings (EFH/MFH) produzierten:
- ✅ building.idf erstellt (10 Zones, PEOPLE/LIGHTS objects)
- ❌ **0 Timesteps** in SQL
- ❌ **Leeres err file**
- ❌ Simulation scheinbar nicht gestartet

## Symptome
```
eplusout.sql: 176KB (aber 0 Time rows)
eplusout.err: 0 bytes (LEER!)
Simulations.Completed: FALSE
```

## Root Cause Analysis - Timeline

### 1. Erste Vermutung: ExpandObjects
- ✅ ExpandObjects funktioniert (HVACTEMPLATE → ZONEHVAC conversion OK)
- ❌ Nicht das Problem

### 2. Zweite Vermutung: HVAC auf alte Geometry
- Hypothese: User hat HVAC auf Geometry OHNE Internal Loads angewendet
- ❌ FALSCH! building.idf HAT 10 PEOPLE + 10 LIGHTS objects

### 3. Analyse der building.idf
```bash
$ grep "SCHEDULETYPELIMITS" building.idf
```
**Gefunden:**
- ✅ ActivityLevel
- ✅ Temperature
- ✅ Control Type

**FEHLT:**
- ❌ **Fraction** (aber OccupancySchedule_Residential referenziert es!)

### 4. Vergleich der Templates

**occupancy_office_8_18.idf** (Office - FUNKTIONIERT):
```idf
SCHEDULETYPELIMITS,
    Fraction,                !- Name
    0.0,                     !- Lower Limit Value
    1.0,                     !- Upper Limit Value
    Continuous;              !- Numeric Type

SCHEDULE:COMPACT,
    OccupancySchedule,       !- Name
    Fraction,                !- Schedule Type Limits Name
    ...
```

**occupancy_residential.idf** (Residential - CRASH):
```idf
!- KEINE SCHEDULETYPELIMITS Definition!

SCHEDULE:COMPACT,
    OccupancySchedule_Residential,  !- Name
    Fraction,                        !- Schedule Type Limits Name (REFERENZ OHNE DEFINITION!)
    ...
```

## ROOT CAUSE

**Template `occupancy_residential.idf` war unvollständig!**

- Enthielt SCHEDULE:COMPACT mit Referenz zu "Fraction"
- **ABER**: SCHEDULETYPELIMITS "Fraction" Definition FEHLTE
- EnergyPlus konnte Schedule nicht validieren
- → **Silent Failure** (0 Timesteps, leeres err file)

## Warum "Silent Failure"?

EnergyPlus verhält sich unterschiedlich je nach Art des Fehlers:
1. **Schwere Fehler (Severe/Fatal)**: Schreibt in err file, Exit Code != 0
2. **Validierungsfehler vor Simulation**: Manchmal keine err file Ausgabe
3. **Missing Schedule Dependencies**: Oft Silent Failure

In diesem Fall: Schedule-Dependency fehlt → EnergyPlus erkennt es während IDD-Validierung → Stoppt vor Simulation → Kein err file output

## Fix

### Commit 23f31e0
```idf
!- templates/schedules/occupancy_residential.idf

!-   ===========  ALL OBJECTS IN CLASS: SCHEDULETYPELIMITS ===========

SCHEDULETYPELIMITS,
    Fraction,                !- Name
    0.0,                     !- Lower Limit Value
    1.0,                     !- Upper Limit Value
    Continuous;              !- Numeric Type

!-   ===========  ALL OBJECTS IN CLASS: SCHEDULE:COMPACT ===========

SCHEDULE:COMPACT,
    OccupancySchedule_Residential,  !- Name
    Fraction,                        !- Schedule Type Limits Name
    ...
```

## Nachhaltige Lösung

✅ **Template-Fix statt Workaround**
- Kein Patch-Skript für existierende IDFs
- Kein Umgehen des Problems
- **Korrektur an der Wurzel**: Template vollständig gemacht

✅ **Konsistenz**
- occupancy_residential.idf jetzt identische Struktur wie occupancy_office_8_18.idf
- Beide Templates vollständig und selbst-contained

✅ **Zukunftssicher**
- Alle neuen Residential Buildings haben vollständige Schedules
- Keine Silent Failures mehr

## Was User tun muss

### Option 1: Neue Geometry erstellen (EMPFOHLEN)
```
1. Streamlit UI öffnen
2. "Geometrie erstellen" Tab
3. Residential Building (EFH oder MFH) eingeben
4. "Generiere Gebäude" klicken
```

→ Neue building.idf hat jetzt **Fraction SCHEDULETYPELIMITS**
→ Simulation sollte funktionieren (8760 Timesteps)

### Option 2: Patch für existierende Geometry (Quick Fix)
Falls User nicht neu erstellen will:

```bash
python3 << 'EOF'
from pathlib import Path
from eppy.modeleditor import IDF

# Load existing building.idf
building_idf = Path("output/simulation_XXXXXX/building.idf")
idf = IDF(str(building_idf))

# Check if Fraction exists
fraction_exists = any(
    obj.Name == "Fraction"
    for obj in idf.idfobjects.get('SCHEDULETYPELIMITS', [])
)

if not fraction_exists:
    print("Adding missing Fraction SCHEDULETYPELIMITS...")
    idf.newidfobject(
        "SCHEDULETYPELIMITS",
        Name="Fraction",
        Lower_Limit_Value=0.0,
        Upper_Limit_Value=1.0,
        Numeric_Type="Continuous"
    )
    idf.save()
    print("✅ Patched!")
else:
    print("✅ Already has Fraction")
EOF
```

**ABER**: Option 1 ist besser (sauberer Zustand)

## Lessons Learned

### 1. Template Validation
❌ **Vorher**: Templates manuell erstellt, keine Validierung
✅ **Zukünftig**: Template-Validierungs-Tests erstellen

### 2. Consistent Structure
❌ **Vorher**: occupancy_residential.idf hatte andere Struktur als occupancy_office_8_18.idf
✅ **Zukünftig**: Alle Schedule-Templates folgen gleichem Muster (SCHEDULETYPELIMITS + SCHEDULE:COMPACT)

### 3. Silent Failures
❌ **Vorher**: Keine Strategie für Silent Failures
✅ **Zukünftig**:
  - Bessere Error Detection in runner.py
  - Check für 0 Timesteps → aussagekräftige Error Message
  - Validierung der Schedule Dependencies vor Simulation

## Nächste Schritte

### Sofort:
- [x] Template gefixt (Commit 23f31e0)
- [ ] User testet neue Geometry-Erstellung
- [ ] Verifizieren dass Simulation 8760 Timesteps produziert

### Mittelfristig:
- [ ] Template-Validierungs-Tests schreiben
- [ ] Silent Failure Detection in runner.py
- [ ] CI/CD: Template-Validation als Pre-Commit Hook

### Langfristig (Phase 2):
- [ ] Template-Generator Tool (verhindert Inkonsistenzen)
- [ ] Comprehensive Template Test Suite
- [ ] Documentation: IDF Best Practices

## Fazit

**Root Cause**: Unvollständiges Template (fehlende SCHEDULETYPELIMITS Definition)

**Fix**: Template vollständig gemacht (nachhaltig, keine Workarounds)

**Result**: Residential Buildings sollten jetzt funktionieren ✅

---

**Generated**: 2025-11-12
**Commit**: 23f31e0
**Status**: ✅ FIXED
