# 03 - Features Dokumentation

> **Modul:** Geometrie, HVAC und Auswertungs-Features
> **Dateien:** `features/geometrie/`, `features/hvac/`, `features/auswertung/`
> **Zuletzt aktualisiert:** 2025-11-14

---

## Übersicht

Die Features-Module implementieren die **Kernfunktionalität** des Tools:

1. **Geometrie** - Gebäudemodell-Generierung (SimpleBox + 5-Zone)
2. **HVAC** - HVAC-System-Konfiguration
3. **Auswertung** - KPI-Berechnung und Visualisierung

---

## 1. FEATURES/GEOMETRIE

### Zweck
Generierung von EnergyPlus-IDF-Dateien aus Gebäudebeschreibungen.

### Module-Übersicht

```
features/geometrie/
├── generators/
│   ├── box_generator.py        # SimpleBox-IDF-Generator
│   └── five_zone_generator.py  # 5-Zone-IDF-Generator (OIB)
├── models/
│   └── energieausweis_input.py # Pydantic-Modell für OIB RL6
├── utils/
│   ├── geometry_solver.py      # L/W/H-Rekonstruktion aus OIB
│   ├── perimeter_calculator.py # 5-Zonen-Layout
│   ├── surfaces.py             # Surface-Generierung
│   ├── fenster_distribution.py # Fenster-Verteilung
│   └── materials.py            # Konstruktionen (Wrapper)
└── components/
    └── ... # UI-Komponenten
```

---

### 1.1 Energieausweis Input (energieausweis_input.py)

**Pydantic-Modell für OIB RL6 12.2-konforme Eingabe:**

```python
class EnergieausweisInput(BaseModel):
    # === PFLICHT ===
    bruttoflaeche_m2: float = Field(..., gt=0)
    bezugsflaeche_m2: Optional[float] = None

    # U-Werte
    u_wert_wand: float = Field(..., gt=0)
    u_wert_dach: float = Field(..., gt=0)
    u_wert_boden: float = Field(..., gt=0)
    u_wert_fenster: float = Field(..., gt=0)

    # Gebäude
    gebaeudetyp: Literal["EFH", "MFH", "NWG"] = "EFH"
    bauweise: Literal["Massiv", "Leicht"] = "Massiv"
    anzahl_geschosse: int = Field(2, ge=1, le=20)
    geschosshoehe_m: float = Field(3.0, gt=0)

    # === OPTIONAL (OIB RL6 § 12.2) ===
    brutto_volumen_m3: Optional[float] = None
    huellflaeche_gesamt_m2: Optional[float] = None
    wandflaeche_m2: Optional[float] = None
    dachflaeche_m2: Optional[float] = None
    bodenflaeche_m2: Optional[float] = None

    # Klimadaten
    klimaregion: str = "Ost"
    heizgradtage_kd: float = 3400.0
    heiztage: int = 220
    norm_aussentemperatur_c: float = -12.0

    # Fenster
    fenster: FensterData

    # Lüftung
    luftwechselrate_h: float = Field(0.6, ge=0, le=5)

    # === COMPUTED PROPERTIES ===
    @property
    def kompaktheit(self) -> float:
        """A/V-Verhältnis [m⁻¹]"""
        if self.huellflaeche_gesamt_m2 and self.brutto_volumen_m3:
            return self.huellflaeche_gesamt_m2 / self.brutto_volumen_m3
        return 0.0

    @property
    def char_laenge_m(self) -> float:
        """Charakteristische Länge ℓc [m]"""
        if self.kompaktheit > 0:
            return 1.0 / self.kompaktheit
        return 0.0

    @property
    def oib_warnings(self) -> List[str]:
        """OIB-Konsistenzprüfungen"""
        warnings = []

        # A/V-Check
        if self.kompaktheit > 0:
            expected_av = self.huellflaeche_gesamt_m2 / self.brutto_volumen_m3
            if abs(self.kompaktheit - expected_av) > 0.05:
                warnings.append(f"A/V-Inkonsistenz: {self.kompaktheit:.2f} vs {expected_av:.2f}")

        # Flächen-Check
        if self.wandflaeche_m2 and self.dachflaeche_m2 and self.bodenflaeche_m2:
            calc_huellflaeche = self.wandflaeche_m2 + self.dachflaeche_m2 + self.bodenflaeche_m2
            if self.huellflaeche_gesamt_m2:
                diff = abs(calc_huellflaeche - self.huellflaeche_gesamt_m2)
                if diff > 5.0:
                    warnings.append(f"Hüllfläche-Inkonsistenz: {diff:.1f} m² Differenz")

        return warnings
```

