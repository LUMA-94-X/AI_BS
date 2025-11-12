# Vision: Ergebnisse-Seite mit Tab-Struktur

## Übersicht

Die aktuelle Ergebnisse-Seite zeigt alle Informationen in einer langen, scrollbaren Seite.
Für eine bessere Übersichtlichkeit und Benutzerfreundlichkeit soll die Seite in thematische **Tabs (Reiter)** aufgeteilt werden.

## Ziel-Struktur

### 🎯 Tab 1: Übersicht (Overview)
**Zweck**: Schnelle Zusammenfassung der wichtigsten Kennzahlen auf einen Blick

**Inhalt**:
- ✅ Effizienzklasse (A+ bis G) mit großem Badge
- ✅ Energiekennzahl [kWh/m²a] als prominente Metrik
- ✅ Dashboard mit 4 Subplots (bereits vorhanden):
  - Energiebilanz (Torte): Heizung, Kühlung, Beleuchtung, Geräte
  - Spezifische Kennzahlen (Balken): Gesamt, Heizung, Kühlung
  - Monatliche Energiebilanz (gestapelte Balken)
  - Raumtemperaturverlauf (7 Tage Vorschau)
- ✅ Zusammenfassung in 3-4 Sätzen:
  - "Das Gebäude hat eine Effizienzklasse B"
  - "Der Gesamtenergiebedarf beträgt X kWh/Jahr"
  - "Heizung macht Y% des Gesamtbedarfs aus"
  - "Durchschnittstemperatur: Z°C"

**Design**:
- Clean, wenig Text, viel Visualisierung
- Große Zahlen und Metriken
- Farbcodierte Effizienzklasse

---

### 📊 Tab 2: Energetische Auswertung (Energy Analysis)
**Zweck**: Detaillierte Analyse des Energiebedarfs

**Inhalt**:

#### 2.1 Jahresbilanz
- Gesamtenergiebedarf [kWh]
- Aufschlüsselung nach Kategorien:
  - Heizung [kWh] + [kWh/m²]
  - Kühlung [kWh] + [kWh/m²]
  - Beleuchtung [kWh] + [kWh/m²]
  - Geräte [kWh] + [kWh/m²]

#### 2.2 Monatliche Detailansicht
- Tabelle: Monat | Heizung | Kühlung | Beleuchtung | Geräte | Gesamt
- Interaktives Balkendiagramm (bereits vorhanden)
- Option: Download als CSV/Excel

#### 2.3 Spitzenlasten
- Maximale Heizleistung [kW] + Zeitpunkt
- Maximale Kühlleistung [kW] + Zeitpunkt
- Visualisierung: Lastgang für Spitzenlast-Tag

#### 2.4 Energiekennzahlen
- Primärenergiebedarf (falls berechenbar)
- Endenergiebedarf
- CO₂-Emissionen (geschätzt basierend auf Energieträger)
- A/V-Verhältnis (Hüllfläche / Volumen)

**Features**:
- Export-Buttons für alle Tabellen
- Vergleich mit Referenzwerten (EnEV/GEG)
- Farbliche Bewertung (grün = gut, rot = schlecht)

---

### 🌡️ Tab 3: Behaglichkeit (Comfort Analysis)
**Zweck**: Analyse der thermischen Behaglichkeit und Raumluftqualität

**Inhalt**:

#### 3.1 Temperaturanalyse
- ✅ **Interaktive Temperaturkurve** (bereits implementiert!)
  - Slider für Zeitraum-Auswahl (Tag 1-365)
  - Auswahl: 1, 3, 7, 14, 30, 60, 90 Tage
  - Schnell-Navigation zu Jahreszeiten
- Statistiken:
  - Durchschnittstemperatur [°C]
  - Min/Max Temperatur [°C]
  - Anzahl Stunden im Komfortbereich (20-26°C)
  - Anzahl Stunden unter 20°C (Heizung aktiv)
  - Anzahl Stunden über 26°C (Kühlung aktiv)

#### 3.2 Behaglichkeitskennzahlen
- **Komfortindex**: % der Zeit im Komfortbereich
- **Überhitzungsstunden**: Anzahl Stunden > 26°C
- **Unterheizungsstunden**: Anzahl Stunden < 20°C
- **Predicted Mean Vote (PMV)**: Falls implementiert
- **Predicted Percentage Dissatisfied (PPD)**: Falls implementiert

