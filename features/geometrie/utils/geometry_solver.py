"""Geometrie-Solver: Berechnet L/W/H aus Energieausweis-Flächenangaben."""

import math
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

from features.geometrie.models.energieausweis_input import EnergieausweisInput


class SolutionMethod(str, Enum):
    """Methode zur Geometrie-Bestimmung."""

    EXACT = "exact"  # Vollständige Hüllflächen-Daten vorhanden
    HEURISTIC = "heuristic"  # Teilweise Daten, mit Annahmen
    FALLBACK = "fallback"  # Minimal-Daten, starke Annahmen
    OIB_DIRECT = "oib_direct"  # Vollständige OIB 12.2-Daten (V, A, A/V, ℓc)
    OIB_MANUAL = "oib_manual"  # OIB-Daten + Nutzer gibt L/W/H manuell ein


@dataclass
class GeometrySolution:
    """Lösung der Geometrie-Rekonstruktion."""

    length: float  # Länge in m (größere Dimension)
    width: float  # Breite in m (kleinere Dimension)
    height: float  # Gesamthöhe in m
    num_floors: int  # Anzahl Geschosse

    # Qualitätsindikatoren
    confidence: float  # 0.0 - 1.0: Wie sicher ist die Lösung?
    method: SolutionMethod  # Welche Methode wurde verwendet?
    warnings: List[str]  # Warnungen/Hinweise

    @property
    def floor_height(self) -> float:
        """Geschosshöhe."""
        return self.height / self.num_floors

    @property
    def floor_area(self) -> float:
        """Grundfläche pro Geschoss."""
        return self.length * self.width

    @property
    def total_floor_area(self) -> float:
        """Gesamt-Grundfläche."""
        return self.floor_area * self.num_floors

    @property
    def volume(self) -> float:
        """Bruttovolumen."""
        return self.length * self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        """Seitenverhältnis L/W."""
        return self.length / self.width

    @property
    def av_ratio(self) -> float:
        """A/V-Verhältnis (Kompaktheit)."""
        envelope_area = self._calculate_envelope_area()
        return envelope_area / self.volume

    def _calculate_envelope_area(self) -> float:
        """Berechnet Hüllfläche."""
        walls = 2 * (self.length + self.width) * self.height
        roof_floor = 2 * self.length * self.width
        return walls + roof_floor


