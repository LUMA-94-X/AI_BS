# ⚡ EnergyPlus Resources

EnergyPlus-spezifische Templates, Wetterdaten und Datenbanken.

## 📁 Struktur

```
energyplus/
├── templates/           # IDF-Templates für HVAC, Loads, Schedules
│   ├── hvac/
│   ├── internal_loads/
│   ├── schedules/
│   └── materials/       # (geplant)
│
└── weather/             # EPW-Wetterdateien nach Land
    ├── germany/
    ├── austria/
    └── switzerland/
```

---

## 📂 templates/

**Zweck:** Wiederverwendbare IDF-Snippets für verschiedene Komponenten

IDF-Templates werden von `HVACTemplateManager` und anderen Generatoren verwendet, um vordefinierte Objekte in Gebäudemodelle einzufügen.

**Siehe:** `templates/README.md` für Details zu verfügbaren Templates

---

## 🌦️ weather/

**Zweck:** EPW-Wetterdateien organisiert nach Land

EPW (EnergyPlus Weather Format) Dateien enthalten stündliche Wetterdaten für ein komplettes Jahr.

### Verfügbare Länder:

#### 📍 Austria (`weather/austria/`)
- `example.epw` - Salzburg IWEC Data

#### 📍 Germany (`weather/germany/`)
*(Noch keine Dateien - für zukünftige Erweiterung)*

#### 📍 Switzerland (`weather/switzerland/`)
*(Noch keine Dateien - für zukünftige Erweiterung)*

### EPW-Dateien hinzufügen:

1. **Download:** https://energyplus.net/weather
2. **Speichern:** `resources/energyplus/weather/{land}/{dateiname}.epw`
3. **Verwendung:** Wird automatisch vom Tool erkannt

### Naming Convention:

```
{LAND}_{STADT}_{DATASET}.epw

Beispiele:
- AUT_Vienna_IWEC.epw
- DEU_Berlin_IWEC.epw
- DEU_Munich_TMY.epw
- CHE_Zurich_IWEC.epw
```

---

## 🔧 Verwendung im Code

### Templates:

```python
from pathlib import Path

template_path = Path("resources/energyplus/templates/hvac/ideal_loads.idf")
```

### Wetterdateien:

```python
from pathlib import Path

weather_path = Path("resources/energyplus/weather/austria/example.epw")

# Oder: Rekursive Suche
weather_dir = Path("resources/energyplus/weather")
all_epw_files = list(weather_dir.glob("**/*.epw"))
```

---

## 📊 Erweiterungen (Geplant)

### `materials/` (Phase 4+)
Material-Datenbanken für automatische Konstruktions-Generierung:
- Dämmstoff-Properties (λ-Werte)
- Standard-Konstruktionen (DIN, ASHRAE)
- Fenster-Typen (U-Wert, SHGC)

### `standards/` (Future)
Gebäudestandard-Definitionen:
- TABULA Deutschland
- ASHRAE 90.1
- EN 15459

---

## 🔄 Migration Notes

**Previous Structure:**
```
templates/          → resources/energyplus/templates/
data/weather/       → resources/energyplus/weather/
```

**Breaking Changes:**
- Alle Pfad-Referenzen im Code aktualisiert
- Web UI verwendet jetzt rekursive Suche für EPW-Dateien
- Config: `weather.data_dir = "resources/energyplus/weather"`

---

**Erstellt:** 2025-11-13
**Letztes Update:** 2025-11-13
**Maintainer:** AI_BS Project
