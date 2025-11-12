# EnergyPlus IDF Templates

Dieses Verzeichnis enthält vordefinierte, getestete IDF-Fragmente für EnergyPlus-Simulationen.

## Struktur

```
templates/
├── internal_loads/       # PEOPLE, LIGHTS, ELECTRICEQUIPMENT Templates
├── schedules/            # Schedule-Definitionen
└── hvac/                 # HVAC-System Templates
```

## Internal Loads

### Office (Bürogebäude - NWG)
- **people_office_0.05.idf**: 0.05 Personen/m² (typisch für Büros)
- **lights_office_10w.idf**: 10 W/m² Beleuchtungslast
- **equipment_office_5w.idf**: 5 W/m² elektrische Geräte

### Residential (Wohngebäude)
- **people_residential_0.02.idf**: 0.02 Personen/m² (typisch für Wohnungen)
- **lights_residential_5w.idf**: 5 W/m² Beleuchtungslast
- **equipment_residential_3w.idf**: 3 W/m² elektrische Geräte

## Schedules

- **occupancy_office_8_18.idf**: Büro-Nutzung (Mo-Fr 8-18 Uhr)
- **occupancy_residential.idf**: Wohngebäude-Nutzung (abends/Wochenenden)
- **activity_level_120w.idf**: 120 W/Person (sitzende Tätigkeit)
- **always_on.idf**: Konstant 1.0 (für Infiltration, etc.)

## Verwendung

Templates verwenden **ZONE_NAME** als Platzhalter. Beim Laden muss dieser durch den echten Zone-Namen ersetzt werden:

```python
from pathlib import Path

def load_template_with_zone(template_path: Path, zone_name: str) -> str:
    """Lädt Template und ersetzt ZONE_NAME Platzhalter."""
    content = template_path.read_text(encoding='utf-8')
    return content.replace('ZONE_NAME', zone_name)
```

### Beispiel-Integration

```python
# Template laden
template_path = Path("templates/internal_loads/people_office_0.05.idf")
idf_content = load_template_with_zone(template_path, "Perimeter_North_F1")

# In IDF einfügen
with open("temp_fragment.idf", "w") as f:
    f.write(idf_content)

# Via eppy laden und mergen
fragment_idf = IDF("temp_fragment.idf")
for obj in fragment_idf.idfobjects["PEOPLE"]:
    main_idf.copyidfobject(obj)
```

## Wartung

- **Testen**: Jedes Template einzeln mit EnergyPlus validieren
- **IDFEditor**: Templates können mit dem EnergyPlus IDFEditor visuell bearbeitet werden
- **Standards**: Templates basieren auf ASHRAE 90.1, DIN V 18599

## Hintergrund

Diese Templates wurden erstellt um **eppy-Bugs** zu umgehen, die beim programmatischen Erstellen von PEOPLE/LIGHTS/EQUIPMENT-Objekten zu Silent Crashes führten (siehe [Issue #5](https://github.com/LUMA-94-X/AI_BS/issues/5)).

Der template-basierte Ansatz:
- ✅ Umgeht eppy-Bugs komplett
- ✅ Garantiert funktionierende Definitionen
- ✅ Einfach testbar und wartbar
- ✅ Erweiterbar ohne Code-Änderungen
