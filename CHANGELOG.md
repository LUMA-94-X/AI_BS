# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [Unreleased]

### Fixed - 2025-11-14

#### 🔧 Design Loads: Fallback für IdealLoadsAirSystem
- **Problem**: HVAC Design Loads waren 0 trotz korrekter IDF-Konfiguration
- **Root Cause**: `HVACTemplate:Zone:IdealLoadsAirSystem` erzeugt keine physischen HVAC-Komponenten (Coils, Fans, Pumps), daher bleiben die Tabular Reports `HVACSizingSummary` leer
- **Lösung**: Intelligente Fallback-Logik implementiert
  - Neue Methode `_get_design_loads_from_timeseries()` in `tabular_reports.py`
  - Extrahiert MAX-Werte aus `Zone Ideal Loads Zone Total Heating/Cooling Rate`
  - Design Days aus `SizingPeriod:DesignDay` Tabular Data
  - Automatische Umschaltung wenn Tabular Reports leer sind (alle Werte = 0)
- **Ergebnis**: Design Loads werden jetzt korrekt angezeigt (~1,78 kW Heizlast statt 0)
- **Limitation**: IdealLoadsAirSystem kann keine spezifischen Lasten pro m² liefern (nur Gesamt-kW)
- **Betroffene Datei**: `features/auswertung/tabular_reports.py` (+67 Zeilen)

### Added - 2025-11-14

#### 📊 Tabular Reports - Erweiterte EnergyPlus Auswertung
- **Neues Modul**: `features/auswertung/tabular_reports.py`
  - `TabularReportParser` Klasse zur Auswertung vorgefertigter EnergyPlus Summary Reports
  - 4 Datenklassen: `EndUseSummary`, `SiteSourceEnergy`, `HVACSizing`, `EnvelopePerformance`
  - Direkter Zugriff auf 25+ vorgefertigte EnergyPlus Reports aus SQL-Datenbank
  - **Vorteil**: Keine manuelle Summierung von 8760 Zeitreihen-Werten erforderlich!

- **SQL-Parser Integration**:
  - Neue Methoden in `EnergyPlusSQLParser`:
    - `get_tabular_summaries()` - Alle Reports auf einmal
    - `get_end_use_breakdown()` - Detaillierte Verbrauchsaufteilung
    - `get_hvac_design_loads()` - HVAC Auslegungslasten

- **KPI-Rechner erweitert**:
  - Neue Datenklasse `ErweiterteKennzahlen` mit Tabular Data
  - Neue Methode `berechne_erweiterte_kennzahlen()` kombiniert Standard- und Tabular-Metriken

- **Neue Visualisierungen** (`visualisierung.py`):
  - `erstelle_detailliertes_end_use_chart()` - Pie Chart mit Fans, Pumps, Sonstiges
  - `erstelle_hvac_design_loads_chart()` - Absolute & spezifische Lasten
  - `erstelle_site_source_energy_chart()` - Site vs. Source Energy Vergleich
  - `erstelle_erweiterte_uebersicht()` - Dashboard mit allen Tabular Reports

- **UI-Integration** (Ergebnisse-Seite):
  - **Neuer Sub-Tab**: "📈 Tabular Reports (Erweitert)" unter "Energetische Auswertung"
  - Metriken-Anzeige:
    - **End Use Breakdown**: Heizung, Kühlung, Beleuchtung, Geräte, Ventilatoren, Pumpen
    - **Energieträger**: Strom vs. Gas Aufschlüsselung
    - **Site vs. Source Energy**: Endenergie vs. Primärenergie Vergleich
    - **HVAC Design Loads**: Heiz-/Kühllast mit Auslegungstag-Info
    - **Envelope**: Wandfläche, Fensterfläche, Dachfläche mit U-Werten
  - Interaktive Plotly Charts für alle Metriken
  - Button "Erweiterte Übersicht anzeigen" für kombiniertes Dashboard

- **Vorteile der Tabular Reports**:
  - ✅ Instant-Zugriff auf aggregierte Daten (keine Zeitreihen-Summierung)
  - ✅ 95% ungenutztes EnergyPlus-Potential jetzt verfügbar
  - ✅ Detailliertere End-Use Breakdown (inkl. Fans, Pumps)
  - ✅ Primärenergie-Analyse (Site vs. Source)
  - ✅ HVAC-Dimensionierung (Design Loads mit Auslegungstag)