class GeometrySolver:
    """Löst Gebäudegeometrie aus Energieausweis-Daten."""

    # Typische A/V-Verhältnisse (für Plausibilitätsprüfung)
    AV_MIN = 0.2  # Sehr kompakt (großes Gebäude)
    AV_MAX = 2.0  # Wenig kompakt (kleines/langes Gebäude)

    # Typische Geschosshöhen
    FLOOR_HEIGHT_MIN = 2.3
    FLOOR_HEIGHT_MAX = 4.5

    def solve(self, ea_data: EnergieausweisInput) -> GeometrySolution:
        """
        Hauptmethode: Berechnet Geometrie aus Energieausweis-Daten.

        Strategie:
        1. Falls vollständige Hüllflächen → Exakte Lösung
        2. Falls Teilinformationen → Heuristische Lösung
        3. Sonst → Fallback mit Standardannahmen
        """

        # Wähle beste verfügbare Methode
        if ea_data.has_complete_envelope_data:
            return self._solve_exact(ea_data)
        elif ea_data.wandflaeche_m2 is not None or ea_data.dachflaeche_m2 is not None:
            return self._solve_heuristic(ea_data)
        else:
            return self._solve_fallback(ea_data)

    def _solve_exact(self, ea_data: EnergieausweisInput) -> GeometrySolution:
        """
        Exakte Lösung bei vollständigen Hüllflächen-Daten.

        Gegeben:
        - A_Wand, A_Dach, A_Boden, A_Netto, n_floors

        Gleichungen:
        - A_Grundriss = A_Dach = A_Boden = L × W
        - A_Wand = 2 × (L + W) × H
        - AR = L / W (aus Hint)

        Lösung:
        - W = √(A_Grundriss / AR)
        - L = AR × W
        - H = A_Wand / (2 × (L + W))
        """
        warnings = []

        # Grundfläche
        A_grundriss = ea_data.dachflaeche_m2  # Annahme: Flachdach
        if abs(ea_data.dachflaeche_m2 - ea_data.bodenflaeche_m2) > 5.0:
            warnings.append(
                f"Dach ({ea_data.dachflaeche_m2:.1f}m²) und Boden "
                f"({ea_data.bodenflaeche_m2:.1f}m²) unterschiedlich - nutze Mittelwert"
            )
            A_grundriss = (ea_data.dachflaeche_m2 + ea_data.bodenflaeche_m2) / 2

        # Berechne L, W aus AR
        AR = ea_data.aspect_ratio_hint
        W = math.sqrt(A_grundriss / AR)
        L = AR * W

        # Berechne H aus Wandfläche
        perimeter = 2 * (L + W)
        H = ea_data.wandflaeche_m2 / perimeter

        # Plausibilitätschecks
        h_floor = H / ea_data.anzahl_geschosse
        if h_floor < self.FLOOR_HEIGHT_MIN:
            warnings.append(
                f"Geschosshöhe ({h_floor:.2f}m) zu niedrig - "
                f"Prüfe Wandfläche oder Geschosszahl"
            )
        elif h_floor > self.FLOOR_HEIGHT_MAX:
            warnings.append(
                f"Geschosshöhe ({h_floor:.2f}m) sehr hoch - "
                f"Ggf. Altbau oder ungenaue Daten"
            )

        # Erstelle Lösung
        solution = GeometrySolution(
            length=L,
            width=W,
            height=H,
            num_floors=ea_data.anzahl_geschosse,
            confidence=0.95,
            method=SolutionMethod.EXACT,
            warnings=warnings
        )

        # Validiere A/V-Verhältnis
        self._validate_compactness(solution, warnings)

        return solution

    def _solve_heuristic(self, ea_data: EnergieausweisInput) -> GeometrySolution:
        """
        Heuristische Lösung bei Teilinformationen.

        Strategie:
        1. Falls A_Dach gegeben → direkt L, W berechnen
        2. Falls nur A_Wand → schätze aus Nettofläche
        3. H aus Geschosshöhe-Annahme oder A_Wand
        """
        warnings = []

        # 1. Grundfläche bestimmen
        if ea_data.dachflaeche_m2 is not None:
            A_grundriss = ea_data.dachflaeche_m2
        elif ea_data.bodenflaeche_m2 is not None:
            A_grundriss = ea_data.bodenflaeche_m2
        else:
            # Schätze aus Bruttofläche (bereits inkl. Wände)
            A_grundriss = ea_data.bruttoflaeche_m2 / ea_data.anzahl_geschosse
            warnings.append(
                f"Grundfläche geschätzt aus Bruttofläche: {A_grundriss:.1f}m² pro Geschoss"
            )

        # 2. L, W aus AR
        AR = ea_data.aspect_ratio_hint
        W = math.sqrt(A_grundriss / AR)
        L = AR * W

        # 3. Höhe bestimmen
        if ea_data.wandflaeche_m2 is not None:
            # Berechne H aus Wandfläche
            perimeter = 2 * (L + W)
            H = ea_data.wandflaeche_m2 / perimeter
        else:
            # Nutze Geschosshöhe-Annahme
            H = ea_data.anzahl_geschosse * ea_data.geschosshoehe_m
            warnings.append(
                f"Höhe aus Geschosshöhe-Annahme: {ea_data.geschosshoehe_m:.1f}m"
            )

        solution = GeometrySolution(
            length=L,
            width=W,
            height=H,
            num_floors=ea_data.anzahl_geschosse,
            confidence=0.75,
            method=SolutionMethod.HEURISTIC,
            warnings=warnings
        )

        self._validate_compactness(solution, warnings)

        return solution

    def _solve_fallback(self, ea_data: EnergieausweisInput) -> GeometrySolution:
        """
        Fallback-Lösung bei minimalen Daten.

        Nur Nettofläche und Geschosszahl gegeben.
        Nutzt Standardannahmen für AR und Geschosshöhe.
        """
        warnings = [
            "Minimale Datenlage - starke Annahmen!",
            f"Aspect Ratio angenommen: {ea_data.aspect_ratio_hint:.1f}",
            f"Geschosshöhe angenommen: {ea_data.geschosshoehe_m:.1f}m"
        ]

        # Grundfläche aus Bruttofläche (bereits inkl. Wände)
        A_grundriss = ea_data.bruttoflaeche_m2 / ea_data.anzahl_geschosse

        # L, W aus AR
        AR = ea_data.aspect_ratio_hint
        W = math.sqrt(A_grundriss / AR)
        L = AR * W

        # H aus Geschosshöhe
        H = ea_data.anzahl_geschosse * ea_data.geschosshoehe_m

        solution = GeometrySolution(
            length=L,
            width=W,
            height=H,
            num_floors=ea_data.anzahl_geschosse,
            confidence=0.50,
            method=SolutionMethod.FALLBACK,
            warnings=warnings
        )

        self._validate_compactness(solution, warnings)

        return solution

    def _validate_compactness(
        self,
        solution: GeometrySolution,
        warnings: List[str]
    ) -> None:
        """Validiert A/V-Verhältnis und gibt Warnungen."""

        av = solution.av_ratio

        if av < self.AV_MIN:
            warnings.append(
                f"A/V-Verhältnis ({av:.2f}) sehr niedrig - "
                f"ungewöhnlich kompaktes Gebäude"
            )
        elif av > self.AV_MAX:
            warnings.append(
                f"A/V-Verhältnis ({av:.2f}) sehr hoch - "
                f"ungewöhnlich wenig kompakt (langes/schmales Gebäude)"
            )

        # Prüfe ob Aspect Ratio zu extrem
        if solution.aspect_ratio > 4.0:
            warnings.append(
                f"Aspect Ratio ({solution.aspect_ratio:.1f}) sehr hoch - "
                f"sehr langgestrecktes Gebäude"
            )
        elif solution.aspect_ratio < 0.5:
            warnings.append(
                f"Aspect Ratio ({solution.aspect_ratio:.1f}) sehr niedrig - "
                f"W > L (ungewöhnlich)"
            )


