# 02 - Core Module Dokumentation

> **Modul:** Core Backend-Komponenten
> **Dateien:** `core/*.py`
> **Zuletzt aktualisiert:** 2025-11-14

---

## Übersicht

Die Core-Module bilden das **Fundament** der Anwendung. Sie sind framework-agnostisch und können auch ohne Streamlit verwendet werden.

**Hauptmodule:**
1. `building_model.py` - Einheitliches Gebäudemodell (Pydantic)
2. `climate_data.py` - Klimadaten-Datenbank & EPW-Parser
3. `config.py` - Konfigurationsmanagement
4. `simulation_config.py` - YAML-basierte Szenario-Konfiguration
5. `materialien.py` - Baumaterialien & Konstruktionen

---

## 1. building_model.py

### Zweck
**Einheitliches Datenmodell** für alle Gebäudetypen (SimpleBox + Energieausweis).

### Hauptklasse: BuildingModel

**Pydantic BaseModel:**

```python
class BuildingModel(BaseModel):
    source: Literal["simplebox", "energieausweis", "oib_energieausweis"]
    geometry_summary: Dict[str, Any]
    idf_path: Optional[Path] = None
    num_zones: int
    has_hvac: bool = False
    gebaeudetyp: Optional[str] = None  # EFH/MFH/NWG
    energieausweis_data: Optional[Dict] = None
```

### Factory Methods

#### from_simplebox()

**Zweck:** BuildingModel aus SimpleBox-Parametern erstellen

**Input:**

```python
@classmethod
def from_simplebox(
    cls,
    length: float,           # [m]
    width: float,            # [m]
    height: float,           # [m]
    num_floors: int,
    floor_height: float,     # [m]
    window_wall_ratio: float,
    idf_path: Optional[Path] = None
) -> "BuildingModel"
```

**Berechnete geometry_summary-Felder:**

```python
geometry_summary = {
    'length': length,
    'width': width,
    'height': height,
    'num_floors': num_floors,
    'floor_height': floor_height,
    'window_wall_ratio': window_wall_ratio,

    # Berechnete Werte:
    'floor_area': length * width,
    'total_floor_area': length * width * num_floors,
    'volume': length * width * height,
    'envelope_area': 2 * (length + width) * height + 2 * length * width,
    'av_ratio': envelope_area / volume
}
```

**Verwendung:**

```python
from core.building_model import BuildingModel

model = BuildingModel.from_simplebox(
    length=20.0, width=12.0, height=6.0,
    num_floors=2, floor_height=3.0, window_wall_ratio=0.3
)
```

---

#### from_energieausweis()

**Zweck:** BuildingModel aus OIB-Energieausweis-Daten erstellen

**Input:**

```python
@classmethod
def from_energieausweis(
    cls,
    geo_solution: GeometrySolution,     # Berechnete Geometrie
    ea_data: EnergieausweisInput,       # Vollständige EA-Daten
    idf_path: Path,
    num_zones: int = 5                  # 5 pro Geschoss
) -> "BuildingModel"
```

**Berechnete geometry_summary-Felder:**

