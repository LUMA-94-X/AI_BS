# Dokumentations-Übersicht

> **Vollständige Systemdokumentation des AI_BS Gebäudesimulations-Tools**
> **Erstellt:** 2025-11-14
> **Total:** 6.638 Zeilen Code-Dokumentation

---

## 📚 Dokumentations-Struktur

### Haupt-Einstieg

**[../SYSTEM_DOKUMENTATION.md](../SYSTEM_DOKUMENTATION.md)** (250 Zeilen)
- Überblick über gesamtes System
- Index zu allen 6 Detail-Dokumentationen
- Quick Start Guide
- Technologie-Stack

---

## 📖 Detail-Dokumentationen

### 01 - Web UI (1.482 Zeilen, 41K)

**[01_WEB_UI_DOKUMENTATION.md](01_WEB_UI_DOKUMENTATION.md)**

**Inhalt:**
- Alle 4 Streamlit-Seiten im Detail
- Input-Widgets und Validierung
- Session State Management
- Datenfluss zwischen Seiten
- Button-Workflows

**Für wen:**
- UI-Entwickler
- Neue Features in UI implementieren
- Session State Debug

---

### 02 - Core Module (1.172 Zeilen, 28K)

**[02_CORE_MODULE_DOKUMENTATION.md](02_CORE_MODULE_DOKUMENTATION.md)**

**Inhalt:**
- `building_model.py` - Zentrales Datenmodell
- `climate_data.py` - PLZ-Lookup & EPW-Parser
- `config.py` - Tool-Konfiguration
- `simulation_config.py` - YAML-Szenarien
- `materialien.py` - Basis-Konstruktionen

**Für wen:**
- Backend-Entwickler
- Neue Core-Features
- Config-Management

---

### 03 - Features (1.088 Zeilen, 24K)

**[03_FEATURES_DOKUMENTATION.md](03_FEATURES_DOKUMENTATION.md)**

**Inhalt:**
- **Geometrie:** five_zone_generator, geometry_solver, perimeter_calculator
- **HVAC:** ideal_loads, HVACTemplate-System
- **Auswertung:** sql_parser, kpi_rechner, visualisierung

**Für wen:**
- Feature-Entwickler
- Neue Geometrie-Modi
- Neue HVAC-Systeme
- KPI-Erweiterungen

---

### 04 - Datenfluss (815 Zeilen, 20K)

**[04_DATENFLUSS_DOKUMENTATION.md](04_DATENFLUSS_DOKUMENTATION.md)**

**Inhalt:**
- SimpleBox-Workflow (Schritt-für-Schritt)
- Energieausweis-Workflow (Schritt-für-Schritt)
- Datentransformationen
- Session State Dependencies
- YAML Export/Import

**Für wen:**
- Alle Entwickler (Gesamtverständnis)
- AI-Assistenten (Kontext für Code-Änderungen)
- Debugging

---

### 05 - IDF-Struktur (901 Zeilen, 23K)

**[05_IDF_STRUKTUR_DOKUMENTATION.md](05_IDF_STRUKTUR_DOKUMENTATION.md)**

**Inhalt:**
- Parameter-Mapping: Energieausweis → IDF
- IDF-Struktur (5-Zonen-Modell)
- **KRITISCH:** Vertex-Ordering Konventionen
- Boundary Objects (Inter-Zone Walls)
- Vollständiges IDF-Beispiel

**Für wen:**
- IDF-Generator-Entwickler
- EnergyPlus-Experten
- Surface-Generator-Debugging

---

### 06 - Simulation & Daten (820 Zeilen, 21K)

**[06_SIMULATION_DOKUMENTATION.md](06_SIMULATION_DOKUMENTATION.md)**

**Inhalt:**
- Simulations-Workflow (EnergyPlusRunner)
- Output-Dateien (SQL, ERR, CSV)
- **Aktuell genutzte Variablen:** 11 (nur 5%!)
- **Verfügbare Variablen:** 200+ (95% ungenutzt!)
- Ungenutztes Potential & Empfehlungen

**Für wen:**
- Auswertungs-Entwickler
- Neue KPIs identifizieren
- Optimierungs-Potential

---

## 🎯 Nutzungsempfehlungen

### Bei Code-Änderungen

1. **Betroffenes Modul identifizieren** (01-06)
2. **Relevante Dokumentation lesen**
3. **Änderung vornehmen**
4. **Dokumentation aktualisieren!** ← WICHTIG

