"""
Klimadaten-System für österreichische Gebäudesimulation.

Bietet 3 Modi:
1. Manuelle Eingabe: Nutzer gibt Klimadaten direkt ein
2. Datenbank: Lookup nach PLZ (österreichische Klimazonen nach ÖNORM B 8110-5)
3. EPW: Berechnung aus EPW-Wetterdatei

Autor: Claude Code
Datum: 2025-11-14
"""

from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ClimateData(BaseModel):
    """Klimadaten für eine Region/Standort."""

    klimaregion: str = Field(
        ...,
        description="Klimaregion (z.B. 'Ost', 'West', 'Süd', 'Nord')"
    )

    heizgradtage_kd: float = Field(
        ...,
        gt=0,
        lt=10000,
        description="Heizgradtage [Kd] für 20°C Heizgrenze"
    )

    heiztage: int = Field(
        ...,
        gt=0,
        lt=366,
        description="Anzahl Heiztage [-]"
    )

    norm_aussentemperatur_c: float = Field(
        ...,
        gt=-30,
        lt=10,
        description="Norm-Außentemperatur für Heizlastberechnung [°C]"
    )

    # Optional: Zusätzliche Klimadaten
    kuehlgradtage_kd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Kühlgradtage [Kd] für 26°C Kühlgrenze (optional)"
    )

    jahresmitteltemperatur_c: Optional[float] = Field(
        default=None,
        gt=-10,
        lt=20,
        description="Jahresmitteltemperatur [°C] (optional)"
    )

    hoehe_m: Optional[int] = Field(
        default=None,
        ge=0,
        lt=4000,
        description="Höhe über Meer [m] (optional)"
    )


# ============ ÖSTERREICHISCHE KLIMADATENBANK ============
# Basierend auf ÖNORM B 8110-5 und klimatischen Regionen

AUSTRIA_CLIMATE_DATABASE: Dict[str, Dict[str, Any]] = {
    # Ostösterreich (Pannonisches Klima)
    "Wien": {
        "klimaregion": "Ost",
        "heizgradtage_kd": 3400,
        "heiztage": 220,
        "norm_aussentemperatur_c": -12,
        "kuehlgradtage_kd": 150,
        "jahresmitteltemperatur_c": 10.4,
        "hoehe_m": 200,
        "plz_ranges": [(1000, 1239), (2000, 2490), (7000, 7143)]
    },
    "Eisenstadt": {
        "klimaregion": "Ost",
        "heizgradtage_kd": 3300,
        "heiztage": 215,
        "norm_aussentemperatur_c": -12,
        "kuehlgradtage_kd": 160,
        "jahresmitteltemperatur_c": 10.8,
        "hoehe_m": 180,
        "plz_ranges": [(7000, 7143)]
    },

    # Westösterreich (Alpines Klima)
    "Innsbruck": {
        "klimaregion": "West",
        "heizgradtage_kd": 3800,
        "heiztage": 240,
        "norm_aussentemperatur_c": -16,
        "kuehlgradtage_kd": 80,
        "jahresmitteltemperatur_c": 9.0,
        "hoehe_m": 580,
        "plz_ranges": [(6000, 6699)]
    },
    "Bregenz": {
        "klimaregion": "West",
        "heizgradtage_kd": 3600,
        "heiztage": 230,
        "norm_aussentemperatur_c": -14,
        "kuehlgradtage_kd": 90,
        "jahresmitteltemperatur_c": 9.5,
        "hoehe_m": 400,
        "plz_ranges": [(6700, 6993)]
    },

    # Südösterreich (Mediterran beeinflusst)
    "Graz": {
        "klimaregion": "Süd",
        "heizgradtage_kd": 3500,
        "heiztage": 225,
        "norm_aussentemperatur_c": -14,
        "kuehlgradtage_kd": 140,
        "jahresmitteltemperatur_c": 9.9,
        "hoehe_m": 350,
        "plz_ranges": [(8000, 8990)]
    },
    "Klagenfurt": {
        "klimaregion": "Süd",
        "heizgradtage_kd": 3700,
        "heiztage": 235,
        "norm_aussentemperatur_c": -15,
        "kuehlgradtage_kd": 120,
        "jahresmitteltemperatur_c": 8.9,
        "hoehe_m": 450,
        "plz_ranges": [(9000, 9990)]
    },

    # Zentralösterreich (Übergangsklima)
    "Linz": {
        "klimaregion": "Nord",
        "heizgradtage_kd": 3600,
        "heiztage": 230,
        "norm_aussentemperatur_c": -14,
        "kuehlgradtage_kd": 110,
        "jahresmitteltemperatur_c": 9.3,
        "hoehe_m": 260,
        "plz_ranges": [(4000, 4992)]
    },
    "Salzburg": {
        "klimaregion": "Nord",
        "heizgradtage_kd": 3700,
        "heiztage": 235,
        "norm_aussentemperatur_c": -15,
        "kuehlgradtage_kd": 100,
        "jahresmitteltemperatur_c": 9.0,
        "hoehe_m": 430,
        "plz_ranges": [(5000, 5630)]
    },
    "St. Pölten": {
        "klimaregion": "Nord",
        "heizgradtage_kd": 3500,
        "heiztage": 225,
        "norm_aussentemperatur_c": -14,
        "kuehlgradtage_kd": 120,
        "jahresmitteltemperatur_c": 9.5,
        "hoehe_m": 270,
        "plz_ranges": [(3000, 3943)]
    },
}