```python
geometry_summary = {
    # Basis-Geometrie
    'length': geo_solution.length,
    'width': geo_solution.width,
    'height': geo_solution.height,
    'floor_height': geo_solution.floor_height,
    'num_floors': ea_data.anzahl_geschosse,

    # Flächen
    'total_floor_area': ea_data.bruttoflaeche_m2,
    'nettoflaeche_m2': ea_data.bezugsflaeche_m2,

    # OIB RL6 Kennzahlen
    'oib_brutto_grundflaeche': ea_data.bruttoflaeche_m2,
    'oib_bezugsflaeche': ea_data.bezugsflaeche_m2,
    'oib_brutto_volumen': ea_data.brutto_volumen_m3,
    'oib_huellflaeche_gesamt': ea_data.huellflaeche_gesamt_m2,
    'oib_kompaktheit': ea_data.kompaktheit,          # A/V [m⁻¹]
    'oib_char_laenge': ea_data.char_laenge_m,        # ℓc [m]
    'oib_mittlerer_u_wert': ea_data.mittlerer_u_wert,

    # Klimadaten
    'oib_klimaregion': ea_data.klimaregion,
    'oib_heizgradtage': ea_data.heizgradtage_kd,
    'oib_heiztage': ea_data.heiztage,
    'oib_norm_aussentemp': ea_data.norm_aussentemperatur_c,

    # U-Werte
    'u_wand': ea_data.u_wert_wand,
    'u_dach': ea_data.u_wert_dach,
    'u_boden': ea_data.u_wert_boden,
    'u_fenster': ea_data.u_wert_fenster
}

# Vollständige EA-Daten für YAML-Export speichern
energieausweis_data = ea_data.model_dump()
energieausweis_data["_geometry_solver_meta"] = {
    "method": geo_solution.method.value,
    "confidence": geo_solution.confidence,
    "calculated_length": geo_solution.length,
    "calculated_width": geo_solution.width,
    "calculated_height": geo_solution.height
}
```

**Verwendung:**

```python
from core.building_model import BuildingModel
from features.geometrie.utils.geometry_solver import DirectOIBSolver

solver = DirectOIBSolver()
solution = solver.solve(ea_input=ea_data)

model = BuildingModel.from_energieausweis(
    geo_solution=solution,
    ea_data=ea_data,
    idf_path=Path("output/building.idf"),
    num_zones=5 * ea_data.anzahl_geschosse
)
```

---

### Helper Methods

#### get_display_name()

```python
def get_display_name(self) -> str:
    if self.source == "simplebox":
        return "SimpleBox Model"
    elif self.source == "oib_energieausweis":
        return f"OIB Energieausweis ({self.gebaeudetyp})"
    else:
        return f"Energieausweis ({self.gebaeudetyp})"
```

#### get_summary_text()

```python
def get_summary_text(self) -> str:
    """Mehrzeilige Zusammenfassung für UI"""
    summary = [
        f"Typ: {self.get_display_name()}",
        f"Zonen: {self.num_zones}",
        f"Fläche: {self.geometry_summary.get('total_floor_area', 0):.1f} m²",
        f"HVAC: {'Ja' if self.has_hvac else 'Nein'}"
    ]
    return "\n".join(summary)
```

---

### Session State Helper Functions

**Diese Funktionen kapseln die Streamlit-Session-State-Logik:**

#### get_building_model_from_session()

```python
def get_building_model_from_session(session_state) -> Optional[BuildingModel]:
    """Lädt BuildingModel aus Streamlit Session State"""
    if 'building_model' in session_state:
        try:
            # Session State speichert als Dict
            data = session_state['building_model']
            return BuildingModel(**data)
        except Exception as e:
            logging.warning(f"Failed to load BuildingModel: {e}")
            return None
    return None
```

#### save_building_model_to_session()

```python
def save_building_model_to_session(session_state, model: BuildingModel):
    """Speichert BuildingModel in Streamlit Session State"""
    # Als Dict speichern (JSON-serializable)
    session_state['building_model'] = model.model_dump()

    # Legacy-Kompatibilität
    session_state['geometry_valid'] = True
    session_state['geometry_method'] = model.source
```

#### clear_building_model_from_session()

```python
def clear_building_model_from_session(session_state):
    """Löscht BuildingModel und verwandte Keys"""
    keys_to_remove = [
        'building_model',
        'geometry_valid',
        'geometry_method',
        'geometry_source',
        'idf',
        'idf_path'
    ]
    for key in keys_to_remove:
        if key in session_state:
            del session_state[key]
```

**Verwendung in Streamlit:**

