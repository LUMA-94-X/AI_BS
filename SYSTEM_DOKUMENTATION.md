# AI_BS - Gebäudesimulations-Tool: Vollständige Systemdokumentation

> **Zuletzt aktualisiert:** 2025-11-14
> **Version:** 1.0
> **Zweck:** Umfassende Dokumentation des gesamten Systems von Input bis Output

---

## 📋 Übersicht

Dieses Tool ist eine **webbasierte Gebäudesimulations-Anwendung** für energetische Bewertungen nach **deutschen (EnEV)** und **österreichischen (OIB RL6 12.2)** Standards. Es kombiniert:

- **Streamlit Web UI** für einfache Bedienung
- **EnergyPlus** als Simulationsengine
- **5-Zonen-Modellierung** für detaillierte Gebäudeanalyse
- **Österreichische Energieausweis-Kennzahlen** (HWB, PEB, CO₂)

---

## 🗂️ Dokumentations-Struktur

Die Dokumentation ist in 6 Module aufgeteilt:

### ✅ [01 - Web UI Dokumentation](docs/01_WEB_UI_DOKUMENTATION.md)
**Was:** Alle 4 Streamlit-Seiten im Detail
**Inhalt:**
- Seite 01: Geometrie (SimpleBox + Energieausweis)
- Seite 02: HVAC-Konfiguration
- Seite 03: Simulation
- Seite 04: Ergebnisse
- Session State Variablen
- Datenfluss zwischen Seiten

### ✅ [02 - Core Module Dokumentation](docs/02_CORE_MODULE_DOKUMENTATION.md)
**Was:** Zentrale Backend-Komponenten
**Inhalt:**
- `building_model.py` - Einheitliches Gebäudemodell
- `climate_data.py` - Klimadaten-Datenbank & EPW-Parser
- `config.py` - Konfigurationsmanagement
- `simulation_config.py` - YAML-basierte Szenario-Konfiguration
- `materialien.py` - Baumaterialien & Konstruktionen

### ✅ [03 - Features Dokumentation](docs/03_FEATURES_DOKUMENTATION.md)
**Was:** Geometrie, HVAC, Auswertung
**Inhalt:**
- **Geometrie:** five_zone_generator, geometry_solver, perimeter_calculator
- **HVAC:** ideal_loads, HVACTemplate-System
- **Auswertung:** sql_parser, kpi_rechner, visualisierung

### ✅ [04 - Datenfluss Dokumentation](docs/04_DATENFLUSS_DOKUMENTATION.md)
**Was:** Vollständiger Datenfluss von Input bis Output
**Inhalt:**
- User Input → Geometrie-Generierung
- Geometrie → IDF-File
- IDF → EnergyPlus Simulation
- SQL-Output → KPI-Berechnung
- KPIs → Visualisierung
- Zwei parallele Workflows (SimpleBox vs. Energieausweis)

### ✅ [05 - IDF-Struktur Dokumentation](docs/05_IDF_STRUKTUR_DOKUMENTATION.md)
**Was:** EnergyPlus IDF-File im Detail
**Inhalt:**
- Welche Daten aus dem Input werden ins IDF übernommen?
- Komplette IDF-Struktur (Zonen, Surfaces, HVAC, Schedules)
- Parameter-Mapping (Energieausweis → IDF)
- Kritische EnergyPlus-Konventionen (Vertex-Ordering, Boundary Objects)

### ✅ [06 - Simulation & Verfügbare Daten](docs/06_SIMULATION_DOKUMENTATION.md)
**Was:** Simulationsprozess und Output-Daten
**Inhalt:**
- Wie wird die Simulation gestartet? (Runner, ExpandObjects)
- Welche Output-Dateien werden erzeugt? (SQL, ERR, CSV)
- Welche Daten werden aktuell genutzt? (11 Output-Variablen)
- **Welche Daten sind verfügbar aber NICHT genutzt?** (100+ Variablen!)
- Ungenutztes Potential & Empfehlungen

---

## 🎯 Zielgruppe dieser Dokumentation

1. **Entwickler** - Verstehen der System-Architektur
2. **AI-Assistenten** - Kontextuelle Code-Änderungen ohne Fehler
3. **Maintainer** - Identifikation von überflüssigen Daten/Files
4. **Power-User** - Erweiterte Anpassungen

---

## 🚀 Quick Start

### Hauptworkflow

```
1. Geometrie-Seite → Gebäude definieren (SimpleBox ODER Energieausweis)
2. HVAC-Seite → Heizsystem konfigurieren
3. Simulation-Seite → EnergyPlus-Simulation starten
4. Ergebnisse-Seite → KPIs, Grafiken, Energieausweis
```

### Zwei Workflows

| Workflow | Eingabe | Output | Zonen | Use Case |
|----------|---------|--------|-------|----------|
| **SimpleBox** | L × W × H, WWR | IDF on-the-fly | n Zonen (1 pro Geschoss) | Schnelle Machbarkeitsstudien |
| **Energieausweis** | OIB RL6 12.2 Daten | IDF aus File | 5×n Zonen | Österreichischer Energieausweis |