---

### 1.2 Geometry Solver (geometry_solver.py)

**Zweck:** Rekonstruktion von L/W/H aus OIB-Kennzahlen.

#### DirectOIBSolver

**3 Modi:**

| Modus | User-Input | Solver-Aufgabe |
|-------|------------|----------------|
| **Automatisch** | Aspect Ratio | L/W/H aus V, AR, n_floors berechnen |
| **Manuell** | L, W, H | Gegen OIB-Daten validieren |
| **Hybrid** | L, AR | W/H aus V, L, n_floors berechnen |

**Algorithmus (Automatisch):**

```python
def solve(
    ea_input: EnergieausweisInput,
    manual_length: Optional[float] = None,
    manual_width: Optional[float] = None,
    manual_height: Optional[float] = None
) -> GeometrySolution:

    # 1. Geschosshöhe
    floor_height = ea_input.geschosshoehe_m
    height = floor_height * ea_input.anzahl_geschosse

    # 2. Grundfläche pro Geschoss
    floor_area = ea_input.bruttoflaeche_m2 / ea_input.anzahl_geschosse

    # 3. L und W aus Aspect Ratio
    aspect_ratio = 1.8  # Default oder aus Input
    # L × W = floor_area
    # L = AR × W
    # → AR × W² = floor_area
    width = math.sqrt(floor_area / aspect_ratio)
    length = aspect_ratio * width

    # 4. Validierung gegen A/V
    envelope_area = 2 * (length + width) * height + 2 * length * width
    volume = length * width * height
    calc_av = envelope_area / volume

    if ea_input.kompaktheit > 0:
        av_diff = abs(calc_av - ea_input.kompaktheit)
        confidence = 1.0 - min(av_diff / ea_input.kompaktheit, 0.5)
    else:
        confidence = 0.75

    return GeometrySolution(
        length=length,
        width=width,
        height=height,
        floor_height=floor_height,
        method=SolverMethod.AUTOMATIC,
        confidence=confidence,
        warnings=[]
    )
```

---

### 1.3 Perimeter Calculator (perimeter_calculator.py)

**Zweck:** 5-Zonen-Layout für alle Geschosse erstellen.

#### Layout

```
        North Perimeter (p)
    +---------------------+
    |W |               | E|
    |e |     Core      | a|
    |s |               | s|
    |t |               | t|
    +---------------------+
        South Perimeter (p)
```

**Adaptive Perimeter-Tiefe:**

```python
def calculate_perimeter_depth(
    length: float,
    width: float,
    window_wall_ratio: float
) -> float:
    """
    Perimeter-Tiefe abhängig von WWR.

    WWR 10-20%: p ≈ 3m
    WWR 40-60%: p ≈ 5-6m

    Constraints:
    - Core ≥ 30% der Fläche
    - p ≤ 30% der kleineren Dimension
    """
    # Basis-Tiefe aus WWR
    base_depth = 3.0 + (window_wall_ratio * 6.0)

    # Constraint 1: Core-Mindestfläche
    min_dim = min(length, width)
    max_depth = min_dim * 0.35  # 30% Rand → 70% Core

    # Constraint 2: Absolute Grenze
    max_depth = min(max_depth, min_dim * 0.3)

    depth = min(base_depth, max_depth)

    return max(depth, 2.5)  # Mindestens 2.5m
```

#### create_multi_floor_layout()

```python
def create_multi_floor_layout(
    length: float,
    width: float,
    height: float,
    num_floors: int,
    window_wall_ratio: float = 0.3
) -> Dict[int, FloorLayout]:
    """
    Erstellt 5-Zonen-Layout für alle Geschosse.

    Returns:
        Dict mit floor_number → FloorLayout
    """
    p = calculate_perimeter_depth(length, width, window_wall_ratio)
    floor_height = height / num_floors

    layouts = {}

    for floor in range(num_floors):
        z_origin = floor * floor_height

        # North Zone (Perimeter)
        north = ZoneGeometry(
            x_origin=0,
            y_origin=width - p,
            z_origin=z_origin,
            length=length,
            width=p,
            height=floor_height
        )

        # South Zone
        south = ZoneGeometry(
            x_origin=0,
            y_origin=0,
            z_origin=z_origin,
            length=length,
            width=p,
            height=floor_height
        )

        # East Zone (ohne Ecken!)
        east = ZoneGeometry(
            x_origin=length - p,
            y_origin=p,
            z_origin=z_origin,
            length=p,
            width=width - 2*p,
            height=floor_height
        )

        # West Zone
        west = ZoneGeometry(
            x_origin=0,
            y_origin=p,
            z_origin=z_origin,
            length=p,
            width=width - 2*p,
            height=floor_height
        )

        # Core Zone
        core = ZoneGeometry(
            x_origin=p,
            y_origin=p,
            z_origin=z_origin,
            length=length - 2*p,
            width=width - 2*p,
            height=floor_height
        )

        layouts[floor] = FloorLayout(
            north=north,
            east=east,
            south=south,
            west=west,
            core=core
        )

    return layouts
```