```python
import streamlit as st
from core.building_model import get_building_model_from_session

# Laden
building_model = get_building_model_from_session(st.session_state)
if not building_model:
    st.error("Kein Gebäudemodell vorhanden!")
    st.stop()

# Modifikation
building_model.has_hvac = True

# Speichern
from core.building_model import save_building_model_to_session
save_building_model_to_session(st.session_state, building_model)
```

---

## 2. climate_data.py

### Zweck
**Klimadaten-Management** für österreichische Standorte und EPW-Dateien.

### Hauptklasse: ClimateData

**Pydantic BaseModel:**

```python
class ClimateData(BaseModel):
    klimaregion: str                    # Ost/West/Süd/Nord
    heizgradtage_kd: float              # Heizgradtage bei 20°C Heizgrenze
    heiztage: int                       # Anzahl Heiztage (Tmittel < 12°C)
    norm_aussentemperatur_c: float      # Auslegungstemperatur für Heizlast

    # Optional
    kuehlgradtage_kd: Optional[float] = None
    jahresmitteltemperatur_c: Optional[float] = None
    hoehe_m: Optional[int] = None
```

### Datenbank: AUSTRIA_CLIMATE_DATABASE

**8 österreichische Städte:**

```python
AUSTRIA_CLIMATE_DATABASE = {
    "Wien": {
        "plz_ranges": [(1000, 1999)],
        "data": ClimateData(
            klimaregion="Ost",
            heizgradtage_kd=3400.0,
            heiztage=220,
            norm_aussentemperatur_c=-12.0,
            kuehlgradtage_kd=85.0,
            jahresmitteltemperatur_c=10.4,
            hoehe_m=156
        )
    },
    "Eisenstadt": {
        "plz_ranges": [(7000, 7999)],
        "data": ClimateData(...)
    },
    # ... weitere Städte
}
```

---

### Funktionen: Datenbank-Lookup

#### get_climate_data_by_plz()

```python
def get_climate_data_by_plz(plz: int) -> Optional[ClimateData]:
    """
    Sucht Klimadaten nach Postleitzahl.

    Args:
        plz: Österreichische Postleitzahl (1000-9999)

    Returns:
        ClimateData wenn gefunden, sonst None
    """
    for city_name, city_info in AUSTRIA_CLIMATE_DATABASE.items():
        for plz_start, plz_end in city_info["plz_ranges"]:
            if plz_start <= plz <= plz_end:
                return city_info["data"]
    return None
```

**Verwendung:**

```python
from core.climate_data import get_climate_data_by_plz

climate = get_climate_data_by_plz(1010)  # Wien
if climate:
    print(f"Heizgradtage: {climate.heizgradtage_kd} Kd")
    print(f"Klimaregion: {climate.klimaregion}")
```

#### get_climate_data_by_city()

```python
def get_climate_data_by_city(city_name: str) -> Optional[ClimateData]:
    """Sucht Klimadaten nach Städtename"""
    city_info = AUSTRIA_CLIMATE_DATABASE.get(city_name)
    return city_info["data"] if city_info else None
```

#### get_available_cities()

```python
def get_available_cities() -> List[str]:
    """Liste aller verfügbaren Städte"""
    return list(AUSTRIA_CLIMATE_DATABASE.keys())
```

---

### Funktionen: EPW-Analyse

**Benötigt `ladybug-core` Library (optional dependency):**

```bash
pip install ladybug-core
```

#### calculate_heating_degree_days_from_epw()

```python
def calculate_heating_degree_days_from_epw(
    epw_path: Path,
    base_temp_c: float = 20.0
) -> float:
    """
    Berechnet Heizgradtage aus EPW-Datei.

    Formel: Σ max(0, T_base - T_outdoor) / 24

    Args:
        epw_path: Pfad zur EPW-Datei
        base_temp_c: Heizgrenztemperatur (default 20°C)

    Returns:
        Heizgradtage [Kd]
    """
    from ladybug.epw import EPW

    epw = EPW(str(epw_path))
    temps = epw.dry_bulb_temperature

    hdd = 0.0
    for temp in temps:
        if temp < base_temp_c:
            hdd += (base_temp_c - temp) / 24  # Stundenwerte → Tageswerte

    return hdd
```

