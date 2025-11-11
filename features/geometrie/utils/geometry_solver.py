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
            # Schätze aus Nettofläche (Annahme: 85% Nutzungsgrad)
            A_grundriss = (ea_data.nettoflaeche_m2 / ea_data.anzahl_geschosse) / 0.85
            warnings.append(
                f"Grundfläche geschätzt aus Nettofläche: {A_grundriss:.1f}m² "
                f"(Annahme: 85% Nutzungsgrad)"
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

        # Grundfläche aus Nettofläche (85% Nutzungsgrad)
        A_grundriss = (ea_data.nettoflaeche_m2 / ea_data.anzahl_geschosse) / 0.85

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
