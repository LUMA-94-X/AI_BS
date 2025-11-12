# EnergyPlus IDF Best Practices

## 📋 Inhaltsverzeichnis
1. [Geometrie-Regeln](#geometrie-regeln)
2. [Vertex-Reihenfolge](#vertex-reihenfolge)
3. [Inter-Zone Surfaces](#inter-zone-surfaces)
4. [HVAC-Systeme](#hvac-systeme)
5. [Systematisches Testen](#systematisches-testen)
6. [Häufige Fehler](#häufige-fehler)

---

## 🏗️ Geometrie-Regeln

### GlobalGeometryRules
**KRITISCH**: Muss **direkt nach VERSION** stehen (vor allen Geometrie-Objekten)!

```
VERSION, 25.1;

GLOBALGEOMETRYRULES,
    UpperLeftCorner,          !- Starting Vertex Position
    Counterclockwise,         !- Vertex Entry Direction
    Relative,                 !- Coordinate System
    Relative,                 !- Daylighting Reference Point Coordinate System
    Relative;                 !- Rectangular Surface Coordinate System
```

### Koordinatensystem
- **Counterclockwise** (gegen Uhrzeiger) von **außen** betrachtet
- Vertices müssen korrekte Richtung für Surface Normal ergeben
- Falsche Vertex-Reihenfolge → Negative Zonen-Volumina!

---

## 🔄 Vertex-Reihenfolge

### ✅ KORREKT: Floor-Surfaces
**Floor-Normal muss nach UNTEN zeigen!**

```python
# Floor vertices: REVERSED [3,2,1,0]
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_Floor",
    Surface_Type="Floor",
    Number_of_Vertices=4,
    # REVERSED order!
    Vertex_1_Xcoordinate=x0, Vertex_1_Ycoordinate=y1, Vertex_1_Zcoordinate=z,
    Vertex_2_Xcoordinate=x1, Vertex_2_Ycoordinate=y1, Vertex_2_Zcoordinate=z,
    Vertex_3_Xcoordinate=x1, Vertex_3_Ycoordinate=y0, Vertex_3_Zcoordinate=z,
    Vertex_4_Xcoordinate=x0, Vertex_4_Ycoordinate=y0, Vertex_4_Zcoordinate=z,
)
```

**Warum reversed?**
- Counterclockwise von UNTEN betrachtet
- Normal zeigt nach unten (wie physikalisch korrekt)

### ✅ KORREKT: Ceiling/Roof-Surfaces
**Ceiling-Normal muss nach OBEN zeigen!**

```python
# Ceiling vertices: NORMAL [0,1,2,3]
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_Ceiling",
    Surface_Type="Ceiling",  # or "Roof"
    Number_of_Vertices=4,
    # NORMAL order!
    Vertex_1_Xcoordinate=x0, Vertex_1_Ycoordinate=y0, Vertex_1_Zcoordinate=z,
    Vertex_2_Xcoordinate=x1, Vertex_2_Ycoordinate=y0, Vertex_2_Zcoordinate=z,
    Vertex_3_Xcoordinate=x1, Vertex_3_Ycoordinate=y1, Vertex_3_Zcoordinate=z,
    Vertex_4_Xcoordinate=x0, Vertex_4_Ycoordinate=y1, Vertex_4_Zcoordinate=z,
)
```

**Warum normal?**
- Counterclockwise von OBEN betrachtet
- Normal zeigt nach oben (wie physikalisch korrekt)

### ✅ KORREKT: Wall-Surfaces
**Wall-Normal muss nach AUSSEN zeigen!**

```python
# Wall (counterclockwise from outside)
# Beispiel: North Wall (Y = max)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_Wall_North",
    Surface_Type="Wall",
    Number_of_Vertices=4,
    # Start bottom-left, counterclockwise from outside
    Vertex_1_Xcoordinate=x0, Vertex_1_Ycoordinate=y1, Vertex_1_Zcoordinate=z0,  # Bottom-left
    Vertex_2_Xcoordinate=x1, Vertex_2_Ycoordinate=y1, Vertex_2_Zcoordinate=z0,  # Bottom-right
    Vertex_3_Xcoordinate=x1, Vertex_3_Ycoordinate=y1, Vertex_3_Zcoordinate=z1,  # Top-right
    Vertex_4_Xcoordinate=x0, Vertex_4_Ycoordinate=y1, Vertex_4_Zcoordinate=z1,  # Top-left
)
```

---

## 🔗 Inter-Zone Surfaces

### Floor/Ceiling Matching (KRITISCH!)
**Inter-Zone Floor/Ceiling Paare müssen EXAKTE Umkehrungen sein!**

#### Beispiel: 2-Stockwerk Gebäude

```python
# FLOOR 1 - Ceiling (connects to Floor 2)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_F1_Ceiling",
    Surface_Type="Ceiling",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Zone_F2_Floor",  # ← Points to Floor above
    Number_of_Vertices=4,
    # Ceiling: [0,1,2,3]
    Vertex_1_Xcoordinate=0,  Vertex_1_Ycoordinate=0,  Vertex_1_Zcoordinate=3,
    Vertex_2_Xcoordinate=10, Vertex_2_Ycoordinate=0,  Vertex_2_Zcoordinate=3,
    Vertex_3_Xcoordinate=10, Vertex_3_Ycoordinate=10, Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0,  Vertex_4_Ycoordinate=10, Vertex_4_Zcoordinate=3,
)

# FLOOR 2 - Floor (connects to Floor 1 Ceiling)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_F2_Floor",
    Surface_Type="Floor",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Zone_F1_Ceiling",  # ← Points to Ceiling below
    Number_of_Vertices=4,
    # Floor: [3,2,1,0] = REVERSED!
    Vertex_1_Xcoordinate=0,  Vertex_1_Ycoordinate=10, Vertex_1_Zcoordinate=3,
    Vertex_2_Xcoordinate=10, Vertex_2_Ycoordinate=10, Vertex_2_Zcoordinate=3,
    Vertex_3_Xcoordinate=10, Vertex_3_Ycoordinate=0,  Vertex_3_Zcoordinate=3,
    Vertex_4_Xcoordinate=0,  Vertex_4_Ycoordinate=0,  Vertex_4_Zcoordinate=3,
)
```

**Validierung**:
- Ceiling: `(0,0,3) → (10,0,3) → (10,10,3) → (0,10,3)`
- Floor:   `(0,10,3) → (10,10,3) → (10,0,3) → (0,0,3)` ✅ REVERSED!

### Inter-Zone Walls (Horizontal)
**Matching Walls müssen ebenfalls reversed sein!**

```python
# Zone West - East Wall (to Zone East)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_West_Wall_ToEast",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Zone_East_Wall_ToWest",
    # Vertices: (X=5, Y from 10→0, Z from 0→3)
    Vertex_1=5,10,0  →  Vertex_2=5,0,0  →  Vertex_3=5,0,3  →  Vertex_4=5,10,3
)

# Zone East - West Wall (to Zone West) - REVERSED!
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Zone_East_Wall_ToWest",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Zone_West_Wall_ToEast",
    # Vertices: (X=5, Y from 0→10, Z from 0→3) - REVERSED!
    Vertex_1=5,0,0  →  Vertex_2=5,10,0  →  Vertex_3=5,10,3  →  Vertex_4=5,0,3
)
```

---

## 🌡️ HVAC-Systeme

### Minimum Requirements
Jede Zone **MUSS** ein HVAC-System haben:
1. **ZONEHVAC:IDEALLOADSAIRSYSTEM** (einfachste Option)
2. **ZONECONTROL:THERMOSTAT** mit Setpoints
3. **ZONEHVAC:EQUIPMENTCONNECTIONS** mit Nodes

### Beispiel: IdealLoads HVAC

```python
# 1. Thermostat
idf.newidfobject(
    "ZONECONTROL:THERMOSTAT",
    Name="Zone_Thermostat",
    Zone_or_ZoneList_Name="Zone",
    Control_Type_Schedule_Name="AlwaysOn",  # Schedule with value=4
    Control_1_Object_Type="ThermostatSetpoint:DualSetpoint",
    Control_1_Name="DualSetPoint",
)

# 2. Setpoints
idf.newidfobject(
    "THERMOSTATSETPOINT:DUALSETPOINT",
    Name="DualSetPoint",
    Heating_Setpoint_Temperature_Schedule_Name="HeatingSetpoint",  # 20°C
    Cooling_Setpoint_Temperature_Schedule_Name="CoolingSetpoint",  # 26°C
)

# 3. IdealLoads System
idf.newidfobject(
    "ZONEHVAC:IDEALLOADSAIRSYSTEM",
    Name="Zone_IdealLoads",
    Zone_Supply_Air_Node_Name="Zone_Supply_Node",
    Heating_Limit="NoLimit",
    Cooling_Limit="NoLimit",
)

# 4. Equipment List
idf.newidfobject(
    "ZONEHVAC:EQUIPMENTLIST",
    Name="Zone_Equipment_List",
    Load_Distribution_Scheme="SequentialLoad",
    Zone_Equipment_1_Object_Type="ZoneHVAC:IdealLoadsAirSystem",
    Zone_Equipment_1_Name="Zone_IdealLoads",
    Zone_Equipment_1_Cooling_Sequence=1,
    Zone_Equipment_1_Heating_or_NoLoad_Sequence=1,
)

# 5. Equipment Connections
idf.newidfobject(
    "ZONEHVAC:EQUIPMENTCONNECTIONS",
    Zone_Name="Zone",
    Zone_Conditioning_Equipment_List_Name="Zone_Equipment_List",
    Zone_Air_Inlet_Node_or_NodeList_Name="Zone_Supply_Node",
    Zone_Air_Node_Name="Zone_Air_Node",
    Zone_Return_Air_Node_or_NodeList_Name="Zone_Return_Node",
)
```

---

## 🧪 Systematisches Testen

### Inkrementelle Komplexität
**Empfohlener Ablauf** (wie in diesem Projekt validiert):

#### Step 1: Baseline (1-Zone Box)
- Einfachste Geometrie: 1 Zone, 6 Surfaces
- Ground Floor, Outdoor Roof, 4 Outdoor Walls
- IdealLoads HVAC
- **Ziel**: Simulation läuft durch

#### Step 2: Fenster
- Basis von Step 1
- **1 FENSTER** hinzufügen (FENESTRATIONSURFACE:DETAILED)
- **Ziel**: Window-Geometrie funktioniert

#### Step 3: Inter-Zone Walls (Horizontal)
- **2 Zones** horizontal nebeneinander
- Inter-Zone Wall zwischen Zones
- **Ziel**: Horizontale Inter-Zone Verbindungen funktionieren

#### Step 4: Floor/Ceiling (Vertical) ⚠️ KRITISCH!
- **2 Zones** vertikal übereinander
- Inter-Zone Floor/Ceiling Paar
- **Ziel**: Vertikale Inter-Zone Verbindungen funktionieren
- **Dies ist der kritischste Test!**

#### Step 5: Multi-Zone Single Floor
- **5 Zones** (Perimeter N/E/S/W + Core) auf 1 Etage
- Mehrere Inter-Zone Walls
- **Ziel**: Komplexe horizontale Layouts funktionieren

#### Step 6: Multi-Floor Building
- **10 Zones** (5 zones x 2 floors)
- Mehrere Floor/Ceiling Paare
- **Ziel**: Vollständiges Multi-Floor Modell funktioniert

### Validierungskriterien
Für jeden Test prüfen:
- ✅ **Simulation erfolgt**: Return Code = 0
- ✅ **Timesteps vorhanden**: Time rows = 8,760 (jährlich)
- ✅ **SQL-Datei plausibel**: > 0.5 MB für Jahressimulation
- ✅ **Keine Severe Errors** im .err file
- ✅ **Positive Zone Volumes** (negative = falsche Vertex Order!)

---

## ⚠️ Häufige Fehler

### 1. Negative Zone Volumes
**Symptom**:
```
** Warning ** Indicated Zone Volume <= 0.0 for Zone=ZONE_NAME
**   ~~~   ** The calculated Zone Volume was=-100.00
```

**Ursache**: Falsche Vertex-Reihenfolge bei Floor oder Ceiling

**Lösung**:
- Floors: Vertices [3,2,1,0] (reversed)
- Ceilings: Vertices [0,1,2,3] (normal)

### 2. Inter-Zone Surface Mismatch
**Symptom**:
```
** Severe ** GetSurfaceData: Non-coincident interzone surfaces
```

**Ursache**: Inter-Zone Surface-Paare sind nicht exakte Umkehrungen

**Lösung**: Vertices müssen gespiegelt sein:
- Surface A: `V1, V2, V3, V4`
- Surface B: `V4, V3, V2, V1` (exact reverse)

### 3. Fehlende HVAC-Systeme
**Symptom**: Simulation startet, aber keine Zeitschritte (EnvironmentPeriods = 0)

**Ursache**: Zonen haben kein HVAC-System

**Lösung**: IdealLoads HVAC zu allen Zonen hinzufügen

### 4. GlobalGeometryRules zu spät
**Symptom**:
```
** Warning ** GlobalGeometryRules should be first after VERSION
```

**Ursache**: GLOBALGEOMETRYRULES steht nicht direkt nach VERSION

**Lösung**: Immer als 2. Objekt nach VERSION platzieren

### 5. Fehlende OUTPUT-Objekte
**Symptom**: Simulation läuft, aber keine SQL-Datei

**Ursache**: OUTPUT:SQLITE fehlt

**Lösung**:
```python
idf.newidfobject("OUTPUTCONTROL:TABLE:STYLE", Column_Separator="HTML")
idf.newidfobject("OUTPUT:SQLITE", Option_Type="SimpleAndTabular")
idf.newidfobject("OUTPUT:VARIABLE", Key_Value="*",
                 Variable_Name="Zone Mean Air Temperature",
                 Reporting_Frequency="Hourly")
```

---

## 📚 Referenzen

### Test Scripts (in diesem Projekt)
- `test_step4_vertical.py` - Floor/Ceiling Validierung
- `test_step6_simple.py` - Multi-Floor Validierung
- Alle Scripts unter `/test_step*.py`

### Fix Location
- `features/geometrie/generators/five_zone_generator.py`
  - Lines 469-480: Floor vertices (REVERSED)
  - Lines 529-540: Ceiling vertices (NORMAL)

### EnergyPlus Dokumentation
- [Input Output Reference](https://energyplus.net/documentation)
- [Application Guide for EMS](https://energyplus.net/assets/nrel_custom/pdfs/pdfs_v23.2.0/EMSApplicationGuide.pdf)

---

## ✅ Checkliste für neue IDF-Modelle

- [ ] VERSION als erstes Objekt
- [ ] GLOBALGEOMETRYRULES als zweites Objekt
- [ ] Floor vertices: `[3,2,1,0]` (reversed)
- [ ] Ceiling vertices: `[0,1,2,3]` (normal)
- [ ] Inter-Zone Floor/Ceiling: Exact reverse pairs
- [ ] Inter-Zone Walls: Exact reverse pairs
- [ ] HVAC zu allen Zonen hinzugefügt
- [ ] OUTPUT:SQLITE definiert
- [ ] Mindestens 1 OUTPUT:VARIABLE
- [ ] RUNPERIOD definiert
- [ ] Test mit Step-by-Step Ansatz

---

**Erstellt**: 2025-11-12
**Validiert mit**: EnergyPlus V25.1.0
**Status**: ✅ Alle 6 Test-Steps PASSED