---

### 1.4 Five Zone Generator (five_zone_generator.py)

**Haupt-Workflow:**

```python
class FiveZoneGenerator:
    def create_from_energieausweis(
        ea_data: EnergieausweisInput,
        output_path: Path
    ) -> Tuple[IDF, Path]:

        # 1. Geometrie rekonstruieren
        solver = DirectOIBSolver()
        geo_solution = solver.solve(ea_data)

        # 2. Multi-Floor Layouts
        layouts = PerimeterCalculator.create_multi_floor_layout(
            length=geo_solution.length,
            width=geo_solution.width,
            height=geo_solution.height,
            num_floors=ea_data.anzahl_geschosse,
            window_wall_ratio=ea_data.fenster.window_wall_ratio_gesamt
        )

        # 3. IDF initialisieren
        idf = IDF()

        # 4. Komponenten hinzufügen
        MetadataGenerator.add_metadata(idf, ea_data)
        MaterialsGenerator.add_materials_from_u_values(idf, ea_data)
        ZoneGenerator.add_zones(idf, layouts)
        SurfaceGenerator.add_all_surfaces(idf, layouts, ea_data)
        ScheduleGenerator.add_schedules(idf)
        InternalLoadsGenerator.add_loads(idf, layouts, ea_data.gebaeudetyp)
        InfiltrationGenerator.add_infiltration(idf, ea_data.luftwechselrate_h)

        # 5. IDF speichern
        idf.save(output_path)

        # 6. eppy Bug-Fix (Boundary Objects)
        EppyBugFixer.fix_boundary_objects(output_path)

        return idf, output_path
```

---

### 1.5 Surface Generator (surfaces.py)

**Kritische EnergyPlus-Konventionen:**

#### Vertex Ordering

```python
# FLOORS: REVERSED order! (Normal zeigt nach unten)
floor_vertices = [
    (x3, y3, z0),  # REVERSED!
    (x2, y2, z0),
    (x1, y1, z0),
    (x0, y0, z0)
]

# CEILINGS/ROOFS: NORMAL order (Normal zeigt nach oben)
ceiling_vertices = [
    (x0, y0, z1),
    (x1, y1, z1),
    (x2, y2, z1),
    (x3, y3, z1)
]

# WALLS: Counter-clockwise (Normal zeigt nach außen)
wall_vertices = [
    (x0, y0, z0),  # Unten links
    (x1, y1, z0),  # Unten rechts
    (x1, y1, z1),  # Oben rechts
    (x0, y0, z1)   # Oben links
]
```

#### Boundary Objects (Inter-Zone Walls)

```python
# Wall A → Wall B
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Core_to_North",
    Surface_Type="Wall",
    Construction_Name="WallConstruction",
    Zone_Name="Core_F1",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="North_to_Core",  # Paar!
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=v0[0],
    Vertex_1_Ycoordinate=v0[1],
    Vertex_1_Zcoordinate=v0[2],
    # ...
)

# Wall B → Wall A (VERTICES REVERSED!)
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="North_to_Core",
    Surface_Type="Wall",
    Construction_Name="WallConstruction",
    Zone_Name="North_F1",
    Outside_Boundary_Condition="Surface",
    Outside_Boundary_Condition_Object="Core_to_North",
    Number_of_Vertices=4,
    Vertex_1_Xcoordinate=v3[0],  # REVERSED!
    Vertex_1_Ycoordinate=v3[1],
    Vertex_1_Zcoordinate=v3[2],
    # ...
)
```

---

## 2. FEATURES/HVAC

### Zweck
Konfiguration von HVAC-Systemen in EnergyPlus-IDF.

