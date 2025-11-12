# Changelog - 2025-11-12: FiveZoneGenerator Debugging Session

## ✅ Erfolgreich behobene Bugs

### 1. GeometrySolver Dimensionen (5-Zone)
**Problem:** Gebäude-Dimensionen falsch (23.01m x 15.34m statt 20m x 15m)
**Ursache:** `A_grundriss = nettoflaeche_m2 / 0.85` "Nutzungsgrad" Faktor
**Fix:** `create_from_explicit_dimensions()` Methode umgeht GeometrySolver
**Datei:** `features/geometrie/generators/five_zone_generator.py:119-217`

### 2. Eppy Boundary Object Bug
**Problem:** `Outside_Boundary_Condition_Object` wurde von eppy.save() korrumpiert
**Symptom:** Inter-zone Wände referenzierten sich selbst statt Nachbar-Wand
**Fix:** Post-save regex replacement mit block-spezifischem Pattern
**Datei:** `features/geometrie/generators/five_zone_generator.py:221-296`

### 3. WallConstruction Bug
**Problem:** Inter-zone Wände nutzten "CeilingConstruction" statt "WallConstruction"
**Fix:** Zeilen 1147, 1176 korrigiert
**Datei:** `features/geometrie/generators/five_zone_generator.py`

### 4. Exterior Wall Vertex Order
**Problem:** Alle 4 Außenwände hatten CLOCKWISE Vertex-Reihenfolge
**Standard:** EnergyPlus erfordert COUNTER-CLOCKWISE (UpperLeftCorner)
**Fix:** Vertices für Nord/Süd/Ost/West Wände neu geordnet
**Datei:** `features/geometrie/generators/five_zone_generator.py:761-825`

### 5. Window Geometry Berechnung
**Problem:** Fenster hatten negative Z-Koordinaten
**Ursache:**
- `wall_height = abs(v2[2] - v1[2])` = 0 (beide am Boden nach Vertex-Fix)
- `wall_width` berechnete Diagonale v1-v3 statt Horizontale v1-v2
**Fix:**
- `wall_height = abs(v4[2] - v1[2])` (bottom to top)
- `wall_width = sqrt((v1[0]-v2[0])² + (v1[1]-v2[1])²)` (horizontal)
- `h_dir` von v1-v2 Vektor
**Datei:** `features/geometrie/generators/five_zone_generator.py:882-921`

### 6. Duplicate Thermostat Error (Simple Box)
**Problem:** "Duplicate ZoneControl:Thermostat" Error bei mehrfachem HVAC-Aufruf
**Fix:** Prüfung ob Thermostat bereits existiert vor Erstellung
**Datei:** `features/hvac/ideal_loads.py:341-358`

### 7. Output-Variablen für IdealLoads HVAC
**Problem:** "Keine Ergebnisse" - falsche Output-Variablen requestet
**Fix:** Korrekte IdealLoads Output-Variablen:
- `Zone Ideal Loads Zone Total Heating Energy`
- `Zone Ideal Loads Zone Total Cooling Energy`
- `Zone Ideal Loads Supply Air Total Heating Energy`
- `Zone Ideal Loads Supply Air Total Cooling Energy`
- Plus: `OUTPUT:TABLE:SUMMARYREPORTS` für AllSummary
**Datei:** `features/geometrie/generators/five_zone_generator.py:1367-1399`

## ⚠️ Bekannte Limitierungen

### Internal Loads (PEOPLE/LIGHTS/EQUIPMENT) deaktiviert
**Problem:** eppy generiert defekte PEOPLE/LIGHTS/EQUIPMENT Objekte → Silent Crash
**Workaround:** Internal Loads vorerst deaktiviert
**Empfehlung:** Standard-Ressourcen Templates erstellen (siehe `ISSUE_PEOPLE_CRASH.md`)
**Status:** Generator funktioniert fehlerfrei OHNE Internal Loads

## 📊 Test-Ergebnisse

### FiveZoneGenerator (test_quick_5zone.py)
```
✅ SUCCESS
Execution Time: 3.14s
Timesteps: 8,760 (vollständiges Jahr)
SQL-Datei: 6.0 MB
CSV-Tabellen: quick5tbl.csv
Konfiguration:
- 5 Zonen (4 Perimeter + 1 Core)
- 30 BuildingSurfaces (16 inter-zone walls)
- 4 Windows (WWR=0.3)
- IdealLoads HVAC
- Dimensionen: 20m x 15m x 3m
- Keine Severe Errors
```

### Simple Box Generator
```
✅ SUCCESS (nach Duplicate Thermostat Fix)
- Multi-floor unterstützt
- Ideal Loads HVAC
- U-Wert basierte Konstruktionen
```

## 📁 Dateien

### Geändert
- `features/geometrie/generators/five_zone_generator.py` (7 Fixes)
- `features/hvac/ideal_loads.py` (Duplicate Thermostat Fix)

### Neu
- `ISSUE_PEOPLE_CRASH.md` - Dokumentation Internal Loads Problem
- `test_quick_5zone.py` - Validierungs-Test für 5-Zone Generator

### Gelöscht (Cleanup)
- 17+ alte Test-Dateien entfernt
- Debug-Verzeichnisse aufgeräumt

## 🚀 Nächste Schritte

1. **Standard-Ressourcen Templates erstellen:**
   - `resources/energyplus/templates/internal_loads/`
   - `resources/energyplus/templates/materials/`
   - `resources/energyplus/templates/constructions/`
   - Siehe `ISSUE_PEOPLE_CRASH.md` für Details

2. **Template-Integration:**
   - Generator nutzt vordefinierte IDF-Fragmente
   - Umgeht eppy-Bugs komplett

3. **Validierung:**
   - Templates einzeln simulieren
   - Integration testen

## 📝 Commit Message

```
Fix: FiveZoneGenerator - 7 kritische Bugs behoben

- Fix GeometrySolver Dimensionen (create_from_explicit_dimensions)
- Fix eppy Boundary Object Bug (post-save regex fix)
- Fix WallConstruction für inter-zone walls
- Fix Exterior Wall Vertex Order (counter-clockwise)
- Fix Window Geometry (wall_height, wall_width, h_dir)
- Fix Duplicate Thermostat Error (HVAC)
- Fix Output-Variablen für IdealLoads HVAC

Generator läuft fehlerfrei: 8760 Timesteps, 6MB SQL-Datei
Internal Loads vorerst deaktiviert (siehe ISSUE_PEOPLE_CRASH.md)

Tests:
- test_quick_5zone.py: ✅ SUCCESS (3.14s, 8760 timesteps)
- Simple Box: ✅ SUCCESS (nach Thermostat-Fix)
```
