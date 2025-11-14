"""Datenmodelle für Energieausweis-basierte Geometrie-Generierung."""

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class GebaeudeTyp(str, Enum):
    """Gebäudetypologien nach TABULA."""

    EFH = "EFH"  # Einfamilienhaus
    MFH = "MFH"  # Mehrfamilienhaus
    NWG = "NWG"  # Nichtwohngebäude (Office, Retail, etc.)


class Bauweise(str, Enum):
    """Bauweise des Gebäudes."""

    MASSIV = "Massiv"  # Massivbau (Ziegel, Beton)
    LEICHT = "Leicht"  # Leichtbau (Holz, Fertighaus)


class LueftungsArt(str, Enum):
    """Art der Lüftung nach OIB RL6."""

    FENSTER = "Fensterlüftung"
    ABLUFT = "Mechanische Abluft"
    ZUABLUFT_OHNE_WRG = "Zu-/Abluft ohne WRG"
    ZUABLUFT_MIT_WRG = "Zu-/Abluft mit WRG"


class KlimaQuelle(str, Enum):
    """Quelle für Klimadaten."""

    MANUELL = "Manuell"  # Nutzer gibt Werte direkt ein
    DATENBANK = "Datenbank"  # Aus österreichischer Klimadatenbank (PLZ)
    EPW = "EPW"  # Aus EPW-Wetterdatei berechnet