#### calculate_heating_days_from_epw()

```python
def calculate_heating_days_from_epw(
    epw_path: Path,
    threshold_temp_c: float = 12.0
) -> int:
    """
    Berechnet Anzahl Heiztage (Tagesmitteltemp < 12°C).

    Args:
        epw_path: Pfad zur EPW-Datei
        threshold_temp_c: Schwellentemperatur (default 12°C)

    Returns:
        Anzahl Heiztage
    """
    from ladybug.epw import EPW

    epw = EPW(str(epw_path))
    temps = epw.dry_bulb_temperature

    # Tägliche Mittelwerte berechnen
    daily_temps = [
        sum(temps[i:i+24]) / 24
        for i in range(0, len(temps), 24)
    ]

    # Heiztage zählen
    heating_days = sum(1 for temp in daily_temps if temp < threshold_temp_c)

    return heating_days
```

#### get_design_outdoor_temperature_from_epw()

```python
def get_design_outdoor_temperature_from_epw(
    epw_path: Path,
    percentile: float = 0.04
) -> float:
    """
    Bestimmt Norm-Außentemperatur (4%-Perzentil).

    Das 4%-Perzentil bedeutet: 96% aller Temperaturen sind wärmer.

    Args:
        epw_path: Pfad zur EPW-Datei
        percentile: Perzentil (default 0.04 = 4%)

    Returns:
        Norm-Außentemperatur [°C]
    """
    from ladybug.epw import EPW
    import numpy as np

    epw = EPW(str(epw_path))
    temps = epw.dry_bulb_temperature

    design_temp = np.percentile(temps, percentile * 100)

    return round(design_temp, 1)
```

#### get_climate_data_from_epw()

```python
def get_climate_data_from_epw(
    epw_path: Path,
    klimaregion: Optional[str] = None
) -> ClimateData:
    """
    Erstellt ClimateData aus EPW-Datei (kombiniert alle obigen Funktionen).

    Args:
        epw_path: Pfad zur EPW-Datei
        klimaregion: Optional (sonst "EPW")

    Returns:
        ClimateData mit berechneten Werten
    """
    hdd = calculate_heating_degree_days_from_epw(epw_path)
    heating_days = calculate_heating_days_from_epw(epw_path)
    design_temp = get_design_outdoor_temperature_from_epw(epw_path)

    # Klimaregion aus EPW-Datei-Name extrahieren (falls nicht angegeben)
    if not klimaregion:
        klimaregion = epw_path.stem  # Dateiname ohne Extension

    return ClimateData(
        klimaregion=klimaregion,
        heizgradtage_kd=hdd,
        heiztage=heating_days,
        norm_aussentemperatur_c=design_temp
    )
```

**Verwendung:**

```python
from core.climate_data import get_climate_data_from_epw
from pathlib import Path

epw_path = Path("resources/energyplus/weather/AUT_Vienna.epw")
climate = get_climate_data_from_epw(epw_path, klimaregion="Ost")

print(f"Heizgradtage: {climate.heizgradtage_kd:.0f} Kd")
print(f"Heiztage: {climate.heiztage}")
print(f"Norm-Außentemp: {climate.norm_aussentemperatur_c} °C")
```

---

## 3. config.py

### Zweck
**Zentrale Konfiguration** für Tool-Einstellungen (nicht für Szenarios - siehe `simulation_config.py`).

### Klassen-Hierarchie

```
Config (Haupt-Config)
├── EnergyPlusConfig
├── SimulationConfig
├── WeatherConfig
├── StandardsConfig
├── GeometryConfig
├── MaterialsConfig
├── HVACConfig
├── PostProcessingConfig
└── LoggingConfig
```

---

### EnergyPlusConfig

**Verwaltet EnergyPlus-Installation:**

