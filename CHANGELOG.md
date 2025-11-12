# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [Unreleased]

### Added - 2025-01-12

#### 🎨 Ergebnisse-Seite: Tab-Struktur implementiert
- **5 Tabs** für bessere Übersichtlichkeit:
  - 🎯 **Übersicht**: Dashboard mit Effizienzklasse, KPIs, 4-Subplot-Dashboard, Zusammenfassung
  - 📊 **Energetische Auswertung**: Jahresbilanz, Monatliche Übersicht, Vergleich mit Standards, Export
  - 🌡️ **Behaglichkeit**: Interaktive Temperaturkurve mit Slider, Schnell-Navigation, Statistiken
  - 💰 **Wirtschaftlichkeit**: MVP-Kostenrechner mit Strom-/Gaspreis-Eingabe (Vorschau)
  - 🏗️ **Zonenauswertung**: Platzhalter für 5-Zone-Modelle (zukünftig)

#### 🌡️ Temperaturvisualisierung verbessert
- **Dashboard-Temperatur-Subplot**: Zeigt jetzt **Jahresübersicht** (365 Tage) statt nur 7 Tage
  - Tägliche Durchschnittswerte für bessere Lesbarkeit
  - Komfortbereich (20-26°C) grün markiert
  - Titel: "Raumtemperaturverlauf (Jahresübersicht)"
- **Interaktive Temperaturkurve** (Behaglichkeit-Tab):
  - Slider für beliebigen Zeitraum (Tag 1-365)
  - Auswahl: 1, 3, 7, 14, 30, 60, 90 Tage
  - Schnell-Navigation zu Jahreszeiten (Jan, Apr, Jul, Okt)
  - Live-Statistiken (Ø/Min/Max) im Titel
  - Komfortbereich-Highlighting, Heiz-/Kühl-Solltemperaturen

#### 💰 Wirtschaftlichkeitsrechner (MVP)
- Eingabefelder für Energiepreise (Strom, Gas)
- Automatische Kostenberechnung:
  - Heizkosten [€/Jahr]
  - Stromkosten [€/Jahr]
  - Gesamtkosten [€/Jahr]
  - Spezifische Kosten [€/m²a]

#### 📖 Dokumentation
- **VISION_ERGEBNISSE_TABS.md**: Umfassendes Konzept für zukünftige Features
  - Detaillierte Roadmap (5 Phasen)
  - Technische Umsetzungshinweise
  - Mockup-Beispiele

### Changed - 2025-01-12

#### 🔄 UI-Struktur optimiert
- Ergebnisse nicht mehr als lange scrollbare Seite, sondern **Tab-basiert**
- Bessere Übersichtlichkeit und Performance (Lazy Loading)
- Logische Gruppierung: Energie, Komfort, Kosten, Zonen

### Fixed - 2025-01-12

#### 🐛 Raumtemperaturverlauf
- **Problem**: Dashboard zeigte nur erste 7 Tage (Januar 1-7) ohne Navigation
- **Lösung**: Dashboard zeigt Jahresübersicht, separate interaktive Ansicht im Behaglichkeit-Tab
- **Problem**: Temperaturkurve war 2x vorhanden (Duplikat)
- **Lösung**: Dashboard = Jahresübersicht, Behaglichkeit-Tab = interaktive Detailansicht

#### 🐛 Plotly Kompatibilität
- **Problem**: `add_hrect()` funktioniert nicht mit Subplots, die Pie-Charts enthalten
- **Lösung**: Komfortbereich als gefüllten Scatter-Trace implementiert (Polygon mit `fill='toself'`)

### Removed - 2025-01-12

#### 🗑️ Backup-Dateien entfernt
- `features/web_ui/pages/_backup_01_Geometrie_old.py` (nach erfolgreicher Migration)
- `features/web_ui/pages/_backup_01a_Energieausweis_old.py` (nach erfolgreicher Migration)

---

## [Previous] - 2025-01-11

### Added - 2025-01-11

#### 🏗️ Geometrie-Seite: UI-Konsolidierung
- **Unified Geometry Page**: Zwei separate Seiten (Geometrie & Energieausweis) in eine zusammengeführt
- **Tab-basierte Navigation**:
  - Tab 1: Einfache Eingabe (SimpleBox)
  - Tab 2: Energieausweis (5-Zone-Modell)
  - Tab 3: Vorschau (3D, 2D, Fassaden, Kennzahlen)

#### 🎨 Erweiterte Visualisierungen
- **2D-Grundriss**: Top-down-Ansicht mit Zonen-Farbcodierung und Nordpfeil
- **Fassadenansichten**: 4 realistische Fassaden (N/O/S/W) mit:
  - Physikalisch korrekten Fenstergrößen (basierend auf Fenster-Daten)
  - Realistische Platzierung (Standard: 1.2m × 1.5m Fenster)
  - Window-to-Wall Ratio (WWR) Statistiken pro Orientierung