---

## 📊 Datenfluss-Übersicht

```mermaid
graph LR
    A[User Input] --> B[Geometrie-Generator]
    B --> C[IDF-File]
    C --> D[EnergyPlus]
    D --> E[SQL-Output]
    E --> F[KPI-Rechner]
    F --> G[Visualisierung]
    G --> H[Web UI]
```

**Detailliert:** Siehe [04 - Datenfluss Dokumentation](docs/04_DATENFLUSS_DOKUMENTATION.md)

---

## 🔑 Schlüssel-Komponenten

### Core-Datenmodell: `BuildingModel`

Einheitliches Modell für beide Workflows:

```python
BuildingModel:
  - source: "simplebox" | "energieausweis" | "oib_energieausweis"
  - geometry_summary: {L, W, H, floors, areas, A/V, ...}
  - idf_path: Path
  - num_zones: int
  - has_hvac: bool
  - energieausweis_data: Dict (vollständige OIB-Daten)
```

### Simulation-Kette

```
Input → GeometrySolver → FiveZoneGenerator → IDF
      → HVACTemplateManager → IDF mit HVAC
      → ExpandObjects → Vollständiges IDF
      → EnergyPlus → eplusout.sql
      → SQLParser → ErgebnisUebersicht
      → KennzahlenRechner → GebaeudeKennzahlen
      → Visualisierer → Charts
```

---

## 📈 Kennzahlen

### Deutsche Standards (EnEV)
- **Energiekennzahl** [kWh/m²a] - Gesamtenergiebedarf
- **Effizienzklasse** A+ bis H

### Österreichische Standards (OIB RL6)
- **HWB** - Heizwärmebedarf
- **EEB** - Endenergiebedarf
- **PEB** - Primärenergiebedarf (mit Konversionsfaktoren)
- **CO₂** - Emissionen [kg/m²a]
- **f_GEE** - Gesamtenergieeffizienz-Faktor
- **OIB-Effizienzklasse** A++ bis G

---

## ⚠️ Kritische Erkenntnisse

### ✅ Stärken
- Modularer Aufbau (leicht erweiterbar)
- OIB RL6 12.2-konform
- Robuste Validierung
- YAML-Export für Reproduzierbarkeit

### ⚠️ Ungenutztes Potential
- **Aktuell genutzt:** 11 Output-Variablen (~5% verfügbar)
- **Verfügbar aber NICHT genutzt:**
  - Zonale Unterschiede (Nord/Ost/Süd/West/Kern)
  - Oberflächentemperaturen
  - Komfort-Indizes (PMV/PPD)
  - Luftqualität (CO₂, Feuchte)
  - 100+ weitere EnergyPlus-Variablen

**Details:** [06 - Simulation Dokumentation](docs/06_SIMULATION_DOKUMENTATION.md)

---

## 🛠️ Entwicklungs-Roadmap

### Kurzfristig
- [ ] U-Wert-basierte Konstruktionsgenerierung
- [ ] Zonale Auswertung (5-Zonen-Vergleich)
- [ ] Erweiterte Output-Variablen (PMV/PPD, Luftfeuchte)

### Mittelfristig
- [ ] Weitere HVAC-Templates (VAV, Fan Coil)
- [ ] EPW-Import für präzise Wetterdaten
- [ ] Variantenstudien-Tool

### Langfristig
- [ ] Komplexere Gebäudeformen (L-Form, Innenhöfe)
- [ ] Detaillierte HVAC-Systeme
- [ ] LCCA (Life Cycle Cost Analysis)

---

## 📝 Wie diese Dokumentation nutzen?

### Bei Code-Änderungen:
1. Betroffenes Modul identifizieren (01-06)
2. Relevante Dokumentation lesen
3. Änderung vornehmen
4. **Dokumentation aktualisieren!**

### Bei neuen Features:
1. Passenden Dokumentations-Abschnitt erweitern
2. Datenfluss-Diagramm aktualisieren (04)
3. IDF-Parameter-Mapping aktualisieren (05)

### Für AI-Assistenten:
- Gesamte Dokumentation gibt Kontext für präzise Code-Änderungen
- Verhindert unbeabsichtigte Breaking Changes
- Identifiziert überflüssige Daten/Files

---

## 📚 Anhang

### Technologie-Stack
- **Frontend:** Streamlit 1.28+
- **Simulation:** EnergyPlus 23.2
- **Geometrie:** eppy 0.5.63
- **Datenvalidierung:** Pydantic 2.x
- **Visualisierung:** Plotly 5.x
- **Datenbank:** SQLite3 (eplusout.sql)

### Wichtige Konventionen
- **Session State Keys:** `building_model`, `hvac_config`, `simulation_result`
- **IDF-Vertex-Order:** Counter-clockwise für Wände, REVERSED für Böden
- **U-Werte:** [W/m²K]
- **Energien:** SQL in [J], KPIs in [kWh] oder [kWh/m²a]

---

**Letzte Änderung:** 2025-11-14
**Changelog:** Initial creation - Vollständige Systemanalyse