```python
class EnergyPlusConfig(BaseModel):
    installation_path: str
    version: str = "23.2"
    executable: str

    def get_executable_path(self) -> Path:
        """
        Auto-Detection mit OS-spezifischen Pfaden.
        Konvertiert WSL → Windows Pfade wenn nötig.
        """
        # Auto-detect wenn nicht gesetzt
        if not self.installation_path:
            self.installation_path = self._auto_detect_installation()

        exe_path = Path(self.installation_path) / self.executable

        # WSL: Konvertiere /mnt/c/... → C:/...
        if platform.system() == "Linux" and str(exe_path).startswith("/mnt/"):
            import subprocess
            result = subprocess.run(
                ["wslpath", "-w", str(exe_path)],
                capture_output=True, text=True
            )
            return Path(result.stdout.strip())

        return exe_path

    def _auto_detect_installation(self) -> str:
        """OS-spezifische Standard-Pfade"""
        system = platform.system()

        if system == "Windows":
            return "C:/EnergyPlusV23-2-0"
        elif system == "Linux":
            # WSL erkennen
            if "microsoft" in platform.release().lower():
                return "/mnt/c/EnergyPlusV23-2-0"
            else:
                return "/usr/local/EnergyPlus-23-2-0"
        elif system == "Darwin":  # macOS
            return "/Applications/EnergyPlus-23-2-0"
        else:
            raise ValueError(f"Unsupported OS: {system}")
```

**Verwendung:**

```python
from core.config import get_config

config = get_config()
energyplus_exe = config.energyplus.get_executable_path()
# → Path("C:/EnergyPlusV23-2-0/energyplus.exe")
```

---

### SimulationConfig

**Standard-Simulations-Einstellungen:**

```python
class SimulationConfig(BaseModel):
    output_dir: str = "output"
    num_processes: int = Field(4, ge=1, le=32)
    keep_intermediate_files: bool = False
    timeout: int = 3600  # Sekunden
```

---

### WeatherConfig

```python
class WeatherConfig(BaseModel):
    data_dir: str = "resources/energyplus/weather"
    default_file: str = "AUT_Vienna.epw"
```

---

### GeometryConfig

**Default-Werte für Geometrie-Parameter:**

```python
class GeometryConfig(BaseModel):
    defaults: Dict[str, Any] = {
        "floor_height": 3.0,        # [m]
        "window_wall_ratio": 0.3,   # [-]
        "orientation": 0.0,          # [°]
        "num_floors": 2
    }
    min_zone_volume: float = 10.0   # [m³]
```

---

### Config (Hauptklasse)

**Kombiniert alle Sub-Configs:**

```python
class Config(BaseModel):
    energyplus: EnergyPlusConfig
    simulation: SimulationConfig
    weather: WeatherConfig
    standards: StandardsConfig
    geometry: GeometryConfig
    materials: MaterialsConfig
    hvac: HVACConfig
    post_processing: PostProcessingConfig
    logging: LoggingConfig

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Config":
        """Lädt Config aus YAML-Datei"""
        import yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, yaml_path: Path):
        """Speichert Config als YAML"""
        import yaml
        with open(yaml_path, 'w') as f:
            yaml.dump(self.model_dump(), f)

    @classmethod
    def load_default(cls) -> "Config":
        """Lädt default_config.yaml"""
        default_path = Path(__file__).parent.parent / "default_config.yaml"
        if default_path.exists():
            return cls.from_yaml(default_path)
        else:
            # Fallback: Hardcoded defaults
            return cls(
                energyplus=EnergyPlusConfig(...),
                simulation=SimulationConfig(),
                # ... weitere mit Defaults
            )
```

---

### Global Functions (Singleton Pattern)

