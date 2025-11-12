# Issue #5: Internal Loads (PEOPLE/LIGHTS/EQUIPMENT) verursachen EnergyPlus Silent Crash

**GitHub Issue:** https://github.com/LUMA-94-X/AI_BS/issues/5

## Problem
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

## Status
- [x] Problem identifiziert
- [x] Mehrere Fixes getestet (alle erfolglos)
- [x] Workaround implementiert (Internal Loads deaktiviert)
- [x] Generator funktioniert fehlerfrei ohne Internal Loads (8760 Timesteps, 6MB SQL)
- [ ] Standard-Ressourcen erstellen (internal_loads, schedules, materials, constructions)
- [ ] Templates in Generator integrieren
- [ ] Validierung: Templates einzeln simulieren
- [ ] PEOPLE/LIGHTS/EQUIPMENT re-aktivieren und testen

## Dateien
- Generator: `features/geometrie/generators/five_zone_generator.py` (Zeilen 1286-1350)
- Test: `test_with_internal_loads.py`
- Debug: `test_manual_people.py`