#### 🏭 Gebäudetechnik-Systeme: Trennung von Heiz- und Lüftungssystem
- **HVAC-Seite erweitert**:
  - Separate Auswahl für **Heizsystem** (Wärmeerzeuger):
    - Ideal Loads Air System
    - Gas-Brennwertkessel
    - Öl-Brennwertkessel
    - Biomasse-Kessel
    - Wärmepumpe
    - Fernwärme / Fernwärme KWK / Fernwärme Heizwerk
  - Separate Auswahl für **Lüftungssystem**:
    - Ideal Loads Air System
    - Mechanische Lüftung mit WRG (Wärmerückgewinnung)
    - Mechanische Lüftung ohne WRG
    - Natürliche Lüftung
  - Anzeige von OIB RL6 Konversionsfaktoren für gewähltes Heizsystem
  - Systemeigenschaften-Darstellung (WRG-Effizienz, etc.)

#### 📊 OIB RL6 Konversionsfaktoren-Modul
- **Neues Modul**: `data/oib_konversionsfaktoren.py`
  - Vollständige Implementierung von OIB RL6 § 7 (Tabelle 7)
  - 11 Energieträger mit Primärenergie- und CO₂-Faktoren:
    - Kohle, Heizöl, Erdgas, Biomasse
    - Strom-Mix Österreich
    - Fernwärme (erneuerbar/fossil/KWK)
    - Abwärme
  - Mapping von HVAC-Systemen zu Referenz-Wärmeerzeugern (OIB RL6 § 9.2)
  - Berechnungsfunktionen: `berechne_peb()`, `berechne_co2()`

#### 🔋 Primärenergiebedarf (PEB) & CO₂-Berechnung
- **PEB-Berechnung implementiert**:
  - Formel: `PEB = EEB × f_PE` (Endenergiebedarf × Primärenergiefaktor)
  - Abhängig vom gewählten Heizsystem
  - Automatische Berechnung wenn HVAC-System konfiguriert
- **CO₂-Berechnung implementiert**:
  - Formel: `CO₂ = EEB × f_CO₂` (in kg/m²a)
  - Systemspezifische Emissionsfaktoren
- **Energieausweis-Anzeige**:
  - PEB und CO₂ zeigen berechnete Werte statt "k.A."
  - Info-Box zeigt verwendetes Heiz-/Lüftungssystem
  - Warnung wenn kein System gewählt (PEB nicht berechenbar)

#### 🏗️ Mittlerer U-Wert Übertragung
- **Geometrie → Energieausweis**:
  - Flächengewichteter U-Wert aus Geometrie-Eingabe
  - Automatisch in `geometry_summary['oib_mittlerer_u_wert']` gespeichert
  - Korrekte Anzeige im Energieausweis statt "k.A."

### Changed - 2025-11-14

#### 🔄 HVAC-Konfigurationsstruktur erweitert
- `hvac_config` enthält jetzt:
  - `type`: Legacy-Feld (=Heizsystem für Kompatibilität)
  - `heating_system`: Neues Feld für Wärmeerzeuger
  - `ventilation_system`: Neues Feld für Lüftungsart
- Rückwärtskompatibilität gewährleistet durch Fallback-Logik

#### 📊 Kennzahlen-Berechnung erweitert
- `kpi_rechner.py`:
  - Liest `hvac_config` aus `building_model` (dict oder Pydantic-Objekt)
  - Verwendet `heating_system` für PEB/CO₂-Berechnung
  - Extrahiert `oib_mittlerer_u_wert` aus `geometry_summary`
- `04_Ergebnisse.py`:
  - Konvertiert Pydantic `BuildingModel` zu dict für `hvac_config`-Übergabe
  - Zeigt verwendete Systeme im Energieausweis-Tab

### Fixed - 2025-11-14

#### 🐛 Streamlit UI-Fehler
- **Problem**: `st.info()` unterstützt kein `unsafe_allow_html`
- **Lösung**: Parameter entfernt, HTML-Subscripts zu Plain Text (f_GEE, ℓc)
- Betroffen: Zeilen 533, 542 in `04_Ergebnisse.py`

