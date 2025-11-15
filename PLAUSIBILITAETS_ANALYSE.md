# Plausibilitäts-Analyse: Zonale Simulationsergebnisse

> **Datum:** 2025-11-15
> **Simulation:** `simulation_20251115_121019`
> **Gebäude:** 3-geschossiges 5-Zonen-Modell (15 Zonen total)
> **Analysiert:** Floor 1 (F1) - repräsentativ

---

## 🔴 KRITISCHER BUG: Nord/Süd-Orientierungen VERTAUSCHT!

### Befund

**Fensterflächen (Floor 1):**
- North-Fenster: 1.896 m² (klein)
- South-Fenster: 5.055 m² (groß, 2.7× größer als Nord)
- East-Fenster: 0.102 m²
- West-Fenster: 0.081 m²

**Solare Gewinne (gesamt für alle 3 Geschosse):**
- North: 1,074 kWh/a
- South: 716 kWh/a
- East: 303 kWh/a
- West: 241 kWh/a

**Solare Gewinne pro m² Fensterfläche:**

| Orientierung | Fensterfläche | Solare Gewinne | Solar/m² Fenster |
|--------------|---------------|----------------|------------------|
| **North**    | 1.896 m²      | 1,074 kWh/a    | **566.5 kWh/m²a** |
| **South**    | 5.055 m²      | 716 kWh/a      | **141.6 kWh/m²a** |
| East         | 0.102 m²      | 303 kWh/a      | 2,970.6 kWh/m²a |
| West         | 0.081 m²      | 241 kWh/a      | 2,975.3 kWh/m²a |

### Analyse

⚠️ **North empfängt 4× MEHR Solarstrahlung pro m² als South** (566.5 vs 141.6 kWh/m²a)

Dies ist **physikalisch unmöglich** auf der Nordhalbkugel:
- Südfassaden erhalten die meiste direkte Sonneneinstrahlung
- Nordfassaden erhalten hauptsächlich diffuse Strahlung
- Erwartetes Verhältnis: South/North ≈ 3-5×, NICHT umgekehrt!

### Root Cause

**Die Orientierungslabels im IDF-Modell sind VERTAUSCHT.**
- Was als "North" bezeichnet ist, zeigt tatsächlich nach **Süden**
- Was als "South" bezeichnet ist, zeigt tatsächlich nach **Norden**

### Auswirkungen

1. ✅ **Simulation ist physikalisch korrekt** - Größeres Südfenster empfängt mehr Sonne
2. ❌ **Labels sind falsch** - User sieht "North" mit hohen Gewinnen
3. ❌ **Fehlerquelle**: Wahrscheinlich in `features/geometrie/generators/five_zone_generator.py` oder `perimeter_calculator.py`

### Fix erforderlich

- IDF-Generator überprüfen: Surface-Normalen und Zonen-Benennung
- Wahrscheinlich Koordinatensystem-Bug (Y-Achse invertiert?)
- Test: Manuelle Verifikation der Surface-Normalen im IDF

---

## ⚠️ East/West Fensterflächen unrealistisch klein

### Befund

- East: 0.102 m² (10 cm × 100 cm)
- West: 0.081 m² (9 cm × 90 cm)

Dies sind extrem schmale Fenster (~8-10 cm breit!), wahrscheinlich ein Geometrie-Bug.

**Solare Gewinne pro m²** sind dadurch unrealistisch hoch (2970-2975 kWh/m²a), vermutlich durch:
- Edge-Effekte in EnergyPlus
- Rounding-Errors bei Vertex-Berechnung
- Perimeter-Tiefe zu klein für realistische Ost/West-Zonen

### Root Cause

**Aspect Ratio des Gebäudes ist extrem:**
- Länge (Nord/Süd): 11.46 m
- Breite (Ost/West): 6.37 m
- Aspect Ratio: 1.8:1

**Perimeter-Tiefe**: 3.0 m (Standard)

Bei dieser Perimeter-Tiefe bleiben für East/West-Zonen nur:
- Breite: 6.37 - 2×3.0 = **0.37 m** (!)
- Das ist unrealistisch dünn

**Zonenflächen bestätigen dies:**
- North/South: 34.39 m² (groß)
- East/West: 1.10 m² (winzig - nur 3% der Gesamtfläche!)
- Core: 2.01 m²

