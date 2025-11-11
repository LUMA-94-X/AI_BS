"""Datenmodelle für Energieausweis-basierte Geometrie-Generierung."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class GebaeudeTyp(str, Enum):
    """Gebäudetypologien nach TABULA."""

    EFH = "EFH"  # Einfamilienhaus
    MFH = "MFH"  # Mehrfamilienhaus
    NWG = "NWG"  # Nichtwohngebäude (Office, Retail, etc.)


class FensterData(BaseModel):
    """Fensterflächenangaben aus Energieausweis."""

    # Variante A: Exakte Flächen pro Orientierung (bevorzugt)
    nord_m2: Optional[float] = Field(default=None, ge=0, description="Fensterfläche Nord [m²]")
    ost_m2: Optional[float] = Field(default=None, ge=0, description="Fensterfläche Ost [m²]")
    sued_m2: Optional[float] = Field(default=None, ge=0, description="Fensterfläche Süd [m²]")
    west_m2: Optional[float] = Field(default=None, ge=0, description="Fensterfläche West [m²]")

    # Variante B: Gesamt-WWR (Fallback)
    window_wall_ratio: Optional[float] = Field(
        default=0.3,
        ge=0.05,
        le=0.95,
        description="Gesamter Fensterflächenanteil (Window-to-Wall Ratio)"
    )

    @property
    def has_exact_areas(self) -> bool:
        """Prüft ob exakte Flächenangaben vorhanden sind."""
        return any([
            self.nord_m2 is not None,
            self.ost_m2 is not None,
            self.sued_m2 is not None,
            self.west_m2 is not None
        ])

    @property
    def total_fenster_m2(self) -> float:
        """Berechnet Gesamt-Fensterfläche."""
        if self.has_exact_areas:
            return sum([
                self.nord_m2 or 0,
                self.ost_m2 or 0,
                self.sued_m2 or 0,
                self.west_m2 or 0
            ])
        return 0.0

    @field_validator('nord_m2', 'ost_m2', 'sued_m2', 'west_m2')
    @classmethod
    def check_positive(cls, v):
        """Validiere dass Fensterflächen nicht negativ sind."""
        if v is not None and v < 0:
            raise ValueError("Fensterfläche kann nicht negativ sein")
        return v


class EnergieausweisInput(BaseModel):
    """Vollständige Eingabedaten aus Energieausweis für 5-Zone-Modell."""

    # ============ PFLICHTFELDER ============
    nettoflaeche_m2: float = Field(
        ...,
        gt=10,
        lt=50000,
        description="Netto-Grundfläche / konditionierte Fläche [m²]"
    )

    u_wert_wand: float = Field(
        ...,
        gt=0.1,
        lt=3.0,
        description="U-Wert Außenwand [W/m²K]"
    )

    u_wert_dach: float = Field(
        ...,
        gt=0.1,
        lt=2.0,
        description="U-Wert Dach [W/m²K]"
    )

    u_wert_boden: float = Field(
        ...,
        gt=0.1,
        lt=2.0,
        description="U-Wert Bodenplatte [W/m²K]"
    )

    u_wert_fenster: float = Field(
        ...,
        gt=0.5,
        lt=6.0,
        description="U-Wert Fenster [W/m²K]"
    )

    # ============ GEOMETRIE (optional für Rückrechnung) ============
    wandflaeche_m2: Optional[float] = Field(
        default=None,
        gt=0,
        description="Außenwandfläche gesamt [m²]"
    )

    dachflaeche_m2: Optional[float] = Field(
        default=None,
        gt=0,
        description="Dachfläche [m²]"
    )

    bodenflaeche_m2: Optional[float] = Field(
        default=None,
        gt=0,
        description="Bodenfläche (Grundrissfläche) [m²]"
    )

    anzahl_geschosse: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Anzahl der Geschosse"
    )

    geschosshoehe_m: float = Field(
        default=3.0,
        ge=2.3,
        le=4.5,
        description="Geschosshöhe [m]"
    )

    # ============ FENSTER ============
    fenster: FensterData = Field(
        default_factory=FensterData,
        description="Fensterflächenangaben"
    )

    g_wert_fenster: float = Field(
        default=0.6,
        ge=0.1,
        le=0.9,
        description="g-Wert / SHGC (Solar Heat Gain Coefficient)"
    )

    # ============ LÜFTUNG ============
    luftwechselrate_h: float = Field(
        default=0.5,
        ge=0.0,
        le=3.0,
        description="Luftwechselrate [1/h]"
    )

    infiltration_ach50: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=15.0,
        description="Infiltration bei 50 Pa [1/h] (Blower Door Test)"
    )

    # ============ METADATA ============
    gebaeudetyp: GebaeudeTyp = Field(
        default=GebaeudeTyp.MFH,
        description="Gebäudetypologie"
    )

    baujahr: Optional[int] = Field(
        default=None,
        ge=1800,
        le=2030,
        description="Baujahr"
    )

    aspect_ratio_hint: float = Field(
        default=1.5,
        ge=1.0,
        le=3.0,
        description="Hinweis für Länge/Breite-Verhältnis (für Geometrie-Rekonstruktion)"
    )

    # ============ VALIDIERUNGEN ============

    @model_validator(mode='after')
    def validate_geometry_consistency(self):
        """Prüfe Konsistenz der Geometrie-Angaben."""

        # Falls Dach-/Bodenfläche gegeben, sollten sie ähnlich sein
        if self.dachflaeche_m2 is not None and self.bodenflaeche_m2 is not None:
            ratio = max(self.dachflaeche_m2, self.bodenflaeche_m2) / min(
                self.dachflaeche_m2, self.bodenflaeche_m2
            )
            if ratio > 1.5:
                raise ValueError(
                    f"Dachfläche ({self.dachflaeche_m2:.1f}m²) und Bodenfläche "
                    f"({self.bodenflaeche_m2:.1f}m²) weichen stark ab. "
                    f"Bei Flachdach sollten diese ähnlich sein."
                )

        # Nettofläche sollte zu Anzahl Geschosse passen
        grundflaeche_approx = self.nettoflaeche_m2 / self.anzahl_geschosse
        if grundflaeche_approx < 20:
            raise ValueError(
                f"Grundfläche pro Geschoss ({grundflaeche_approx:.1f}m²) sehr klein. "
                f"Prüfe Anzahl Geschosse ({self.anzahl_geschosse})."
            )

        # Falls Bodenfläche gegeben, Plausibilität prüfen
        if self.bodenflaeche_m2 is not None:
            grundflaeche_netto = self.nettoflaeche_m2 / self.anzahl_geschosse
            # Nettofläche ist ca. 80-90% der Bruttofläche
            if self.bodenflaeche_m2 < grundflaeche_netto * 0.7:
                raise ValueError(
                    f"Bodenfläche ({self.bodenflaeche_m2:.1f}m²) zu klein für "
                    f"Nettofläche ({grundflaeche_netto:.1f}m² pro Geschoss)"
                )

        return self

    @model_validator(mode='after')
    def validate_fenster_plausibility(self):
        """Prüfe Plausibilität der Fensterangaben."""

        if self.fenster.has_exact_areas:
            total_fenster = self.fenster.total_fenster_m2

            # Schätze Wandfläche falls nicht gegeben
            if self.wandflaeche_m2 is not None:
                wand = self.wandflaeche_m2
            else:
                # Grobe Schätzung: Umfang × Höhe
                grundflaeche = self.nettoflaeche_m2 / self.anzahl_geschosse
                umfang_approx = 4 * (grundflaeche ** 0.5)  # Für quadratisches Gebäude
                wand = umfang_approx * (self.anzahl_geschosse * self.geschosshoehe_m)

            # Fensteranteil sollte realistisch sein (5-60%)
            wwr_approx = total_fenster / wand
            if wwr_approx < 0.02:
                raise ValueError(
                    f"Fensterfläche ({total_fenster:.1f}m²) sehr klein "
                    f"für Wandfläche (~{wand:.1f}m²). WWR: {wwr_approx*100:.1f}%"
                )
            if wwr_approx > 0.95:
                raise ValueError(
                    f"Fensterfläche ({total_fenster:.1f}m²) zu groß "
                    f"für Wandfläche (~{wand:.1f}m²). WWR: {wwr_approx*100:.1f}%"
                )

        return self

    @property
    def has_complete_envelope_data(self) -> bool:
        """Prüft ob vollständige Hüllflächen-Daten vorhanden sind."""
        return all([
            self.wandflaeche_m2 is not None,
            self.dachflaeche_m2 is not None,
            self.bodenflaeche_m2 is not None
        ])

    @property
    def effective_infiltration(self) -> float:
        """Berechnet effektive Infiltrationsrate."""
        if self.infiltration_ach50 is not None:
            # Umrechnung: ACH50 → ACH (grob: ACH ≈ ACH50 / 20)
            return self.infiltration_ach50 / 20.0
        return self.luftwechselrate_h * 0.1  # Annahme: 10% der Lüftung ist Infiltration


# ============ BEISPIEL-INSTANZEN ============

def create_example_efh() -> EnergieausweisInput:
    """Beispiel: Typisches Einfamilienhaus Baujahr 2010."""
    return EnergieausweisInput(
        nettoflaeche_m2=150.0,
        wandflaeche_m2=240.0,
        dachflaeche_m2=80.0,
        bodenflaeche_m2=80.0,
        anzahl_geschosse=2,
        geschosshoehe_m=2.8,
        u_wert_wand=0.28,
        u_wert_dach=0.20,
        u_wert_boden=0.35,
        u_wert_fenster=1.3,
        g_wert_fenster=0.6,
        fenster=FensterData(
            nord_m2=8.0,
            ost_m2=12.0,
            sued_m2=20.0,
            west_m2=10.0
        ),
        luftwechselrate_h=0.5,
        gebaeudetyp=GebaeudeTyp.EFH,
        baujahr=2010,
        aspect_ratio_hint=1.3
    )


def create_example_mfh() -> EnergieausweisInput:
    """Beispiel: Mehrfamilienhaus Baujahr 1980, saniert."""
    return EnergieausweisInput(
        nettoflaeche_m2=800.0,
        wandflaeche_m2=950.0,
        dachflaeche_m2=280.0,
        bodenflaeche_m2=280.0,
        anzahl_geschosse=3,
        geschosshoehe_m=2.7,
        u_wert_wand=0.35,
        u_wert_dach=0.25,
        u_wert_boden=0.45,
        u_wert_fenster=1.5,
        g_wert_fenster=0.65,
        fenster=FensterData(
            nord_m2=40.0,
            ost_m2=55.0,
            sued_m2=80.0,
            west_m2=50.0
        ),
        luftwechselrate_h=0.6,
        infiltration_ach50=4.0,
        gebaeudetyp=GebaeudeTyp.MFH,
        baujahr=1980,
        aspect_ratio_hint=1.8
    )