### Für neue Features

1. **Passenden Abschnitt erweitern**
2. **Datenfluss-Diagramm aktualisieren** (04)
3. **IDF-Parameter-Mapping aktualisieren** (05)

### Für AI-Assistenten

- **Gesamte Dokumentation** gibt Kontext für präzise Code-Änderungen
- Verhindert unbeabsichtigte Breaking Changes
- Identifiziert überflüssige Daten/Files

### Für Wartung

- **01 - Web UI:** Welche UI-Änderungen beeinflussen welche Seiten?
- **04 - Datenfluss:** Wo werden Session State Keys gesetzt/gelesen?
- **06 - Simulation:** Welche zusätzlichen Daten können genutzt werden?

---

## 📊 Statistiken

```
Total Lines:    6.888
Total Size:     168K
Documents:      7 (1 Index + 6 Details)
Created:        2025-11-14
Language:       Markdown with Code-Blocks (Python, IDF, SQL, YAML)
```

**Detaillierte Zeilenzahlen:**

| Dokument | Zeilen | Größe | Thema |
|----------|--------|-------|-------|
| SYSTEM_DOKUMENTATION.md | 250 | 7K | Index & Übersicht |
| 01_WEB_UI | 1.482 | 41K | Streamlit Web Interface |
| 02_CORE_MODULE | 1.172 | 28K | Backend-Komponenten |
| 03_FEATURES | 1.088 | 24K | Geometrie, HVAC, Auswertung |
| 04_DATENFLUSS | 815 | 20K | Workflows & Transformationen |
| 05_IDF_STRUKTUR | 901 | 23K | EnergyPlus IDF-Mapping |
| 06_SIMULATION | 820 | 21K | Simulation & verfügbare Daten |

---

## 🔑 Wichtige Erkenntnisse

### Stärken des Systems

✅ Modularer Aufbau (leicht erweiterbar)
✅ OIB RL6 12.2-konform
✅ Robuste Validierung
✅ YAML-Export für Reproduzierbarkeit

### Kritische Punkte

⚠️ **Vertex-Ordering** (05): REVERSED für Floors, NORMAL für Ceilings
⚠️ **Boundary Objects** (05): Inter-Zone Walls paarweise + reversed
⚠️ **eppy Bug** (03): Manuelle Thermostats entfernen vor HVACTemplate
⚠️ **HVAC-Typ** (06): Nur für PEB/CO₂, NICHT im IDF!

### Ungenutztes Potential

🚀 **~95% der EnergyPlus-Daten ungenutzt!**
- Tabular Reports (vorgefertigt in SQL!)
- Zonale Unterschiede (Nord vs. Süd)
- PMV/PPD (objektiver Komfort)
- Oberflächentemperaturen
- Luftqualität (CO₂, Feuchte)

**Details:** [06_SIMULATION_DOKUMENTATION.md](06_SIMULATION_DOKUMENTATION.md)

---

## 🛠️ Wartung dieser Dokumentation

### Wann aktualisieren?

- **Neue Features:** Erweitere relevanten Abschnitt
- **Geänderte Workflows:** Update 04_DATENFLUSS
- **Neue IDF-Parameter:** Update 05_IDF_STRUKTUR
- **Neue Output-Variablen:** Update 06_SIMULATION

### Wie aktualisieren?

```bash
# 1. Betroffenes Dokument öffnen
vim docs/03_FEATURES_DOKUMENTATION.md

# 2. Änderungen vornehmen

# 3. Changelog aktualisieren (am Ende)
**Letzte Änderung:** 2025-11-XX
**Changelog:** Feature XY hinzugefügt

# 4. Commit
git add docs/
git commit -m "docs: Update 03_FEATURES - Add new geometry mode"
```

---

## 📞 Support

Bei Fragen zur Dokumentation:
- Check zuerst [SYSTEM_DOKUMENTATION.md](../SYSTEM_DOKUMENTATION.md)
- Dann relevantes Detail-Dokument (01-06)
- Nutze Suche (Ctrl+F) nach Stichworten

**Hinweis:** Diese Dokumentation wurde **automatisch generiert** durch vollständige Code-Analyse am 2025-11-14. Sie sollte bei Code-Änderungen manuell aktualisiert werden.

---

**Letzte Änderung:** 2025-11-14
**Erstellt von:** AI-gestützte vollständige Systemanalyse