### 2.1 Ideal Loads (ideal_loads.py)

**HVACTemplateManager:**

```python
class HVACTemplateManager:
    @staticmethod
    def apply_template_simple(
        idf: IDF,
        heating_setpoint: float = 20.0,
        cooling_setpoint: float = 26.0,
        heating_enabled: bool = True,
        cooling_enabled: bool = True
    ) -> IDF:
        """
        Fügt HVAC-System zu allen Zonen hinzu.

        Verwendet HVACTEMPLATE-Objekte (benötigt ExpandObjects!).
        """

        # 1. Check: Beide deaktiviert?
        if not heating_enabled and not cooling_enabled:
            return idf  # Keine HVAC

        # 2. KRITISCH: Remove existing manual thermostats
        # (verhindert eppy field-order bugs)
        for obj in idf.idfobjects["ZONECONTROL:THERMOSTAT"]:
            idf.removeidfobject(obj)

        # 3. Global objects
        _ensure_convection_algorithms(idf)

        # 4. Schedules
        _add_schedule_type_limits(idf)
        _add_control_schedule(idf)  # AlwaysOn (Value=4)
        _add_setpoint_schedules(idf, heating_setpoint, cooling_setpoint)
        _add_availability_schedules(idf, heating_enabled, cooling_enabled)

        # 5. Shared Thermostat
        idf.newidfobject(
            "HVACTEMPLATE:THERMOSTAT",
            Name="All Zones",  # 1× für alle Zonen!
            Constant_Heating_Setpoint=heating_setpoint,
            Constant_Cooling_Setpoint=cooling_setpoint
        )

        # 6. Ideal Loads pro Zone
        zones = idf.idfobjects["ZONE"]
        for zone in zones:
            idf.newidfobject(
                "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
                Zone_Name=zone.Name,
                Template_Thermostat_Name="All Zones",
                Heating_Availability_Schedule_Name="HeatingAvailability",
                Cooling_Availability_Schedule_Name="CoolingAvailability",
                Heating_Limit_Type="NoLimit",
                Cooling_Limit_Type="NoLimit"
            )

        return idf
```

**Availability Schedules (On/Off-Steuerung):**

```python
def _add_availability_schedules(idf, heating_on, cooling_on):
    """
    Korrekte Methode für Enable/Disable in EnergyPlus.

    1.0 = System ON (verfügbar)
    0.0 = System OFF (deaktiviert)
    """
    idf.newidfobject(
        "SCHEDULE:CONSTANT",
        Name="HeatingAvailability",
        Schedule_Type_Limits_Name="Control Type",
        Hourly_Value=1.0 if heating_on else 0.0
    )

    idf.newidfobject(
        "SCHEDULE:CONSTANT",
        Name="CoolingAvailability",
        Schedule_Type_Limits_Name="Control Type",
        Hourly_Value=1.0 if cooling_on else 0.0
    )
```

---

## 3. FEATURES/AUSWERTUNG

### Zweck
Extraktion, Berechnung und Visualisierung von Kennzahlen.

### 3.1 SQL Parser (sql_parser.py)

**EnergyPlusSQLParser:**

#### get_ergebnis_uebersicht()

```python
def get_ergebnis_uebersicht(self) -> ErgebnisUebersicht:
    """
    Extrahiert Jahreswerte aus eplusout.sql.

    Genutzte Variablen (11):
    - Zone Air System Sensible Heating Energy [J]
    - Zone Air System Sensible Cooling Energy [J]
    - Zone Ideal Loads Zone Total Heating Rate [W]
    - Zone Ideal Loads Zone Total Cooling Rate [W]
    - Zone Mean Air Temperature [°C]
    - Zone Lights Electric Energy [J]
    - Zone Electric Equipment Electric Energy [J]
    - Surface Average Face Conduction Heat Transfer Energy [J]
    - Zone Infiltration Sensible Heat Gain Energy [J]
    - Zone Windows Total Heat Gain Energy [J]
    - Zone Lights/Equipment/People Total Heating Energy [J]
    """

    conn = sqlite3.connect(self.sql_file)

    # SQL Query Pattern:
    query = """
    SELECT SUM(rd.Value)
    FROM ReportData rd
    JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
    WHERE rdd.Name = ?
    """

    # Heizenergie [J → kWh]
    heating_j = self._query_sum("Zone Air System Sensible Heating Energy")
    heating_kwh = heating_j / 3_600_000

    # Kühlung
    cooling_j = self._query_sum("Zone Air System Sensible Cooling Energy")
    cooling_kwh = cooling_j / 3_600_000

    # Spitzenlasten [W → kW]
    heating_peak_w = self._query_max("Zone Ideal Loads Zone Total Heating Rate")
    heating_peak_kw = heating_peak_w / 1000

    # Temperaturen
    temp_avg = self._query_avg("Zone Mean Air Temperature")
    temp_min = self._query_min("Zone Mean Air Temperature")
    temp_max = self._query_max("Zone Mean Air Temperature")

    # OIB-Kennzahlen
    transmission_j = self._query_sum("Surface Average Face Conduction Heat Transfer Energy")
    transmission_kwh = abs(transmission_j) / 3_600_000  # Negative = Verluste

    # ... weitere

    return ErgebnisUebersicht(
        gesamtenergiebedarf_kwh=heating_kwh + cooling_kwh + lights_kwh + equip_kwh,
        heizbedarf_kwh=heating_kwh,
        kuehlbedarf_kwh=cooling_kwh,
        # ...
    )
```