```python
_global_config: Optional[Config] = None

def get_config() -> Config:
    """
    Holt globale Config (Singleton).
    Lädt default_config.yaml beim ersten Aufruf.
    """
    global _global_config
    if _global_config is None:
        _global_config = Config.load_default()
    return _global_config

def set_config(config: Config):
    """Setzt globale Config"""
    global _global_config
    _global_config = config

def load_config(config_path: Path):
    """Lädt und setzt Config aus Datei"""
    config = Config.from_yaml(config_path)
    set_config(config)
```

**Verwendung:**

```python
from core.config import get_config, load_config

# Default verwenden
config = get_config()

# Oder eigene Config laden
load_config(Path("my_config.yaml"))
config = get_config()
```

---

## 4. simulation_config.py

### Zweck
**YAML-basierte Szenario-Konfiguration** für reproduzierbare Simulationen.

**Unterschied zu `config.py`:**
- `config.py` = Tool-Einstellungen (wo ist EnergyPlus, etc.)
- `simulation_config.py` = Szenario-Beschreibung (welches Gebäude simulieren)

### Klassen-Hierarchie

```
SimulationConfig (Haupt-Szenario)
├── BuildingParams
│   ├── GeometryParams (SimpleBox)
│   ├── EnergieausweisParams (OIB RL6)
│   ├── EnvelopeParams
│   ├── ZoneParams
│   └── default_zone
├── HVACSystemConfig
│   └── IdealLoadsParams
└── SimulationParams
    ├── SimulationPeriod
    └── OutputParams
```

---

### GeometryParams (SimpleBox)

```python
class GeometryParams(BaseModel):
    length: float = Field(..., gt=0, description="Gebäudelänge [m]")
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    num_floors: int = Field(..., ge=1, le=50)
    floor_height: Optional[float] = None  # Auto aus height/num_floors
    window_wall_ratio: float = Field(0.3, ge=0.0, le=0.9)
    orientation: float = Field(0.0, ge=0.0, lt=360.0)
```

---

### EnergieausweisParams (OIB RL6)

**Vollständige EA-Eingabe:**

```python
class EnergieausweisParams(BaseModel):
    # Pflichtfelder
    bruttoflaeche_m2: float = Field(..., gt=0)
    u_wert_wand: float = Field(..., gt=0)
    u_wert_dach: float = Field(..., gt=0)
    u_wert_boden: float = Field(..., gt=0)
    u_wert_fenster: float = Field(..., gt=0)

    # Optional: Hüllflächen
    wandflaeche_m2: Optional[float] = None
    dachflaeche_m2: Optional[float] = None
    bodenflaeche_m2: Optional[float] = None

    # Geometrie-Hints
    anzahl_geschosse: int = Field(2, ge=1)
    geschosshoehe_m: float = Field(3.0, gt=0)
    aspect_ratio_hint: float = Field(1.5, gt=0)

    # Fenster
    fenster: FensterParams

    # Klima
    klimaregion: str = "Ost"
    heizgradtage_kd: float = 3400.0
    # ...

    # Auto-populated nach Geometrie-Reconstruction
    geometry_solver_method: Optional[str] = None
    geometry_solver_confidence: Optional[float] = None
```

---

### BuildingParams

**Unterstützt BEIDE Workflows:**

```python
class BuildingParams(BaseModel):
    name: str
    building_type: str  # residential/office/retail
    source: Literal["simplebox", "energieausweis"]

    # Zwei Alternativen (genau eine muss gesetzt sein):
    geometry: Optional[GeometryParams] = None          # Für SimpleBox
    energieausweis: Optional[EnergieausweisParams] = None  # Für OIB

    # Gemeinsame Params:
    envelope: Optional[EnvelopeParams] = None
    zones: Optional[List[ZoneParams]] = None
    default_zone: Optional[ZoneParams] = None

    # Auto-populated:
    calculated_geometry: Optional[Dict] = None

    @model_validator(mode='after')
    def validate_geometry_source(self):
        """Genau eine von geometry ODER energieausweis muss gesetzt sein"""
        if self.geometry and self.energieausweis:
            raise ValueError("Nur geometry ODER energieausweis erlaubt")
        if not self.geometry and not self.energieausweis:
            raise ValueError("geometry oder energieausweis erforderlich")
        return self
```