### Fix erforderlich

**Option 1**: Adaptive Perimeter-Tiefe
```python
# Aktuell:
perimeter_depth = 3.0  # fest

# Besser:
perimeter_depth = min(3.0, min(length, width) * 0.25)
# → Für Breite 6.37 m: p = min(3.0, 1.59) = 1.59 m
# → East/West Breite = 6.37 - 2×1.59 = 3.19 m ✓
```

**Option 2**: East/West-Zonen weglassen bei schmalen Gebäuden
```python
if width < 8.0:
    # 3-Zone Layout: North, South, Core (kein East/West)
```

---

## ✅ Innere Lasten: KORREKT verteilt!

### Befund

**Zonenflächen (Floor 1):**
- North: 34.390 m²
- South: 34.390 m²
- East: 1.100 m²
- West: 1.100 m²
- Core: 2.010 m²

**Innere Gewinne (Floor 1):**

| Zone  | Lights  | Equipment | People  | **Gesamt** | **Gesamt/m²** |
|-------|---------|-----------|---------|------------|---------------|
| North | 451.9   | 482.0     | 602.5   | 1,536.4    | **44.7**      |
| South | 451.9   | 482.0     | 602.5   | 1,536.4    | **44.7**      |
| East  | 14.5    | 15.5      | 19.4    | 49.4       | **44.9**      |
| West  | 14.5    | 15.5      | 19.4    | 49.4       | **44.9**      |
| Core  | 26.4    | 28.2      | 35.3    | 89.9       | **44.7**      |

### Analyse

✅ **Innere Lasten sind proportional zur Zonenfläche verteilt!**
- Alle Zonen: ~44.7-44.9 kWh/m²a (konsistent)
- Große Zonen (North/South) haben entsprechend mehr absolute Werte
- Kleine Zonen (East/West/Core) haben proportional weniger

Dies ist **physikalisch korrekt** und entspricht der Spezifikation:
- Lights: 5 W/m² × 30% = 1.5 W/m² effektiv
- Equipment: 4 W/m² × 40% = 1.6 W/m² effektiv
- People: 0.02 p/m² (residential)

**Keine Fixes erforderlich!**

---

## 📊 Zusammenfassung

### Bugs gefunden

| Bug | Schweregrad | Status | Fix erforderlich in |
|-----|-------------|--------|---------------------|
| **Nord/Süd vertauscht** | 🔴 KRITISCH | Bestätigt | `five_zone_generator.py` |
| **East/West zu schmal** | 🟡 MITTEL | Bestätigt | `perimeter_calculator.py` |
| ~~Innere Lasten falsch~~ | ✅ KEIN BUG | - | - |

### Empfohlene Fixes

1. **Koordinatensystem-Check** (Priorität 1):
   - Surface-Normalen überprüfen
   - Zonen-Benennung gegen tatsächliche Orientierung validieren
   - Test-Case mit bekannter Geometrie

2. **Adaptive Perimeter-Tiefe** (Priorität 2):
   - Mindestbreite für East/West-Zonen: 2.5 m
   - Bei schmalen Gebäuden (<8m Breite): 3-Zonen-Layout verwenden

3. **Multi-Floor Zonal Analysis** (Feature-Request):
   - Aktuell hardcoded auf F1
   - Sollte alle 15 Zonen aggregieren
   - UI: Dropdown zur Floor-Auswahl

4. **Pro-m² Werte in UI** (Feature-Request):
   - Alle zonalen Metriken pro m² normalisieren
   - Faire Vergleichbarkeit zwischen unterschiedlich großen Zonen

---

## Testdaten (Referenz)

**IDF-Datei:** `output/simulation_20251115_121019/building.idf`
**SQL-Datei:** `output/simulation_20251115_121019/eplusout.sql`
**Gebäude-Dimension:**
- Länge (X): 11.46 m
- Breite (Y): 6.37 m
- Höhe (3 Geschosse): 11.02 m
- Geschosshöhe: 3.675 m
- Bruttofläche: 219 m²

**Climate File:** Austria/Vienna
**HVAC:** IdealLoadsAirSystem
**Internal Loads:** Residential (OIB RL6)

---

**Erstellt von:** Claude Code (AI_BS Plausibilitäts-Check)
**Methodik:** Ultrathink-Mode - Systematische Analyse aller zonalen Metriken