---

### 3.2 KPI Rechner (kpi_rechner.py)

**KennzahlenRechner:**

```python
class KennzahlenRechner:
    def __init__(
        self,
        nettoflaeche_m2: float,
        building_model: Optional[BuildingModel] = None
    ):
        self.nettoflaeche_m2 = nettoflaeche_m2
        self.building_model = building_model

    def berechne_kennzahlen(self, sql_file: Path) -> GebaeudeKennzahlen:
        # 1. Daten extrahieren
        parser = EnergyPlusSQLParser(sql_file)
        ergebnisse = parser.get_ergebnis_uebersicht()

        # 2. Spezifische Kennzahlen [kWh/m²a]
        energiekennzahl = ergebnisse.gesamtenergiebedarf_kwh / self.nettoflaeche_m2
        heizkennzahl = ergebnisse.heizbedarf_kwh / self.nettoflaeche_m2
        kuehlkennzahl = ergebnisse.kuehlbedarf_kwh / self.nettoflaeche_m2

        # 3. Effizienzklasse (EU)
        effizienzklasse = self._bestimme_effizienzklasse(energiekennzahl)

        # 4. OIB-Kennzahlen
        hwb_kwh_m2a = heizkennzahl
        wwwb_kwh_m2a = 0.0  # Nicht simuliert
        eeb_kwh_m2a = heizkennzahl + kuehlkennzahl

        # 5. PEB & CO₂ (wenn HVAC-Typ verfügbar)
        hvac_type = None
        if self.building_model:
            hvac_config = self.building_model.get('hvac_config', {})
            hvac_type = hvac_config.get('heating_system')

        if hvac_type:
            from data.oib_konversionsfaktoren import berechne_peb, berechne_co2
            peb_kwh_m2a = berechne_peb(eeb_kwh_m2a, hvac_type)
            co2_kg_m2a = berechne_co2(eeb_kwh_m2a, self.nettoflaeche_m2, hvac_type)
        else:
            peb_kwh_m2a = None
            co2_kg_m2a = None

        # 6. OIB-Effizienzklasse
        oib_effizienzklasse = self._bestimme_oib_effizienzklasse(
            hwb_kwh_m2a, peb_kwh_m2a, co2_kg_m2a, f_gee
        )

        # 7. Geometrische Kennzahlen aus BuildingModel
        if self.building_model:
            geom = self.building_model.geometry_summary
            kompaktheit_av = geom.get('oib_kompaktheit')
            char_laenge_lc = geom.get('oib_char_laenge')
            mittlerer_u_wert = geom.get('oib_mittlerer_u_wert')
        else:
            kompaktheit_av = None
            char_laenge_lc = None
            mittlerer_u_wert = None

        return GebaeudeKennzahlen(
            energiekennzahl_kwh_m2a=energiekennzahl,
            heizkennzahl_kwh_m2a=heizkennzahl,
            kuehlkennzahl_kwh_m2a=kuehlkennzahl,
            effizienzklasse=effizienzklasse,
            hwb_kwh_m2a=hwb_kwh_m2a,
            eeb_kwh_m2a=eeb_kwh_m2a,
            peb_kwh_m2a=peb_kwh_m2a,
            co2_kg_m2a=co2_kg_m2a,
            oib_effizienzklasse=oib_effizienzklasse,
            kompaktheit_av=kompaktheit_av,
            char_laenge_lc=char_laenge_lc,
            mittlerer_u_wert=mittlerer_u_wert,
            # ... weitere
        )
```