#### 3.3 Jahreszeitliche Analyse
- Vergleich Winter/Sommer:
  - Durchschnittstemperaturen
  - Komfortzeiten
  - Heiz-/Kühlstunden
- Visualisierung: Heatmap (Tag vs. Monat)

#### 3.4 Lüftung & CO₂ (zukünftig)
- Luftwechselrate [1/h]
- CO₂-Konzentration [ppm]
- Luftfeuchte [%]

**Ziel**: Zeigen, dass das Gebäude nicht nur energieeffizient, sondern auch **behaglich** ist.

---

### 💰 Tab 4: Wirtschaftlichkeit (Economic Analysis)
**Zweck**: Kosten-Nutzen-Analyse und Wirtschaftlichkeitsberechnung

**Inhalt**:

#### 4.1 Energiekosten (Jahresbasis)
- Eingabefelder für Energiepreise:
  - Strompreis [€/kWh] (Default: 0.30 €/kWh)
  - Gaspreis [€/kWh] (Default: 0.08 €/kWh)
  - Fernwärmepreis [€/kWh] (Default: 0.10 €/kWh)
- Berechnete Kosten:
  - Heizkosten [€/Jahr] + [€/m²a]
  - Kühlkosten [€/Jahr] + [€/m²a]
  - Stromkosten (Beleuchtung + Geräte) [€/Jahr]
  - **Gesamtkosten [€/Jahr]**

#### 4.2 Vergleichsszenarien
- Vergleich mit Referenzgebäude:
  - "Ihr Gebäude ist X% effizienter als Referenz"
  - "Einsparung: Y €/Jahr"
- Was-wäre-wenn-Szenarien:
  - "Bei 20% schlechterer Dämmung: +Z €/Jahr"
  - "Bei PV-Anlage (5 kWp): -W €/Jahr"

#### 4.3 Amortisationsrechnung (zukünftig)
- Investitionskosten für Effizienzmaßnahmen
- Amortisationszeit
- Net Present Value (NPV)
- Internal Rate of Return (IRR)

#### 4.4 Fördermittel-Hinweise (zukünftig)
- Hinweise zu KfW-Förderung
- BAFA-Förderung
- Regionale Förderprogramme

**Features**:
- Interaktive Eingabefelder für Preise
- Echtzeit-Neuberechnung
- Vergleichsgrafik (Balken: Ist vs. Referenz)

---

### 🏗️ Tab 5: Zonenauswertung (Zone Analysis)
**Zweck**: Detaillierte Analyse einzelner Zonen (für 5-Zone-Modelle)

**Inhalt**:

#### 5.1 Zonenauswahl
- Dropdown oder Radio-Buttons:
  - Nord-Zone
  - Ost-Zone
  - Süd-Zone
  - West-Zone
  - Kern-Zone

#### 5.2 Zonen-Kennzahlen
Für gewählte Zone:
- Fläche [m²]
- Volumen [m³]
- Außenwandfläche [m²]
- Fensterfläche [m²]
- WWR (Window-to-Wall Ratio) [%]

#### 5.3 Zonen-Energiebedarf
- Heizenergie [kWh] + [kWh/m²]
- Kühlenergie [kWh] + [kWh/m²]
- Beleuchtung [kWh] + [kWh/m²]
- Geräte [kWh] + [kWh/m²]
- **Gesamt [kWh/m²a]**

#### 5.4 Zonen-Temperaturverlauf
- Temperaturkurve für gewählte Zone
- Vergleich mit anderen Zonen (overlay)
- Statistiken (Min/Max/Durchschnitt)

#### 5.5 Vergleich aller Zonen
- Tabelle: Zone | Energiebedarf | Temperatur | Komfortindex
- Balkendiagramm: Energiebedarf pro Zone
- Heatmap: Temperaturverteilung über das Jahr

**Erkenntnisse**:
- "Nord-Zone hat höchsten Heizbedarf"
- "Süd-Zone profitiert von solaren Gewinnen"
- "Kern-Zone hat stabilste Temperatur"

**Besonderheit**:
- Nur für 5-Zone-Modelle relevant
- Bei SimpleBox: Tab ausblenden oder Hinweis anzeigen

---

## Technische Umsetzung

### Streamlit-Tabs
```python
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Übersicht",
    "📊 Energetische Auswertung",
    "🌡️ Behaglichkeit",
    "💰 Wirtschaftlichkeit",
    "🏗️ Zonenauswertung"
])

with tab1:
    # Übersicht-Inhalt
    ...

with tab2:
    # Energetische Auswertung
    ...

# etc.
```