def get_climate_data_by_plz(plz: int) -> Optional[ClimateData]:
    """
    Gibt Klimadaten basierend auf österreichischer Postleitzahl zurück.

    Args:
        plz: Postleitzahl (1000-9999)

    Returns:
        ClimateData-Objekt oder None wenn PLZ nicht gefunden

    Beispiel:
        >>> climate = get_climate_data_by_plz(1010)  # Wien
        >>> print(climate.heizgradtage_kd)
        3400
    """
    if not (1000 <= plz <= 9999):
        return None

    # Durchsuche Datenbank nach passender PLZ
    for city, data in AUSTRIA_CLIMATE_DATABASE.items():
        for plz_min, plz_max in data.get("plz_ranges", []):
            if plz_min <= plz <= plz_max:
                return ClimateData(
                    klimaregion=data["klimaregion"],
                    heizgradtage_kd=data["heizgradtage_kd"],
                    heiztage=data["heiztage"],
                    norm_aussentemperatur_c=data["norm_aussentemperatur_c"],
                    kuehlgradtage_kd=data.get("kuehlgradtage_kd"),
                    jahresmitteltemperatur_c=data.get("jahresmitteltemperatur_c"),
                    hoehe_m=data.get("hoehe_m"),
                )

    return None


def get_climate_data_by_city(city_name: str) -> Optional[ClimateData]:
    """
    Gibt Klimadaten basierend auf Städtenamen zurück.

    Args:
        city_name: Name der Stadt (z.B. "Wien", "Graz", "Innsbruck")

    Returns:
        ClimateData-Objekt oder None wenn Stadt nicht gefunden

    Beispiel:
        >>> climate = get_climate_data_by_city("Wien")
        >>> print(climate.norm_aussentemperatur_c)
        -12
    """
    data = AUSTRIA_CLIMATE_DATABASE.get(city_name)
    if data is None:
        return None

    return ClimateData(
        klimaregion=data["klimaregion"],
        heizgradtage_kd=data["heizgradtage_kd"],
        heiztage=data["heiztage"],
        norm_aussentemperatur_c=data["norm_aussentemperatur_c"],
        kuehlgradtage_kd=data.get("kuehlgradtage_kd"),
        jahresmitteltemperatur_c=data.get("jahresmitteltemperatur_c"),
        hoehe_m=data.get("hoehe_m"),
    )


def get_available_cities() -> list[str]:
    """Gibt Liste aller verfügbaren Städte in der Datenbank zurück."""
    return list(AUSTRIA_CLIMATE_DATABASE.keys())


def calculate_heating_degree_days_from_epw(
    epw_path: Path,
    base_temp_c: float = 20.0
) -> float:
    """
    Berechnet Heizgradtage aus EPW-Wetterdatei.

    Args:
        epw_path: Pfad zur EPW-Datei
        base_temp_c: Heizgrenztemperatur [°C] (Standard: 20°C)

    Returns:
        Heizgradtage [Kd]

    Hinweis:
        Benötigt ladybug-core: pip install ladybug-core
    """
    try:
        from ladybug.epw import EPW
    except ImportError:
        raise ImportError(
            "ladybug-core ist nicht installiert. "
            "Installation: pip install ladybug-core"
        )

    # EPW laden
    epw = EPW(str(epw_path))

    # Stundenwerte der Außentemperatur
    hourly_temps = epw.dry_bulb_temperature.values

    # Heizgradtage = Σ max(0, T_base - T_outdoor) für alle Stunden / 24
    # (Division durch 24 weil Stundenwerte → Tageswerte)
    hdd_hourly = sum(max(0, base_temp_c - t) for t in hourly_temps)
    hdd_daily = hdd_hourly / 24.0

    return round(hdd_daily, 1)


