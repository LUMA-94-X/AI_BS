# 🔧 Debug Tools

Legacy debugging and analysis scripts used during development.

## 📁 Tools

### 1. `check_sql.py`
**Zweck:** Analysiert EnergyPlus SQL-Datenbank

**Verwendung:**
```bash
python scripts/debug/check_sql.py output/simulation_*/eplusout.sql
```

**Output:**
- Tabellen-Liste
- Zeilen-Counts
- Prüfung auf Simulationserfolg

**Status:** Legacy (verwendet in BUGFIX_5ZONE_SUMMARY.md)

---

### 2. `read_errors.py`
**Zweck:** Extrahiert Errors/Warnings aus SQL-Datenbank

**Verwendung:**
```bash
python scripts/debug/read_errors.py output/simulation_*/eplusout.sql
```

**Output:**
- Alle Severe/Fatal Errors
- Warnings
- Kategorisiert nach Severity

**Status:** Legacy (verwendet in SIMULATION_CRASH_ANALYSIS.md)

---

### 3. `fix_5zone_idf.py`
**Zweck:** Upgrade existierendes IDF auf Version 25.1

**Verwendung:**
```bash
python scripts/debug/fix_5zone_idf.py input.idf output.idf
```

**Ändert:**
- VERSION auf 25.1
- Deaktiviert Sizing
- Kompatibilität für EnergyPlus 25.1

**Status:** Legacy (nicht mehr benötigt - FiveZoneGenerator erstellt korrekte IDFs)

---

### 4. `test_quick_5zone.py`
**Zweck:** Schneller Validierungs-Test für FiveZoneGenerator

**Verwendung:**
```bash
python scripts/debug/test_quick_5zone.py
```

**Testet:**
- Single floor EFH generation
- Simulation run
- Basic validation

**Status:** Legacy (ersetzt durch `tests/geometrie/generators/test_five_zone_integration.py`)

---

## ⚠️ Hinweis

Diese Tools sind **Legacy** und werden nicht mehr aktiv gewartet.

**Stattdessen verwenden:**
- **Testing:** `pytest tests/` (12 umfassende Integration-Tests)
- **SQL-Analyse:** Direkt mit sqlite3 oder EnergyPlus HTML-Reports
- **IDF-Erstellung:** `FiveZoneGenerator` (erstellt korrekte IDFs out-of-the-box)

**Aufbewahrungsgrund:** Historisch relevant für Debugging-Historie und alte Dokumentation.

---

**Erstellt:** 2025-11-13
**Status:** Archiviert