### Datenquellen
- **SQL-Datei** (eplusout.sql): Zeitreihendaten, Zonen-spezifische Daten
- **EnergyPlusSQLParser**: Bereits vorhanden, evtl. erweitern
- **GebaeudeKennzahlen**: Bereits vorhanden (kpi_rechner.py)
- **BuildingModel**: Session State für Geometrie/Zonen-Info

### Neue Features benötigt
1. **Zonen-spezifische Abfragen**:
   - `get_zone_temperature(zone_name: str) -> pd.DataFrame`
   - `get_zone_energy(zone_name: str) -> Dict`

2. **Behaglichkeitsmetriken**:
   - `calculate_comfort_hours() -> Dict`
   - `calculate_comfort_index() -> float`

3. **Wirtschaftlichkeitsrechner**:
   - `calculate_energy_costs(strompreis, gaspreis) -> Dict`
   - `compare_to_reference() -> Dict`

4. **Visualisierungen**:
   - Jahres-Heatmap (Tag vs. Monat)
   - Zonen-Vergleichsdiagramme

---

## Vorteile der Tab-Struktur

✅ **Übersichtlichkeit**: Nutzer sehen nur relevante Informationen
✅ **Performance**: Tabs werden lazy geladen
✅ **Zielgruppen**: Verschiedene Nutzer interessieren sich für verschiedene Aspekte
✅ **Erweiterbarkeit**: Neue Tabs können leicht hinzugefügt werden
✅ **Export**: Jeder Tab kann eigene Export-Funktionen haben

---

## Roadmap

### Phase 1: Struktur aufbauen ✅ (geplant)
- Tabs erstellen
- Bestehende Inhalte umverteilen
- Navigation testen

### Phase 2: Behaglichkeit erweitern ✅ (bereits begonnen!)
- ✅ Interaktive Temperaturkurve (implementiert)
- Komfortindex berechnen
- Jahres-Heatmap

### Phase 3: Wirtschaftlichkeit
- Kostenrechner implementieren
- Preiseingabe-UI
- Vergleichsszenarien

### Phase 4: Zonenauswertung
- Zonen-spezifische SQL-Abfragen
- Zonen-Vergleich
- Zone-Selection UI

### Phase 5: Erweiterte Features
- PDF-Export pro Tab
- Benchmarking
- KI-basierte Empfehlungen

---

## Offene Fragen

1. **Export**: Soll jeder Tab einen eigenen Export-Button haben?
2. **Vergleich**: Mehrere Simulationen vergleichen?
3. **Historische Daten**: Mehrere Simulationen speichern und vergleichen?
4. **Externe Daten**: Integration von Wetterdaten-Visualisierung?

---

## Beispiel-Screenshots (Mockup-Ideen)

### Tab 1: Übersicht
```
┌─────────────────────────────────────────────┐
│  Effizienzklasse: B  (85 kWh/m²a)          │
│                                             │
│  [Dashboard mit 4 Subplots]                 │
│                                             │
│  "Ihr Gebäude verbraucht 15% weniger als    │
│   der Durchschnitt für Wohngebäude."        │
└─────────────────────────────────────────────┘
```

### Tab 3: Behaglichkeit
```
┌─────────────────────────────────────────────┐
│  [Slider: Tag 1 ──●────────────── 365]      │
│  [Select: 7 Tage anzeigen]                  │
│                                             │
│  [Temperaturkurve mit Komfortbereich]       │
│                                             │
│  Komfortindex: 92%                          │
│  Überhitzungsstunden: 124h (1.4%)           │
└─────────────────────────────────────────────┘
```

### Tab 5: Zonenauswertung
```
┌─────────────────────────────────────────────┐
│  Zone: [Nord ▼]                             │
│                                             │
│  Energiebedarf: 92 kWh/m²a                  │
│  Ø Temperatur: 21.2°C                       │
│                                             │
│  [Vergleich mit anderen Zonen - Balken]     │
└─────────────────────────────────────────────┘
```

---

## Status
**Erstellt**: 2025-11-12
**Version**: 1.0 (Vision)
**Nächster Schritt**: User-Feedback einholen
**Implementierung**: Noch nicht gestartet (außer interaktive Temperaturkurve ✅)