def calculate_heating_days_from_epw(
    epw_path: Path,
    threshold_temp_c: float = 12.0
) -> int:
    """
    Berechnet Anzahl Heiztage aus EPW-Wetterdatei.

    Ein Heiztag ist ein Tag, an dem die Tagesmitteltemperatur < threshold_temp_c ist.

    Args:
        epw_path: Pfad zur EPW-Datei
        threshold_temp_c: Heizgrenztemperatur [°C] (Standard: 12°C nach ÖNORM)

    Returns:
        Anzahl Heiztage [-]
    """
    try:
        from ladybug.epw import EPW
    except ImportError:
        raise ImportError(
            "ladybug-core ist nicht installiert. "
            "Installation: pip install ladybug-core"
        )

    # EPW laden
    epw = EPW(str(epw_path))

    # Stundenwerte der Außentemperatur
    hourly_temps = epw.dry_bulb_temperature.values

    # Gruppiere in Tage (24h pro Tag)
    heating_days = 0
    for day_start in range(0, len(hourly_temps), 24):
        day_temps = hourly_temps[day_start:day_start + 24]
        if len(day_temps) == 24:  # Vollständiger Tag
            daily_mean = sum(day_temps) / 24.0
            if daily_mean < threshold_temp_c:
                heating_days += 1

    return heating_days


def get_design_outdoor_temperature_from_epw(
    epw_path: Path,
    percentile: float = 0.04
) -> float:
    """
    Ermittelt Norm-Außentemperatur aus EPW-Datei.

    Verwendet 4%-Perzentil (d.h. 96% der Stunden sind wärmer).

    Args:
        epw_path: Pfad zur EPW-Datei
        percentile: Perzentil (Standard: 0.04 = 4% kälteste Stunden)

    Returns:
        Norm-Außentemperatur [°C]
    """
    try:
        from ladybug.epw import EPW
    except ImportError:
        raise ImportError(
            "ladybug-core ist nicht installiert. "
            "Installation: pip install ladybug-core"
        )

    # EPW laden
    epw = EPW(str(epw_path))

    # Stundenwerte der Außentemperatur
    hourly_temps = sorted(epw.dry_bulb_temperature.values)

    # Perzentil berechnen
    index = int(len(hourly_temps) * percentile)
    design_temp = hourly_temps[index]

    return round(design_temp, 1)


def get_climate_data_from_epw(
    epw_path: Path,
    klimaregion: Optional[str] = None
) -> ClimateData:
    """
    Extrahiert alle Klimadaten aus EPW-Datei.

    Args:
        epw_path: Pfad zur EPW-Datei
        klimaregion: Klimaregion (optional, z.B. "Ost", "West")

    Returns:
        ClimateData-Objekt mit berechneten Werten

    Beispiel:
        >>> climate = get_climate_data_from_epw(Path("weather/AUT_Wien.epw"), "Ost")
        >>> print(f"HDD: {climate.heizgradtage_kd:.0f} Kd")
    """
    try:
        from ladybug.epw import EPW
    except ImportError:
        raise ImportError(
            "ladybug-core ist nicht installiert. "
            "Installation: pip install ladybug-core"
        )

    # EPW laden
    epw = EPW(str(epw_path))

    # Klimaregion aus EPW-Location falls nicht gegeben
    if klimaregion is None:
        klimaregion = epw.location.city or "Unbekannt"

    # Berechnungen
    hdd = calculate_heating_degree_days_from_epw(epw_path, base_temp_c=20.0)
    heating_days = calculate_heating_days_from_epw(epw_path, threshold_temp_c=12.0)
    design_temp = get_design_outdoor_temperature_from_epw(epw_path, percentile=0.04)

    # Jahresmitteltemperatur
    hourly_temps = epw.dry_bulb_temperature.values
    mean_temp = sum(hourly_temps) / len(hourly_temps)

    return ClimateData(
        klimaregion=klimaregion,
        heizgradtage_kd=hdd,
        heiztage=heating_days,
        norm_aussentemperatur_c=design_temp,
        jahresmitteltemperatur_c=round(mean_temp, 1),
        hoehe_m=int(epw.location.elevation) if epw.location.elevation else None,
    )


# ============ TESTING & BEISPIELE ============

if __name__ == "__main__":
    # Test PLZ-Lookup
    print("=== PLZ-Lookup Test ===")
    wien_climate = get_climate_data_by_plz(1010)
    if wien_climate:
        print(f"Wien (1010):")
        print(f"  Klimaregion: {wien_climate.klimaregion}")
        print(f"  HGT: {wien_climate.heizgradtage_kd} Kd")
        print(f"  Heiztage: {wien_climate.heiztage}")
        print(f"  Norm-AT: {wien_climate.norm_aussentemperatur_c}°C")

    # Test City-Lookup
    print("\n=== Stadt-Lookup Test ===")
    innsbruck_climate = get_climate_data_by_city("Innsbruck")
    if innsbruck_climate:
        print(f"Innsbruck:")
        print(f"  HGT: {innsbruck_climate.heizgradtage_kd} Kd")
        print(f"  Norm-AT: {innsbruck_climate.norm_aussentemperatur_c}°C")

    # Verfügbare Städte
    print(f"\n=== Verfügbare Städte ({len(get_available_cities())}) ===")
    for city in get_available_cities():
        print(f"  - {city}")