#### 🐛 HVAC Variable-Fehler
- **Problem**: `NameError: name 'hvac_type' is not defined` in Konfigurationsübersicht
- **Lösung**: Verwende Werte aus `session_state['hvac_config']` statt lokale Variablen
- Betroffen: `02_HVAC.py:372`

#### 🐛 Pydantic BuildingModel Kompatibilität
- **Problem**: `"BuildingModel" object has no field "hvac_config"` (Pydantic erlaubt keine dynamischen Felder)
- **Lösung**: Konvertierung zu dict mit `geometry_summary` + `hvac_config`
- Betroffen: `04_Ergebnisse.py:88-95`

### Added - 2025-11-13

#### 🇦🇹 Energieausweis-Erweiterung: Österreichische Kennzahlen
- **Input-Anpassungen** (Energieausweis-Variante):
  - `Nettogrundfläche` → `Bruttogrundfläche` (inkl. Wände)
  - Neue optionale Kennwerte: Brutto-Volumen, Kompaktheit (A/V), Charakteristische Länge (lc)
  - Mittlerer U-Wert (flächengewichtet, mit Auto-Berechnung)
  - Bauweise-Auswahl (Massiv/Leicht)

- **Output-Kennzahlen** (Österreichischer Energieausweis):
  - **Energiebedarfe**: HWB, WWWB (k.A.), EEB, HEB (k.A.), PEB (k.A.), CO² (k.A.)
  - **Wärmebilanz**: QT (Transmissionswärmeverluste), QV (Lüftungswärmeverluste)
  - **Wärmegewinne**: Solare Gewinne, Innere Gewinne (Lights + Equipment + People)
  - **Auslegungslasten**: Heizlast, Kühllast
  - Nicht verfügbare Kennzahlen werden als "k.A." angezeigt mit Erklärung

- **HVAC-Steuerung**:
  - Checkboxen zum Aktivieren/Deaktivieren von Heizung und Kühlung
  - UI-Integration in HVAC-Einstellungen

- **Neue EnergyPlus Output-Variablen**:
  - `Zone Ideal Loads Zone Total Heating/Cooling Rate` (Lastspitzen)
  - `Surface Average Face Conduction Heat Transfer Energy` (QT)
  - `Zone Infiltration/Ventilation Sensible Heat Gain Energy` (QV)
  - `Zone Windows Total Heat Gain Energy` (Solar)
  - `Zone Lights/Equipment/People Total Heating Energy` (Intern)

- **Ergebnisse-Anzeige**:
  - Neue Sektion "🇦🇹 Energieausweis-Kennzahlen (Österreich)" in Tab "Energetische Auswertung"
  - Strukturierte Darstellung: Energiebedarfe, Wärmebilanz, Auslegungslasten
  - Tooltips mit Erklärungen zu allen Kennzahlen

### Fixed - 2025-11-13

#### ⚡ Heizlast/Kühllast zeigen jetzt korrekte Werte
- **Problem**: Heizlast/Kühllast waren immer 0
- **Ursache**: Falsche EnergyPlus Output-Variablen für Ideal Loads System
- **Fix**:
  - Alt: `"Zone Air System Sensible Heating/Cooling Rate"`
  - Neu: `"Zone Ideal Loads Zone Total Heating/Cooling Rate"`
- Heiz-/Kühllasten werden jetzt korrekt aus der Simulation ausgelesen

### Changed - 2025-11-13

#### 🔄 Datenmodell-Anpassungen
- `EnergieausweisInput.nettoflaeche_m2` → `bruttoflaeche_m2`
- `GeometrySolver` verwendet Bruttofläche für Berechnungen
- `SimulationConfig.EnergieausweisParams` aktualisiert
- 10 Dateien aktualisiert für Konsistenz

#### 📊 Geometrie-Metriken erweitert
- Anzeige von Brutto-Volumen, Charakteristische Länge, Kompaktheit
- Mittlerer U-Wert in erweiterten Kennzahlen
- Bauweise-Anzeige

### Known Issues - 2025-11-13

⚠️ **Siehe Issue #7**:
1. **Bug**: HVAC Kühlung-Deaktivierung funktioniert nicht (Simulation läuft trotzdem mit Kühlung)
2. **UI**: Layout-Optimierung erforderlich (zu viele neue Eingabefelder, überladen)

---

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
