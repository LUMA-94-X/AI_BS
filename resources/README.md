# 📦 Resources

External resources und data files für EnergyPlus-Simulationen.

## 📁 Struktur

```
resources/
└── energyplus/          # EnergyPlus-spezifische Ressourcen
    ├── templates/       # IDF-Templates für verschiedene Komponenten
    └── weather/         # EPW-Wetterdateien nach Land organisiert
```

## 🎯 Zweck

Dieses Verzeichnis enthält **externe Dateien** die vom Tool verwendet werden:
- ✅ Templates (IDF-Snippets)
- ✅ Wetterdaten (EPW-Dateien)
- ✅ Material-Datenbanken (geplant)
- ✅ Standard-Konstruktionen (geplant)

**Kein Code!** Nur Daten und Templates.

## 📚 Sub-Verzeichnisse

### `energyplus/`
Alle EnergyPlus-spezifischen Ressourcen.

**Siehe:** `energyplus/README.md` für Details

---

## 🔄 Migration History

**2025-11-13:** Struktur erstellt
- Moved from `templates/` → `resources/energyplus/templates/`
- Moved from `data/weather/` → `resources/energyplus/weather/`
- Vorbereitung für zukünftige Erweiterungen (materials, standards)

---

**Erstellt:** 2025-11-13
**Projekt:** AI_BS - EnergyPlus Automation Tool
