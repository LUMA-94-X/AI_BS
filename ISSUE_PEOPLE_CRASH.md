# Issue #5: Internal Loads (PEOPLE/LIGHTS/EQUIPMENT) verursachen EnergyPlus Silent Crash

**GitHub Issue:** https://github.com/LUMA-94-X/AI_BS/issues/5

## ✅ STATUS: FIXED (2025-11-12)

**Solution:** Native eppy approach using `idf.newidfobject()` instead of templates.
**Implementation:** `features/internal_loads/native_loads.py`
**Integration:** `features/geometrie/generators/five_zone_generator.py`
**Test Results:** ✅ 12MB SQL, 0 Severe Errors, 30 Internal Loads (PEOPLE+LIGHTS+EQUIPMENT)

---

## Problem (Original)
Das Hinzufügen von PEOPLE/LIGHTS/ELECTRICEQUIPMENT-Objekten via eppy führt zu einem Silent Crash von EnergyPlus:
- Exit Code: 5
- Error-Datei: 0 Bytes (leer!)
- Execution Time: ~0.4s
- OHNE Internal Loads: ✅ Funktioniert perfekt (8760 Timesteps, 6MB SQL-Datei)
- MIT Internal Loads: ❌ Crash

**Ursache:** eppy generiert defekte Objekt-Definitionen mit unvollständigen oder inkorrekten Feldern.

## Getestete Fixes (alle erfolglos)
1. ✅ SCHEDULETYPELIMITS hinzugefügt ("Fraction", "ActivityLevel")
2. ✅ Alle Schedule_Type_Limits_Name Felder mit gültigen Werten gefüllt
3. ✅ Clothing_Insulation_Calculation_Method auf "DynamicClothingModelASHRAE55" gesetzt
4. ✅ Alle optionalen Felder explizit auf "" gesetzt
5. ✅ Sensible_Heat_Fraction auf 0.7 statt "autocalculate"

## Aktuelles PEOPLE-Objekt
```
PEOPLE,
    Perimeter_North_F1_People,
    Perimeter_North_F1,
    OccupancySchedule,        !- mit Fraction Schedule Type
    People/Area,
    ,
    0.05,
    ,
    0.3,
    0.7,
    ActivityLevel,            !- mit ActivityLevel Schedule Type
    3.82e-08,
    No,
    ,
    ,
    ,
    DynamicClothingModelASHRAE55,  !- Kein Schedule nötig
    ,
    ,
    ,
    ,
    ...;
```

## Workaround
PEOPLE, LIGHTS, ELECTRICEQUIPMENT sind vorerst deaktiviert.
Generator funktioniert perfekt OHNE internal loads.

## Empfohlene Lösung: Standard-Ressourcen-Templates

**Ansatz:** Vordefinierte, getestete IDF-Fragmente als Ressourcen bereitstellen und in Generatoren kopieren statt via eppy neu zu erstellen.

### Vorteile:
1. ✅ Umgeht eppy-Bugs komplett
2. ✅ Garantiert funktionierende EnergyPlus-Definitionen
3. ✅ Einfach testbar (Templates einzeln simulieren)
4. ✅ Wartbar (Templates in IDFEditor visuell editierbar)
5. ✅ Erweiterbar (neue Templates hinzufügen ohne Code-Änderungen)

### Vorgeschlagene Ressourcen-Struktur:
```
resources/
  energyplus/
    templates/
      internal_loads/
        people_office_0.05.idf           # PEOPLE: 0.05 Personen/m² (Büro)
        people_residential_0.02.idf      # PEOPLE: 0.02 Personen/m² (Wohngebäude)
        lights_office_10w.idf            # LIGHTS: 10 W/m² (Büro)
        lights_residential_5w.idf        # LIGHTS: 5 W/m² (Wohngebäude)
        equipment_office_5w.idf          # EQUIPMENT: 5 W/m² (Büro)
        equipment_residential_3w.idf     # EQUIPMENT: 3 W/m² (Wohngebäude)

      schedules/
        occupancy_office_8_18.idf        # Office: Werktags 8-18 Uhr
        occupancy_residential.idf        # Wohngebäude: Abends/Wochenende
        activity_level_120w.idf          # Activity: 120 W/Person (sitzend)

      materials/
        wall_insulated_u0.5.idf          # Gedämmte Außenwand U=0.5
        wall_uninsulated_u2.0.idf        # Ungedämmte Wand U=2.0
        roof_insulated_u0.4.idf          # Gedämmtes Dach U=0.4
        floor_ground_u0.6.idf            # Bodenplatte U=0.6
        window_double_u2.5.idf           # Doppelverglasung U=2.5
        window_triple_u1.1.idf           # Dreifachverglasung U=1.1

      constructions/
        construction_sets_nwg.idf        # Komplett-Set NWG (Office)
        construction_sets_wg.idf         # Komplett-Set WG (Wohngebäude)
```