---

### SimulationConfig (Haupt-Klasse)

```python
class SimulationConfig(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = "1.0"

    building: BuildingParams
    hvac: HVACSystemConfig
    simulation: SimulationParams

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "SimulationConfig":
        """Lädt Szenario aus YAML"""
        import yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, yaml_path: Path):
        """Speichert Szenario als YAML"""
        import yaml
        with open(yaml_path, 'w') as f:
            yaml.dump(
                self.model_dump(exclude_none=True),
                f,
                default_flow_style=False,
                sort_keys=False
            )

    def validate_paths(self, base_dir: Path):
        """Prüft ob Weather-File etc. existieren"""
        weather_path = base_dir / self.simulation.weather_file
        if not weather_path.exists():
            raise FileNotFoundError(f"Weather file not found: {weather_path}")
```

**Verwendung:**

```python
from core.simulation_config import SimulationConfig

# Laden
config = SimulationConfig.from_yaml("scenario.yaml")

# Zugriff
print(config.building.name)
print(config.hvac.system_type)
print(config.simulation.weather_file)

# Speichern
config.to_yaml("modified_scenario.yaml")
```

**YAML-Beispiel:**

```yaml
name: "EFH_Wien_2024"
description: "Einfamilienhaus in Wien"
version: "1.0"

building:
  name: "Musterhaus"
  building_type: "residential"
  source: "energieausweis"

  energieausweis:
    bruttoflaeche_m2: 219.0
    u_wert_wand: 0.35
    u_wert_dach: 0.25
    u_wert_boden: 0.45
    u_wert_fenster: 1.5
    anzahl_geschosse: 3
    geschosshoehe_m: 2.7
    klimaregion: "Ost"
    heizgradtage_kd: 3400.0

    fenster:
      window_wall_ratio_gesamt: 0.25

hvac:
  system_type: "ideal_loads"
  ideal_loads:
    heating_setpoint: 20.0
    cooling_setpoint: 26.0

simulation:
  weather_file: "resources/energyplus/weather/AUT_Vienna.epw"
  timestep: 4
  period:
    start_month: 1
    start_day: 1
    end_month: 12
    end_day: 31
  output:
    output_dir: "output"
    reporting_frequency: "Hourly"
```

---

## 5. materialien.py

### Zweck
**Basis-Baumaterialien und -Konstruktionen** für EnergyPlus-IDF.

### Funktionen

#### add_basic_materials()

```python
def add_basic_materials(idf: IDF):
    """
    Fügt 5 Standard-Materialien hinzu.

    Materials:
    - Concrete: λ=1.95 W/mK, d=0.20m, ρ=2400 kg/m³
    - Insulation: λ=0.04 W/mK, d=0.10m, ρ=30 kg/m³
    - GypsumBoard: λ=0.16 W/mK, d=0.0127m, ρ=800 kg/m³
    - Brick: λ=0.89 W/mK, d=0.10m, ρ=1920 kg/m³
    - Plywood: λ=0.12 W/mK, d=0.019m, ρ=540 kg/m³
    """
    idf.newidfobject("MATERIAL")
    # Name, Roughness, Thickness, Conductivity, Density, Specific_Heat, ...
```

#### add_basic_glazing()

```python
def add_basic_glazing(idf: IDF):
    """
    Fügt SimpleDoubleGlazing hinzu.

    Properties:
    - U-Wert: 2.7 W/m²K
    - SHGC: 0.7
    - VT: 0.8
    """
    idf.newidfobject("WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM")
```

#### add_basic_constructions()