class DirectOIBSolver:
    """
    Berechnet Gebäudegeometrie aus vollständigen OIB 12.2-Angaben.

    Gegeben:
        - V (Brutto-Volumen)
        - A (Hüllfläche gesamt)
        - A/V (Kompaktheit)
        - ℓc (Charakteristische Länge)
        - n_floors (Anzahl Geschosse)
        - AR (Aspect Ratio Hint)

    Gesucht:
        - L, W, H

    Strategie:
        1. Berechne H aus n_floors × h_floor (Annahme: h_floor = 3.0m oder aus Input)
        2. Aus V = L × W × H → L × W = V / H
        3. Aus AR = L / W → L = AR × W
        4. Einsetzen: AR × W² = V / H → W = √(V / (H × AR))
        5. L = AR × W
        6. Validiere gegen gegebenes A/V

    Falls nicht konsistent: Iterative Anpassung von H.
    """

    # Typische Geschosshöhen
    FLOOR_HEIGHT_DEFAULT = 3.0  # m
    FLOOR_HEIGHT_MIN = 2.3
    FLOOR_HEIGHT_MAX = 4.5

    # Toleranzen für Konsistenz-Checks
    AV_TOLERANCE = 0.05  # 5% Abweichung erlaubt
    LC_TOLERANCE = 0.05  # 5% Abweichung erlaubt

    def solve(
        self,
        ea_data: EnergieausweisInput,
        manual_length: Optional[float] = None,
        manual_width: Optional[float] = None,
        manual_height: Optional[float] = None
    ) -> GeometrySolution:
        """
        Hauptmethode: Berechnet Geometrie aus vollständigen OIB-Daten.

        Args:
            ea_data: EnergieausweisInput mit vollständigen OIB 12.2-Daten
            manual_length: Optional manuell eingegebene Länge [m]
            manual_width: Optional manuell eingegebene Breite [m]
            manual_height: Optional manuell eingegebene Höhe [m]

        Returns:
            GeometrySolution

        Raises:
            ValueError: Wenn erforderliche OIB-Daten fehlen
        """

        # Prüfe ob OIB-Daten vollständig
        if not self._has_required_oib_data(ea_data):
            raise ValueError(
                "Unvollständige OIB-Daten. Erforderlich: "
                "brutto_volumen_m3, huellflaeche_gesamt_m2, anzahl_geschosse"
            )

        # Entscheide Modus: Automatisch vs. Manuell vs. Hybrid
        if manual_length and manual_width and manual_height:
            return self._solve_manual(ea_data, manual_length, manual_width, manual_height)
        elif manual_length and not manual_width and not manual_height:
            return self._solve_hybrid(ea_data, manual_length)
        else:
            return self._solve_automatic(ea_data)

    def _has_required_oib_data(self, ea_data: EnergieausweisInput) -> bool:
        """Prüft ob minimale OIB-Daten vorhanden sind."""
        return all([
            ea_data.brutto_volumen_m3 is not None,
            ea_data.huellflaeche_gesamt_m2 is not None,
            ea_data.anzahl_geschosse > 0
        ])

    def _solve_automatic(self, ea_data: EnergieausweisInput) -> GeometrySolution:
        """
        Automatische Geometrie-Berechnung aus OIB-Daten.

        Nutzt Aspect Ratio Hint und Geschosshöhe-Annahme.
        """
        warnings = []

        # Daten extrahieren
        V = ea_data.brutto_volumen_m3
        A = ea_data.huellflaeche_gesamt_m2
        n_floors = ea_data.anzahl_geschosse
        AR = ea_data.aspect_ratio_hint

        # 1. Geschosshöhe bestimmen
        h_floor = ea_data.geschosshoehe_m
        if not (self.FLOOR_HEIGHT_MIN <= h_floor <= self.FLOOR_HEIGHT_MAX):
            warnings.append(
                f"Geschosshöhe ({h_floor:.2f}m) außerhalb üblichem Bereich "
                f"({self.FLOOR_HEIGHT_MIN}-{self.FLOOR_HEIGHT_MAX}m)"
            )

        H = n_floors * h_floor

        # 2. Berechne L, W aus V und AR
        # V = L × W × H
        # AR = L / W → L = AR × W
        # → V = AR × W² × H
        # → W = √(V / (AR × H))

        floor_area = V / H
        W = math.sqrt(floor_area / AR)
        L = AR * W

        # 3. Validiere gegen gegebenes A/V
        A_calculated = self._calculate_envelope_area(L, W, H)
        AV_calculated = A_calculated / V

        if ea_data.kompaktheit is not None:
            AV_given = ea_data.kompaktheit
            diff_percent = abs(AV_calculated - AV_given) / AV_given * 100

            if diff_percent > self.AV_TOLERANCE * 100:
                warnings.append(
                    f"A/V-Inkonsistenz: Berechnet {AV_calculated:.3f} m⁻¹, "
                    f"gegeben {AV_given:.3f} m⁻¹ (Abweichung: {diff_percent:.1f}%)"
                )

                # Versuche iterative Anpassung von H
                H_adjusted = self._adjust_height_for_av(L, W, V, AV_given, n_floors)
                if H_adjusted is not None:
                    H = H_adjusted
                    h_floor = H / n_floors
                    warnings.append(
                        f"Höhe angepasst auf {H:.2f}m (Geschosshöhe: {h_floor:.2f}m) "
                        f"für bessere A/V-Konsistenz"
                    )

        # 4. Validiere gegen gegebene Hüllfläche
        A_calculated_final = self._calculate_envelope_area(L, W, H)
        diff_percent_A = abs(A_calculated_final - A) / A * 100

        if diff_percent_A > 5:
            warnings.append(
                f"Hüllfläche-Abweichung: Berechnet {A_calculated_final:.1f}m², "
                f"gegeben {A:.1f}m² (Abweichung: {diff_percent_A:.1f}%)"
            )

        # 5. Erstelle Lösung
        solution = GeometrySolution(
            length=L,
            width=W,
            height=H,
            num_floors=n_floors,
            confidence=0.85,  # Gut, aber nicht perfekt (Annahmen gemacht)
            method=SolutionMethod.OIB_DIRECT,
            warnings=warnings
        )

        return solution

    def _solve_manual(
        self,
        ea_data: EnergieausweisInput,
        length: float,
        width: float,
        height: float
    ) -> GeometrySolution:
        """
        Nutzer gibt L, W, H manuell ein.

        Validiert nur gegen OIB-Daten (V, A, A/V).
        """
        warnings = []

        # Validiere gegen OIB-Daten
        V_calculated = length * width * height
        V_given = ea_data.brutto_volumen_m3

        diff_percent_V = abs(V_calculated - V_given) / V_given * 100
        if diff_percent_V > 10:
            warnings.append(
                f"Volumen-Abweichung: L×W×H = {V_calculated:.1f}m³, "
                f"aber OIB-Angabe = {V_given:.1f}m³ (Abweichung: {diff_percent_V:.1f}%)"
            )

        # Prüfe Hüllfläche
        A_calculated = self._calculate_envelope_area(length, width, height)
        A_given = ea_data.huellflaeche_gesamt_m2

        diff_percent_A = abs(A_calculated - A_given) / A_given * 100
        if diff_percent_A > 10:
            warnings.append(
                f"Hüllfläche-Abweichung: Berechnet {A_calculated:.1f}m², "
                f"aber OIB-Angabe = {A_given:.1f}m² (Abweichung: {diff_percent_A:.1f}%)"
            )

        # Prüfe A/V
        AV_calculated = A_calculated / V_calculated
        if ea_data.kompaktheit is not None:
            AV_given = ea_data.kompaktheit
            diff_percent_AV = abs(AV_calculated - AV_given) / AV_given * 100

            if diff_percent_AV > 10:
                warnings.append(
                    f"A/V-Abweichung: Berechnet {AV_calculated:.3f} m⁻¹, "
                    f"aber OIB-Angabe = {AV_given:.3f} m⁻¹ (Abweichung: {diff_percent_AV:.1f}%)"
                )

        solution = GeometrySolution(
            length=length,
            width=width,
            height=height,
            num_floors=ea_data.anzahl_geschosse,
            confidence=1.0,  # User-Input hat höchste Priorität
            method=SolutionMethod.OIB_MANUAL,
            warnings=warnings
        )

        return solution

    def _solve_hybrid(
        self,
        ea_data: EnergieausweisInput,
        length: float
    ) -> GeometrySolution:
        """
        Hybrid: Nutzer gibt L an, System berechnet W und H.

        Gegeben:
            - L (manuell)
            - V, A (OIB)
            - n_floors

        Gesucht:
            - W, H

        Lösung:
            - H aus Geschosshöhe: H = n_floors × h_floor
            - V = L × W × H → W = V / (L × H)
        """
        warnings = []

        V = ea_data.brutto_volumen_m3
        n_floors = ea_data.anzahl_geschosse
        h_floor = ea_data.geschosshoehe_m

        H = n_floors * h_floor
        W = V / (length * H)

        # Validierung
        A_calculated = self._calculate_envelope_area(length, W, H)
        A_given = ea_data.huellflaeche_gesamt_m2

        diff_percent_A = abs(A_calculated - A_given) / A_given * 100
        if diff_percent_A > 10:
            warnings.append(
                f"Hüllfläche-Abweichung: Berechnet {A_calculated:.1f}m², "
                f"gegeben {A_given:.1f}m² (Abweichung: {diff_percent_A:.1f}%)"
            )

        solution = GeometrySolution(
            length=length,
            width=W,
            height=H,
            num_floors=n_floors,
            confidence=0.90,
            method=SolutionMethod.OIB_DIRECT,
            warnings=warnings
        )

        return solution

    def _calculate_envelope_area(self, L: float, W: float, H: float) -> float:
        """Berechnet Hüllfläche aus L, W, H."""
        walls = 2 * (L + W) * H
        roof_floor = 2 * L * W
        return walls + roof_floor

    def _adjust_height_for_av(
        self,
        L: float,
        W: float,
        V: float,
        target_av: float,
        n_floors: int,
        max_iterations: int = 10
    ) -> Optional[float]:
        """
        Iterativ H anpassen, um Ziel-A/V zu erreichen.

        Returns:
            Angepasste Höhe H oder None falls keine Lösung gefunden
        """
        # Binäre Suche
        H_min = self.FLOOR_HEIGHT_MIN * n_floors
        H_max = self.FLOOR_HEIGHT_MAX * n_floors

        for _ in range(max_iterations):
            H_mid = (H_min + H_max) / 2

            # Berechne A/V für diese Höhe
            # Problem: L, W ändern sich auch wenn H sich ändert (wegen V = const)
            # Vereinfachung: Nur H variieren, L, W fix
            A = self._calculate_envelope_area(L, W, H_mid)
            av = A / V

            if abs(av - target_av) / target_av < self.AV_TOLERANCE:
                return H_mid
            elif av < target_av:
                # Zu kompakt → H erhöhen
                H_min = H_mid
            else:
                # Zu wenig kompakt → H verringern
                H_max = H_mid

        return None  # Keine Lösung gefunden