### Integration in Generatoren:
```python
from pathlib import Path

def _add_internal_loads_from_template(self, idf: IDF, zone_name: str, gebaeudetyp):
    """Fügt Internal Loads aus vordefiniertem Template hinzu."""

    # Template basierend auf Gebäudetyp wählen
    template_map = {
        GebaeudeTyp.NWG: {
            "people": "people_office_0.05.idf",
            "lights": "lights_office_10w.idf",
            "equipment": "equipment_office_5w.idf",
        },
        GebaeudeTyp.WOHNGEBAEUDE: {
            "people": "people_residential_0.02.idf",
            "lights": "lights_residential_5w.idf",
            "equipment": "equipment_residential_3w.idf",
        },
    }

    templates = template_map[gebaeudetyp]
    template_dir = Path("resources/energyplus/templates/internal_loads")

    # Lade Template und kopiere Objekte
    for load_type, template_file in templates.items():
        template_idf = IDF(str(template_dir / template_file))

        # Kopiere PEOPLE/LIGHTS/EQUIPMENT Objekt
        for obj in template_idf.idfobjects[load_type.upper()]:
            new_obj = idf.copyidfobject(obj)
            # Passe Zone-Name an
            new_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
            new_obj.Name = f"{zone_name}_{load_type.capitalize()}"
```

## ✅ FINAL SOLUTION (2025-11-12)

### Native Approach: `NativeInternalLoadsManager`

Created `features/internal_loads/native_loads.py` using direct `idf.newidfobject()` calls:

```python
# NO templates, NO ExpandObjects, NO complexity!
idf.newidfobject(
    "PEOPLE",
    Name=f"{zone_name}_People",
    Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
    Number_of_People_Calculation_Method="People/Area",
    People_per_Floor_Area=0.05,  # office: 1 person per 20m²
    Fraction_Radiant=0.3,
    Activity_Level_Schedule_Name="Activity_Level_Schedule",
)
```

### Key Benefits:
1. ✅ **No ExpandObjects required** (unlike HVACTEMPLATE approach)
2. ✅ **No Energy+.idd issues** (runs directly)
3. ✅ **Same approach as working HVAC** (proven stable)
4. ✅ **Simple schedules** (SCHEDULE:CONSTANT for testing)
5. ✅ **Type-safe** (GebaeudeTyp.EFH/MFH → residential, NWG → office)

### Test Results:
```
✅ Simulation: simulation_20251112_220239
✅ SQL Size: 12 MB
✅ Timesteps: Full year (613,200 data points = ~70 variables * 8760 hours)
✅ Internal Loads: 10 PEOPLE + 10 LIGHTS + 10 ELECTRICEQUIPMENT = 30 objects
✅ Errors: 0 Severe Errors, 15 Warnings (all non-critical)
✅ EnergyPlus: Completed Successfully (13.52 sec)
```

## Status
- [x] Problem identifiziert
- [x] Mehrere Fixes getestet
- [x] Template-based approach tried (failed due to ExpandObjects issues)
- [x] ✅ **FIXED with Native Approach** (NativeInternalLoadsManager)
- [x] Integration in FiveZoneGenerator
- [x] End-to-end testing via UI
- [x] Full year simulation successful

## Dateien
- Generator: `features/geometrie/generators/five_zone_generator.py` (Zeilen 1286-1350)
- Test: `test_with_internal_loads.py`
- Debug: `test_manual_people.py`
