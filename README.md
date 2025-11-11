# 🏗️ EnergyPlus Gebäude-Simulator

Automatisierte Erstellung und Simulation von Gebäuden mit EnergyPlus.

---

## 🚀 Schnellstart

### Simulation starten

**Einfachste Methode** (Doppelklick):
1. Öffne Projekt-Ordner `AI_BS`
2. Doppelklick auf `START_SIMULATION.bat`
3. Fertig! ✅

**ODER im Terminal**:
```bash
.\venv\Scripts\Activate.ps1
python examples\03_building_with_hvac_template.py
```

**ODER mit Web-UI** (empfohlen!):
```bash
.\venv\Scripts\Activate.ps1
streamlit run ui/app.py
```
Öffnet automatisch Browser mit grafischer Oberfläche!

---

## ✨ Features

- ✅ **Web-Oberfläche**: Einfache Bedienung im Browser
- ✅ **Automatische Geometrie**: Gebäude per Parameter erstellen
- ✅ **HVAC-Systeme**: Heizung/Kühlung automatisch konfiguriert
- ✅ **Multi-Floor**: Mehrgeschossige Gebäude möglich
- ✅ **Batch-Simulationen**: Mehrere Varianten parallel
- ✅ **Visualisierung**: Automatische Ergebnis-Diagramme

---

## 📋 Was ist möglich?

### Gebäude-Parameter

- **Größe**: Länge, Breite, Höhe frei wählbar
- **Geschosse**: 1-10 Stockwerke
- **Fenster**: 10-90% Fensteranteil
- **Orientierung**: 0-360° Ausrichtung

### HVAC-Systeme

- **Ideal Loads**: Unbegrenzte Heiz-/Kühlkapazität (für Studien)
- Weitere Systeme geplant (VAV, Fan Coil, etc.)

### Simulationsergebnisse

- Heiz- und Kühlenergie
- Raumtemperaturen
- Solare Gewinne
- HTML-Reports mit Grafiken

---

## 📚 Dokumentation

| Datei | Beschreibung |
|-------|--------------|
| **[ANLEITUNG.md](ANLEITUNG.md)** | Ausführliche Anleitung |
| **[CHANGELOG.md](CHANGELOG.md)** | Änderungshistorie |

---

## 🎯 Beispiele

### Beispiel 1: Einfaches Gebäude

```python
from src.geometry.simple_box import SimpleBoxGenerator, BuildingGeometry
from src.hvac.template_manager import HVACTemplateManager
from src.utils.config import get_config

# Gebäude definieren
geometry = BuildingGeometry(
    length=15.0,      # 15m lang
    width=12.0,       # 12m breit
    height=9.0,       # 9m hoch
    num_floors=3,     # 3 Geschosse
    window_wall_ratio=0.35  # 35% Fenster
)

# IDF erstellen
generator = SimpleBoxGenerator(get_config())
idf = generator.create_model(geometry)

# HVAC hinzufügen
hvac = HVACTemplateManager()
idf = hvac.apply_template_simple(idf, "ideal_loads")

# Speichern
idf.saveas("mein_gebaeude.idf", encoding='utf-8')
```

### Beispiel 2: Parameterstudie

```python
# Verschiedene Fenstervarianten testen
for wwr in [0.2, 0.3, 0.4, 0.5]:
    geometry = BuildingGeometry(
        length=15.0, width=12.0, height=9.0,
        num_floors=3,
        window_wall_ratio=wwr
    )
    # ... simulieren und Ergebnisse vergleichen
```

---

## 📁 Projekt-Struktur

```
AI_BS/
├── ui/                      # 🌐 Web-Oberfläche
│   └── app.py              # Streamlit App
├── src/                     # Haupt-Code
│   ├── geometry/           # Geometrie-Generierung
│   ├── hvac/               # HVAC-Templates
│   ├── simulation/         # Simulation Runner
│   └── utils/              # Hilfsfunktionen
├── examples/                # Code-Beispiele
├── output/                  # Simulationsergebnisse
├── data/weather/           # Wetterdateien (.epw)
├── START_SIMULATION.bat    # 🚀 Quick-Start
├── ANLEITUNG.md            # Ausführliche Anleitung
└── README.md               # Diese Datei
```

---

## 🛠️ Voraussetzungen

- **Python 3.11+**
- **EnergyPlus 23.2.0**
- **Wetterdatei** (.epw) in `data/weather/`

---

## ⚙️ Installation

Bereits installiert! Virtual Environment existiert bereits.

Falls neu aufsetzen nötig:
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🎨 Web-UI verwenden

**Start**:
```bash
.\venv\Scripts\Activate.ps1
streamlit run ui/app.py
```

**Features der UI**:
- 📐 Gebäude-Parameter einstellen (Größe, Geschosse, Fenster)
- 🔥 HVAC-System wählen
- ▶️ Simulation mit einem Klick starten
- 📊 Ergebnisse automatisch visualisieren
- 💾 IDF-Dateien herunterladen

---

## 🆘 Hilfe

### Simulation startet nicht?

```bash
# Prüfe ob venv aktiv ist
.\venv\Scripts\Activate.ps1

# Teste ob EnergyPlus funktioniert
python -c "from src.utils.config import get_config; print(get_config().energyplus.get_executable_path())"

# Teste Python-Pakete
python -c "import eppy; print('✅ OK')"
```

### Wetterdatei fehlt?

Download von: https://energyplus.net/weather
- Wähle: Austria → Salzburg
- Speichere in: `data/weather/salzburg.epw`

### Weitere Hilfe?

Siehe **[ANLEITUNG.md](ANLEITUNG.md)** für detaillierte Schritte.

---

## 📊 Beispiel-Ergebnisse

Nach der Simulation findest du in `output/`:
- `*.idf` - EnergyPlus Eingabedatei
- `*Table.htm` - HTML-Report mit allen Ergebnissen
- `*.csv` - Rohdaten für weitere Analyse
- `*.sql` - SQLite-Datenbank mit Zeitreihen

---

## 🚀 Los geht's!

**Variante 1 - Mit UI** (empfohlen für Einsteiger):
```bash
.\venv\Scripts\Activate.ps1
streamlit run ui/app.py
```

**Variante 2 - Batch-Datei**:
- Doppelklick auf `START_SIMULATION.bat`

**Variante 3 - Python-Code**:
- Siehe `examples/` Ordner

---

**Viel Erfolg! 🎉**