class GeometrieModus(str, Enum):
    """Modus für Geometrie-Erstellung."""

    AUTOMATISCH = "Automatisch"  # System berechnet L/W/H aus OIB-Daten
    MANUELL = "Manuell"  # Nutzer gibt L/W/H selbst ein
    HYBRID = "Hybrid"  # Nutzer gibt L an, System berechnet W/H


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
    bruttoflaeche_m2: float = Field(
        ...,
        gt=10,
        lt=50000,
        description="Brutto-Grundfläche (inkl. Wände) [m²]"
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

    # ============ OIB RL6 12.2 PFLICHTANGABEN ============

    # --- Flächen & Volumen ---
    bezugsflaeche_m2: Optional[float] = Field(
        default=None,
        gt=10,
        lt=50000,
        description="Bezugs-Grundfläche / Nettofläche (ohne Wände) [m²]"
    )

    # ============ ENERGIEAUSWEIS KENNWERTE (optional) ============
    brutto_volumen_m3: Optional[float] = Field(
        default=None,
        gt=30,
        lt=500000,
        description="Brutto-Volumen (inkl. Wände) [m³]"
    )

    kompaktheit: Optional[float] = Field(
        default=None,
        gt=0.1,
        lt=10.0,
        description="Kompaktheit A/V [m²/m³] - wird berechnet wenn nicht angegeben"
    )

    charakteristische_laenge_m: Optional[float] = Field(
        default=None,
        gt=0.5,
        lt=50.0,
        description="Charakteristische Länge lc = V/A [m] - wird berechnet wenn nicht angegeben"
    )

    mittlerer_u_wert: Optional[float] = Field(
        default=None,
        gt=0.1,
        lt=3.0,
        description="Mittlerer U-Wert (flächengewichtet) [W/m²K] - wird berechnet wenn nicht angegeben"
    )

    # --- Hüllfläche gesamt (wird berechnet oder direkt eingegeben) ---
    huellflaeche_gesamt_m2: Optional[float] = Field(
        default=None,
        gt=50,
        lt=100000,
        description="Gebäude-Hüllfläche gesamt [m²] (Wand + Dach + Boden)"
    )

    bauweise: Bauweise = Field(
        default=Bauweise.MASSIV,
        description="Bauweise des Gebäudes"
    )

    # ============ OIB RL6 12.2 KLIMADATEN ============

    # --- Klimaregion & Temperaturen ---
    klimaregion: Optional[str] = Field(
        default=None,
        description="Klimaregion nach ÖNORM B 8110-5 (z.B. 'Ost', 'West', 'Süd', 'Nord')"
    )

    heizgradtage_kd: Optional[float] = Field(
        default=None,
        gt=0,
        lt=10000,
        description="Heizgradtage [Kd] für 20°C Heizgrenze"
    )

    heiztage: Optional[int] = Field(
        default=None,
        gt=0,
        lt=366,
        description="Anzahl Heiztage [-]"
    )

    norm_aussentemperatur_c: Optional[float] = Field(
        default=None,
        gt=-30,
        lt=10,
        description="Norm-Außentemperatur für Heizlastberechnung [°C]"
    )

    klima_quelle: KlimaQuelle = Field(
        default=KlimaQuelle.MANUELL,
        description="Quelle für Klimadaten (Manuell/Datenbank/EPW)"
    )

    plz: Optional[int] = Field(
        default=None,
        gt=1000,
        lt=9999,
        description="Postleitzahl (für Datenbank-basierte Klimadaten)"
    )

    # ============ OIB RL6 12.2 TECHNISCHE SYSTEME ============

    # --- Lüftung ---
    art_der_lueftung: Optional[LueftungsArt] = Field(
        default=None,
        description="Art der Lüftung nach OIB RL6"
    )

    soll_innentemperatur_c: float = Field(
        default=20.0,
        ge=15,
        le=26,
        description="Soll-Innentemperatur Heizperiode [°C]"
    )

    # --- Optional ---
    co2_emissionen_kg_m2a: Optional[float] = Field(
        default=None,
        ge=0,
        description="CO₂-Emissionen [kg/m²a]"
    )

    # ============ GEOMETRIE-MODUS (für 2-Phasen-Eingabe) ============

    geometrie_modus: GeometrieModus = Field(
        default=GeometrieModus.AUTOMATISCH,
        description="Modus für Geometrie-Erstellung"
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

        # Bruttofläche sollte zu Anzahl Geschosse passen
        grundflaeche_approx = self.bruttoflaeche_m2 / self.anzahl_geschosse
        if grundflaeche_approx < 20:
            raise ValueError(
                f"Grundfläche pro Geschoss ({grundflaeche_approx:.1f}m²) sehr klein. "
                f"Prüfe Anzahl Geschosse ({self.anzahl_geschosse})."
            )

        # Falls Bodenfläche gegeben, Plausibilität prüfen
        if self.bodenflaeche_m2 is not None:
            grundflaeche_brutto = self.bruttoflaeche_m2 / self.anzahl_geschosse
            # Bodenfläche sollte ähnlich zur Bruttofläche pro Geschoss sein
            if self.bodenflaeche_m2 < grundflaeche_brutto * 0.6:
                raise ValueError(
                    f"Bodenfläche ({self.bodenflaeche_m2:.1f}m²) zu klein für "
                    f"Bruttofläche ({grundflaeche_brutto:.1f}m² pro Geschoss)"
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
                grundflaeche = self.bruttoflaeche_m2 / self.anzahl_geschosse
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

    @model_validator(mode='after')
    def validate_oib_consistency(self):
        """
        Prüfe Konsistenz der OIB 12.2-Angaben.

        Gibt Warnungen aus, aber wirft keine Fehler (User-Eingaben haben Priorität).
        """
        warnings = []

        # Check 1: Hüllfläche-Konsistenz (falls einzelne Flächen UND Gesamt gegeben)
        if (self.wandflaeche_m2 is not None and
            self.dachflaeche_m2 is not None and
            self.bodenflaeche_m2 is not None and
            self.huellflaeche_gesamt_m2 is not None):

            huellflaeche_berechnet = (
                self.wandflaeche_m2 +
                self.dachflaeche_m2 +
                self.bodenflaeche_m2
            )

            diff_prozent = abs(huellflaeche_berechnet - self.huellflaeche_gesamt_m2) / self.huellflaeche_gesamt_m2 * 100

            if diff_prozent > 5:  # Mehr als 5% Abweichung
                warnings.append(
                    f"Hüllfläche-Inkonsistenz: Summe (Wand+Dach+Boden) = {huellflaeche_berechnet:.1f}m², "
                    f"aber Gesamt-Hüllfläche = {self.huellflaeche_gesamt_m2:.1f}m² "
                    f"(Abweichung: {diff_prozent:.1f}%)"
                )

        # Check 2: A/V-Verhältnis (Kompaktheit)
        if (self.huellflaeche_gesamt_m2 is not None and
            self.brutto_volumen_m3 is not None and
            self.kompaktheit is not None):

            av_berechnet = self.huellflaeche_gesamt_m2 / self.brutto_volumen_m3
            diff_prozent = abs(av_berechnet - self.kompaktheit) / self.kompaktheit * 100

            if diff_prozent > 5:
                warnings.append(
                    f"Kompaktheit-Inkonsistenz: A/V berechnet = {av_berechnet:.3f} m⁻¹, "
                    f"aber angegeben = {self.kompaktheit:.3f} m⁻¹ "
                    f"(Abweichung: {diff_prozent:.1f}%)"
                )

        # Check 3: Charakteristische Länge
        if (self.brutto_volumen_m3 is not None and
            self.huellflaeche_gesamt_m2 is not None and
            self.charakteristische_laenge_m is not None):

            lc_berechnet = self.brutto_volumen_m3 / self.huellflaeche_gesamt_m2
            diff_prozent = abs(lc_berechnet - self.charakteristische_laenge_m) / self.charakteristische_laenge_m * 100

            if diff_prozent > 5:
                warnings.append(
                    f"Charakteristische Länge-Inkonsistenz: ℓc berechnet = {lc_berechnet:.2f}m, "
                    f"aber angegeben = {self.charakteristische_laenge_m:.2f}m "
                    f"(Abweichung: {diff_prozent:.1f}%)"
                )

        # Check 4: Bezugs- vs. Brutto-Grundfläche (typisch: BGF ≈ 1.05-1.15 × NF)
        if self.bezugsflaeche_m2 is not None:
            bgf_nf_ratio = self.bruttoflaeche_m2 / self.bezugsflaeche_m2

            if bgf_nf_ratio < 1.0:
                warnings.append(
                    f"Brutto-Grundfläche ({self.bruttoflaeche_m2:.1f}m²) kleiner als "
                    f"Bezugs-Grundfläche ({self.bezugsflaeche_m2:.1f}m²). "
                    f"Üblicherweise: BGF > NF wegen Wänden."
                )
            elif bgf_nf_ratio > 1.25:
                warnings.append(
                    f"Brutto-Grundfläche ({self.bruttoflaeche_m2:.1f}m²) sehr viel größer als "
                    f"Bezugs-Grundfläche ({self.bezugsflaeche_m2:.1f}m²). "
                    f"Faktor: {bgf_nf_ratio:.2f} (typisch: 1.05-1.15)"
                )

        # Warnungen als Attribut speichern (können in UI angezeigt werden)
        if warnings:
            # Speichere Warnungen als private Attribute (Pydantic erlaubt das)
            object.__setattr__(self, '_oib_warnings', warnings)

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
    def has_complete_oib_data(self) -> bool:
        """Prüft ob alle OIB 12.2-Pflichtangaben vorhanden sind."""
        required_fields = [
            self.bruttoflaeche_m2 is not None,
            self.bezugsflaeche_m2 is not None,
            self.brutto_volumen_m3 is not None,
            self.huellflaeche_gesamt_m2 is not None,
            self.kompaktheit is not None,
            self.charakteristische_laenge_m is not None,
            # U-Werte sind bereits Pflicht (...)
            # Klimadaten
            self.klimaregion is not None,
            self.heizgradtage_kd is not None,
            self.heiztage is not None,
            self.norm_aussentemperatur_c is not None,
            # Systeme
            self.art_der_lueftung is not None,
            # Bauweise ist bereits mit Default versehen
        ]
        return all(required_fields)

    @property
    def oib_warnings(self) -> list[str]:
        """Gibt Liste der OIB-Konsistenz-Warnungen zurück."""
        return getattr(self, '_oib_warnings', [])

    @property
    def effective_infiltration(self) -> float:
        """Berechnet effektive Infiltrationsrate."""
        if self.infiltration_ach50 is not None:
            # Umrechnung: ACH50 → ACH (grob: ACH ≈ ACH50 / 20)
            return self.infiltration_ach50 / 20.0
        return self.luftwechselrate_h * 0.1  # Annahme: 10% der Lüftung ist Infiltration

    def berechne_mittleren_u_wert(self) -> Optional[float]:
        """
        Berechnet flächengewichteten mittleren U-Wert.

        Formel: U_m = (A_wand * U_wand + A_dach * U_dach + A_boden * U_boden + A_fenster * U_fenster) / A_gesamt

        Returns:
            Mittlerer U-Wert [W/m²K] oder None wenn Flächenangaben fehlen
        """
        if not self.has_complete_envelope_data:
            return None

        # Fensterfläche
        if self.fenster.has_exact_areas:
            a_fenster = self.fenster.total_fenster_m2
        else:
            # Schätzung basierend auf WWR und Wandfläche
            a_fenster = self.wandflaeche_m2 * self.fenster.window_wall_ratio if self.wandflaeche_m2 else 0

        # Opake Wandfläche (ohne Fenster)
        a_wand_opak = self.wandflaeche_m2 - a_fenster if self.wandflaeche_m2 else 0

        # Gesamtfläche Hüllfläche
        a_gesamt = a_wand_opak + self.dachflaeche_m2 + self.bodenflaeche_m2 + a_fenster

        if a_gesamt == 0:
            return None

        # Flächengewichteter U-Wert
        u_mittel = (
            a_wand_opak * self.u_wert_wand +
            self.dachflaeche_m2 * self.u_wert_dach +
            self.bodenflaeche_m2 * self.u_wert_boden +
            a_fenster * self.u_wert_fenster
        ) / a_gesamt

        return round(u_mittel, 3)


# ============ BEISPIEL-INSTANZEN ============

def create_example_efh() -> EnergieausweisInput:
    """Beispiel: Typisches Einfamilienhaus Baujahr 2010."""
    return EnergieausweisInput(
        bruttoflaeche_m2=165.0,  # ca. 10% mehr als Nettofläche 150m²
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
        bauweise=Bauweise.MASSIV,
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
        bruttoflaeche_m2=880.0,  # ca. 10% mehr als Nettofläche 800m²
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
        bauweise=Bauweise.MASSIV,
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