# ============ UTILITY FUNCTIONS ============

def print_solution_summary(solution: GeometrySolution) -> None:
    """Druckt Zusammenfassung der Geometrie-Lösung."""

    print("\n" + "="*60)
    print("GEOMETRIE-LÖSUNG")
    print("="*60)
    print(f"Methode: {solution.method.value.upper()}")
    print(f"Konfidenz: {solution.confidence*100:.0f}%")
    print("\nAbmessungen:")
    print(f"  Länge:         {solution.length:.2f} m")
    print(f"  Breite:        {solution.width:.2f} m")
    print(f"  Höhe (gesamt): {solution.height:.2f} m")
    print(f"  Geschosse:     {solution.num_floors}")
    print(f"  Geschosshöhe:  {solution.floor_height:.2f} m")
    print("\nKennzahlen:")
    print(f"  Grundfläche:   {solution.floor_area:.1f} m²")
    print(f"  Gesamt-Fläche: {solution.total_floor_area:.1f} m²")
    print(f"  Volumen:       {solution.volume:.1f} m³")
    print(f"  Aspect Ratio:  {solution.aspect_ratio:.2f}")
    print(f"  A/V-Verhältnis:{solution.av_ratio:.2f}")

    if solution.warnings:
        print("\n⚠️  WARNUNGEN:")
        for warning in solution.warnings:
            print(f"  - {warning}")

    print("="*60 + "\n")