---

### 3.3 Visualisierung (visualisierung.py)

**ErgebnisVisualisierer:**

```python
class ErgebnisVisualisierer:
    def erstelle_dashboard(
        self,
        kennzahlen: GebaeudeKennzahlen,
        sql_file: Path
    ) -> go.Figure:
        """4-Subplot Dashboard"""

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Energiebilanz',
                'Temperaturverlauf',
                'Monatliche Energie',
                'Spitzenlasten'
            )
        )

        # 1. Energiebilanz (Pie)
        fig.add_trace(
            go.Pie(
                labels=['Heizung', 'Kühlung', 'Beleuchtung', 'Geräte'],
                values=[...],
                name='Energiebilanz'
            ),
            row=1, col=1
        )

        # 2. Temperatur (Line)
        parser = EnergyPlusSQLParser(sql_file)
        temp_data = parser.get_timeseries_data("Zone Mean Air Temperature")

        fig.add_trace(
            go.Scatter(
                x=temp_data.index,
                y=temp_data.values,
                name='Temperatur'
            ),
            row=1, col=2
        )

        # 3. Monatlich (Stacked Bar)
        monthly_df = parser.get_monthly_summary()

        fig.add_trace(
            go.Bar(x=monthly_df['Monat'], y=monthly_df['Heizung_kWh'], name='Heizung'),
            row=2, col=1
        )
        # ... weitere Kategorien

        # 4. Lasten (Bar)
        fig.add_trace(
            go.Bar(
                x=['Heizung', 'Kühlung'],
                y=[kennzahlen.heizlast_w_m2, kennzahlen.kuhllast_w_m2],
                name='Lasten'
            ),
            row=2, col=2
        )

        return fig

    def erstelle_interaktive_temperaturkurve(
        self,
        sql_file: Path,
        start_tag: int = 1,
        anzahl_tage: int = 7
    ) -> go.Figure:
        """Interaktive Temperaturanalyse mit Komfortbereich"""

        parser = EnergyPlusSQLParser(sql_file)
        temp_data = parser.get_timeseries_data("Zone Mean Air Temperature")

        # Zeitraum filtern
        start_idx = (start_tag - 1) * 24
        end_idx = start_idx + (anzahl_tage * 24)
        temp_filtered = temp_data.iloc[start_idx:end_idx]

        fig = go.Figure()

        # Temperaturverlauf
        fig.add_trace(go.Scatter(
            x=temp_filtered.index,
            y=temp_filtered.values,
            mode='lines',
            name='Raumtemperatur',
            line=dict(color='blue')
        ))

        # Komfortbereich (20-26°C)
        fig.add_hrect(
            y0=20, y1=26,
            fillcolor="green", opacity=0.1,
            layer="below",
            annotation_text="Komfortbereich",
            annotation_position="top left"
        )

        fig.update_layout(
            title=f"Temperaturverlauf (Tag {start_tag}-{start_tag+anzahl_tage})",
            xaxis_title="Zeit",
            yaxis_title="Temperatur [°C]",
            hovermode='x unified'
        )

        return fig
```

---

### 3.4 Tabular Reports (tabular_reports.py) 🆕

**NEU (2025-11-14)**: Parser für vorgefertigte EnergyPlus Summary Reports

**Zweck:**
- Instant-Zugriff auf aggregierte EnergyPlus-Daten (keine manuelle Zeitreihen-Summierung!)
- Erschließt 95% der bisher ungenutzten EnergyPlus-Daten
- Detaillierte End-Use Breakdown, HVAC Design Loads, Primärenergie-Analyse

**TabularReportParser:**