- **3D-Zonen-Ansicht**: Multi-Floor 3D-Visualisierung mit:
  - Zonen-spezifische Farben (Nord=rot, Ost=blau, Süd=grün, West=gelb, Kern=grau)
  - Alle Geschosse sichtbar
- **Geometry Metrics**: Strukturierte Anzeige von Abmessungen, Flächen, Volumen, A/V-Verhältnis

#### 🧱 Gemeinsame UI-Komponenten
- **geometry_viz.py**: Alle Visualisierungsfunktionen für Gebäudegeometrie
- **geometry_metrics.py**: Metriken-Anzeige-Funktionen
- **__init__.py**: Zentrale Exports für Komponenten

### Fixed - 2025-01-11

#### 🐛 Multi-Floor Visualisierung
- **Problem**: Nur erstes Geschoss wurde angezeigt
- **Root Cause**: Code erstellte nur Zone-Layout für `floor_number=0`
- **Lösung**: `create_multi_floor_layout()` verwendet, alle Geschosse in `all_zones_dict` gespeichert

#### 🐛 PyArrow Dependency
- **Problem**: `st.table(df)` und `st.dataframe(df)` erforderten pyarrow
- **Lösung**: HTML/Markdown-Tabellen statt pandas DataFrames

#### 🐛 BuildingModel Validation
- **Problem**: Pydantic ValidationError bei direkter Instanziierung
- **Lösung**: Factory-Methode `BuildingModel.from_simplebox()` verwendet

#### 🐛 Unrealistische Fassaden
- **Problem**: Fassaden zeigten willkürlich 3 Fenster mit falschen Größen
- **Feedback**: "sehr irreführend, sollte schon mit den Fenstergrößen und allgemeinen Geometrie passen"
- **Lösung**:
  - Integration von `FensterDistribution` für realistische Berechnungen
  - Berechnung der Fensteranzahl aus tatsächlicher Fensterfläche
  - Standard-Fenstermaße: 1.2m breit × 1.5m hoch
  - Anpassung der Breite, um exakte Fläche zu erreichen

### Changed - 2025-01-11

#### 🔄 Navigationswarnungen aktualisiert
- HVAC-Seite und Simulations-Seite verweisen auf neue Tab-Struktur der Geometrie-Seite

---

## [Previous] - 2025-01-10

### Added - 2025-01-10

#### 📚 Dokumentation
- **ISSUE_PEOPLE_CRASH.md**: Detaillierte Analyse des "People" Objekt-Fehlers
  - Root Cause: Fehlende Schedule-Definitionen
  - Workaround: People-Objekte temporär entfernt
  - GitHub Issue #5 verlinkt
- **IDF_BEST_PRACTICES.md**: Best Practices für EnergyPlus IDF-Files
  - Schedule-Management
  - Material-Definitionen
  - HVAC-Konfiguration
  - Validierung und Testing

#### 🏗️ 5-Zone Generator Fixes
- **7 kritische Bugs behoben**:
  1. ✅ Floor/Ceiling Vertex-Reihenfolge korrigiert
  2. ✅ Multi-Floor HVAC-Zuweisung repariert
  3. ✅ Zone-Naming konsistent gemacht
  4. ✅ Beleuchtung für alle Zonen hinzugefügt
  5. ✅ HVAC-Templates korrigiert
  6. ✅ Output-Variables vervollständigt
  7. ✅ Schedule-Typen korrigiert

### Fixed - 2025-01-10

#### 🐛 Floor/Ceiling Geometrie
- **Problem**: Decken/Böden hatten falsche Vertex-Reihenfolge (CW statt CCW)
- **Root Cause**: Counter-clockwise Regel von außen nach innen betrachten
- **Lösung**:
  - Böden: CW von unten gesehen (CCW von oben)
  - Decken: CCW von oben gesehen
  - Alle Floor/Ceiling Surfaces für alle Geschosse korrigiert

#### 🐛 Multi-Floor HVAC
- **Problem**: HVAC-System nur für erstes Geschoss aktiv
- **Lösung**: HVAC-Zuweisung für alle Zonen aller Geschosse implementiert

---

## Ältere Änderungen

Ältere Änderungen sind in den Git Commit Messages dokumentiert.

---

## Legende

- **Added**: Neue Features
- **Changed**: Änderungen an bestehenden Features
- **Deprecated**: Features, die bald entfernt werden
- **Removed**: Entfernte Features
- **Fixed**: Bugfixes
- **Security**: Sicherheitsfixes