```python
def add_basic_constructions(idf: IDF):
    """
    Erstellt 5 Standard-Konstruktionen.

    Constructions:
    1. WallConstruction: Brick + Insulation + Concrete + GypsumBoard
    2. RoofConstruction: Plywood + Insulation + Concrete + GypsumBoard
    3. FloorConstruction: Concrete + Insulation + Concrete
    4. CeilingConstruction: GypsumBoard + Insulation + GypsumBoard
    5. WindowConstruction: SimpleDoubleGlazing

    Ruft automatisch add_basic_materials() und add_basic_glazing() auf.
    """
    add_basic_materials(idf)
    add_basic_glazing(idf)

    # WallConstruction
    idf.newidfobject(
        "CONSTRUCTION",
        Name="WallConstruction",
        Outside_Layer="Brick",
        Layer_2="Insulation",
        Layer_3="Concrete",
        Layer_4="GypsumBoard"
    )
    # ... weitere Konstruktionen
```

#### get_construction_u_value()

```python
def get_construction_u_value(construction_name: str) -> float:
    """
    Gibt approximierte U-Werte zurück.

    Args:
        construction_name: Name der Konstruktion

    Returns:
        U-Wert [W/m²K]

    Raises:
        ValueError wenn unbekannte Konstruktion
    """
    U_VALUES = {
        "WallConstruction": 0.35,
        "RoofConstruction": 0.25,
        "FloorConstruction": 0.40,
        "WindowConstruction": 2.7
    }
    if construction_name not in U_VALUES:
        raise ValueError(f"Unknown construction: {construction_name}")
    return U_VALUES[construction_name]
```

**Verwendung:**

```python
from eppy.modeleditor import IDF
from core.materialien import add_basic_constructions

# IDF initialisieren
idf = IDF()

# Materialien & Konstruktionen hinzufügen
add_basic_constructions(idf)

# Surface erstellen
idf.newidfobject(
    "BUILDINGSURFACE:DETAILED",
    Name="Wall_North",
    Surface_Type="Wall",
    Construction_Name="WallConstruction",
    # ...
)
```

---

## Zusammenhänge der Core-Module

### Datenfluss

```
SimulationConfig.yaml
       ↓
SimulationConfig.from_yaml()
       ↓
  ┌────┴────┐
  │         │
Geometry  HVAC
  │         │
  └────┬────┘
       ↓
BuildingModel
       ↓
  IDF-Generator
       ↓
add_basic_constructions()
       ↓
    IDF-File
       ↓
EnergyPlusRunner
 (nutzt Config.energyplus)
       ↓
  eplusout.sql
```

### Dependency-Graph

```
config.py (global settings)
    ↓
building_model.py (central model)
    ↓
├── climate_data.py (optional für EA)
├── simulation_config.py (scenarios)
└── materialien.py (IDF content)
```

---

## Best Practices

### 1. Config vs SimulationConfig

**Verwende `config.py` für:**
- Tool-Einstellungen
- EnergyPlus-Pfade
- Logging-Level

**Verwende `simulation_config.py` für:**
- Gebäude-Szenarios
- Reproduzierbare Simulationen
- YAML-Export/Import

### 2. BuildingModel als Unified Interface

**Immer BuildingModel verwenden:**
- Egal ob SimpleBox oder Energieausweis
- Session State über `get_building_model_from_session()`
- Nicht direkt mit Session State arbeiten

### 3. Klimadaten

**3 Optionen:**
1. **PLZ-Lookup** (schnell): `get_climate_data_by_plz(1010)`
2. **Manuelle Eingabe** (flexibel): `ClimateData(...)`
3. **EPW-Analyse** (präzise): `get_climate_data_from_epw(epw_path)`

### 4. Materialien

**Aktuell:** Standard-Konstruktionen mit fixen U-Werten

**Zukünftig (geplant):**
- U-Wert → Dämmstoffdicke Berechnung
- Layer-by-Layer Generierung
- Validierung gegen Ziel-U-Wert

---

**Letzte Änderung:** 2025-11-14
**Changelog:** Initial creation - Vollständige Core Module Analyse