```python
class TabularReportParser:
    def __init__(self, sql_file: Path):
        self.sql_file = Path(sql_file)

    def _get_tabular_data(self, report_name: str) -> pd.DataFrame:
        """
        SQL Query mit JOINs zur Auflösung von String-Indices:

        SELECT
            tn.Value AS TableName,
            rn.Value AS RowName,
            cn.Value AS ColumnName,
            td.Value AS Value,
            u.Value AS Units
        FROM TabularData td
        LEFT JOIN Strings rs ON td.ReportNameIndex = rs.StringIndex
        LEFT JOIN Strings tn ON td.TableNameIndex = tn.StringIndex
        LEFT JOIN Strings rn ON td.RowNameIndex = rn.StringIndex
        LEFT JOIN Strings cn ON td.ColumnNameIndex = cn.StringIndex
        LEFT JOIN Strings u ON td.UnitsIndex = u.StringIndex
        WHERE rs.Value = ?
        """

    def get_available_reports(self) -> List[str]:
        """Liste aller 25+ verfügbaren Reports"""

    def get_end_use_summary(self) -> EndUseSummary:
        """
        End-Use Breakdown aus 'AnnualBuildingUtilityPerformanceSummary' → 'End Uses'

        Extrahiert:
        - Heating, Cooling [kWh]
        - Interior Lighting, Interior Equipment [kWh]
        - Fans, Pumps [kWh]
        - Total, Electricity, Natural Gas [kWh]
        """

    def get_site_source_energy(self) -> SiteSourceEnergy:
        """
        Site vs. Source Energy (Endenergie vs. Primärenergie)

        Aus 'AnnualBuildingUtilityPerformanceSummary' → 'Site and Source Energy'
        - Site Energy = Endenergie am Gebäude [GJ]
        - Source Energy = Primärenergie (inkl. Verluste) [GJ]
        """

    def get_hvac_sizing(self) -> HVACSizing:
        """
        HVAC Design Loads aus 'HVACSizingSummary'

        Extrahiert:
        - Heating/Cooling Design Load [W] und [W/m²]
        - Design Day Namen für Auslegung
        """

    def get_envelope_performance(self) -> EnvelopePerformance:
        """
        Gebäudehülle aus 'EnvelopeSummary'

        Extrahiert:
        - Wandfläche, Fensterfläche, Dachfläche [m²]
        - Window-Wall-Ratio
        - U-Werte (falls verfügbar)
        """
```

**Datenklassen:**

```python
@dataclass
class EndUseSummary:
    heating_kwh: float = 0.0
    cooling_kwh: float = 0.0
    interior_lighting_kwh: float = 0.0
    interior_equipment_kwh: float = 0.0
    fans_kwh: float = 0.0
    pumps_kwh: float = 0.0
    total_kwh: float = 0.0
    electricity_kwh: float = 0.0
    natural_gas_kwh: float = 0.0

    @property
    def other_kwh(self) -> float:
        """Sonstige Verbräuche"""

@dataclass
class SiteSourceEnergy:
    total_site_energy_gj: float = 0.0
    total_source_energy_gj: float = 0.0
    site_energy_per_m2_mj: float = 0.0
    source_energy_per_m2_mj: float = 0.0

    @property
    def total_site_energy_kwh(self) -> float:
        return self.total_site_energy_gj * 277.778

@dataclass
class HVACSizing:
    heating_design_load_w: float = 0.0
    cooling_design_load_w: float = 0.0
    heating_design_load_per_area_w_m2: float = 0.0
    cooling_design_load_per_area_w_m2: float = 0.0
    heating_design_day: str = ""
    cooling_design_day: str = ""

@dataclass
class EnvelopePerformance:
    gross_wall_area_m2: float = 0.0
    gross_window_area_m2: float = 0.0
    gross_roof_area_m2: float = 0.0
    window_wall_ratio: float = 0.0
    window_u_value: Optional[float] = None
    wall_u_value: Optional[float] = None
    roof_u_value: Optional[float] = None
```

**Integration in bestehende Module:**

1. **sql_parser.py** - Neue Methoden:
   - `get_tabular_summaries()` - Alle Reports auf einmal
   - `get_end_use_breakdown()` - End-Use Breakdown
   - `get_hvac_design_loads()` - HVAC Design Loads

2. **kpi_rechner.py** - Erweiterte Kennzahlen:
   ```python
   @dataclass
   class ErweiterteKennzahlen:
       basis_kennzahlen: GebaeudeKennzahlen
       end_uses: Optional[EndUseSummary]
       site_source_energy: Optional[SiteSourceEnergy]
       hvac_sizing: Optional[HVACSizing]
       envelope: Optional[EnvelopePerformance]

   def berechne_erweiterte_kennzahlen(self, sql_file) -> ErweiterteKennzahlen:
       # Kombiniert Standard-Kennzahlen mit Tabular Reports
   ```

3. **visualisierung.py** - Neue Charts:
   - `erstelle_detailliertes_end_use_chart()` - Pie mit allen Kategorien
   - `erstelle_hvac_design_loads_chart()` - Absolute & spezifische Lasten
   - `erstelle_site_source_energy_chart()` - Site vs. Source Vergleich
   - `erstelle_erweiterte_uebersicht()` - Dashboard mit Tabular Reports

**Vorteile:**
- ✅ Keine 8760-Werte Summierung erforderlich
- ✅ Detaillierte End-Use Breakdown (7+ Kategorien statt 4)
- ✅ Primärenergie-Analyse (Site vs. Source)
- ✅ HVAC Design Loads mit Auslegungstag
- ✅ Gebäudehülle-Performance aus Simulation

**Known Issues (durch Tabular Reports aufgedeckt):**
- 🐛 Design Loads sind 0 (IDF Problem oder fehlende Output:Variables)
- 🐛 Interne Lasten sehr hoch (Lights/Equipment W/m² zu hoch konfiguriert)

---

## Zusammenhänge

### Workflow: Energieausweis → IDF

```
EnergieausweisInput
       ↓
DirectOIBSolver
       ↓
GeometrySolution (L/W/H)
       ↓
PerimeterCalculator
       ↓
FloorLayouts (5 Zonen × n Geschosse)
       ↓
FiveZoneGenerator
  ├─ MetadataGenerator
  ├─ MaterialsGenerator
  ├─ ZoneGenerator
  ├─ SurfaceGenerator
  ├─ ScheduleGenerator
  ├─ InternalLoadsGenerator
  └─ InfiltrationGenerator
       ↓
    IDF-File
       ↓
HVACTemplateManager
       ↓
IDF mit HVAC (benötigt ExpandObjects)
```

### Workflow: Simulation → KPIs

```
eplusout.sql
       ↓
EnergyPlusSQLParser
  ├─ get_ergebnis_uebersicht() → Zeitreihen-Aggregation (11 Variablen)
  └─ get_tabular_summaries() → Vorgefertigte Reports (25+ Reports) 🆕
       ↓
ErgebnisUebersicht + TabularReports (EndUseSummary, SiteSourceEnergy, HVACSizing, Envelope)
       ↓
KennzahlenRechner
  ├─ berechne_kennzahlen() → Standard-KPIs
  └─ berechne_erweiterte_kennzahlen() → ErweiterteKennzahlen 🆕
       ↓
GebaeudeKennzahlen + ErweiterteKennzahlen
       ↓
ErgebnisVisualisierer
  ├─ Dashboard (Standard)
  ├─ Temperaturkurve
  ├─ erstelle_detailliertes_end_use_chart() 🆕
  ├─ erstelle_hvac_design_loads_chart() 🆕
  ├─ erstelle_site_source_energy_chart() 🆕
  └─ erstelle_erweiterte_uebersicht() 🆕
       ↓
  Streamlit UI (Tab 2, Sub-Tab 3: "Tabular Reports") 🆕
```

---

## Kritische Punkte

### Geometrie
1. **Vertex-Ordering:** REVERSED für Floors, NORMAL für Ceilings
2. **Boundary Objects:** Inter-Zone Walls müssen paarweise + reversed sein
3. **Perimeter-Tiefe:** Adaptive Berechnung für realistische Zonen

### HVAC
1. **eppy Bug:** Manuelle Thermostats entfernen vor HVACTemplate
2. **Availability Schedules:** 1.0=ON, 0.0=OFF (nicht Setpoint-Schedules!)
3. **Shared Thermostat:** 1× für alle Zonen (effizienter)

### Auswertung
1. **Einheiten:** SQL in [J], KPIs in [kWh] → Division durch 3.6e6
2. **HVAC-Typ:** Muss für PEB/CO₂-Berechnung verfügbar sein
3. **BuildingModel:** Für OIB-Metadaten (A/V, ℓc, Ū) benötigt
4. **Tabular Reports:** 🆕 Nutzen vorgefertigte EnergyPlus Reports statt Zeitreihen-Aggregation
5. **Design Loads:** 🐛 Aktuell = 0 (IDF Problem oder fehlende Output:Variables)
6. **Interne Lasten:** 🐛 Lights/Equipment W/m² zu hoch konfiguriert

---

**Letzte Änderung:** 2025-11-14
**Changelog:**
- 2025-11-14: Tabular Reports Feature hinzugefügt (Abschnitt 3.4)
- 2025-11-14: Workflow-Diagramm erweitert mit Tabular Reports Pfad
- 2025-11-14: Known Issues dokumentiert (Design Loads, Interne Lasten)
- 2025-11-14: Initial creation - Features vollständig dokumentiert
