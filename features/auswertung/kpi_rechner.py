"""KPI (Kennzahlen) Berechnung für Gebäudesimulationen."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from features.auswertung.sql_parser import EnergyPlusSQLParser, ErgebnisUebersicht


@dataclass
class GebaeudeKennzahlen:
    """Gebäude-Kennzahlen (KPIs)."""

    # Spezifische Energiekennzahlen
    energiekennzahl_kwh_m2a: float  # Gesamtenergie pro m² und Jahr
    heizkennzahl_kwh_m2a: float     # Heizenergie pro m² und Jahr
    kuehlkennzahl_kwh_m2a: float    # Kühlenergie pro m² und Jahr

    # Spezifische Leistungen
    heizlast_w_m2: float            # Spezifische Heizlast
    kuhllast_w_m2: float            # Spezifische Kühllast

    # Komfort
    mittlere_temp_c: float
    thermische_behaglichkeit: str   # "Gut", "Akzeptabel", "Problematisch"

    # Bewertung
    effizienzklasse: str            # Nach Energieeinsparverordnung: A+, A, B, C, etc.
    bewertung: str                  # Textuelle Bewertung

    # Rohdaten
    gesamtflaeche_m2: float
    ergebnisse: ErgebnisUebersicht


class KennzahlenRechner:
    """Berechnet Gebäude-Kennzahlen aus Simulationsergebnissen."""

    # Grenzwerte für Effizienzklassen (kWh/m²a Gesamtenergie)
    EFFIZIENZ_GRENZEN = {
        'A+': 30,
        'A': 50,
        'B': 75,
        'C': 100,
        'D': 130,
        'E': 160,
        'F': 200,
        'G': 250,
        'H': float('inf'),
    }

    def __init__(self, nettoflaeche_m2: float):
        """Initialisiere Rechner.

        Args:
            nettoflaeche_m2: Nettogrundfläche des Gebäudes in m²
        """
        self.nettoflaeche_m2 = nettoflaeche_m2

    def berechne_kennzahlen(
        self,
        sql_file: Optional[Path | str] = None,
        ergebnisse: Optional[ErgebnisUebersicht] = None
    ) -> GebaeudeKennzahlen:
        """Berechne alle Kennzahlen.

        Args:
            sql_file: Path zur SQL-Ergebnisdatei (optional, wenn ergebnisse gegeben)
            ergebnisse: Bereits geparste Ergebnisse (optional, wenn sql_file gegeben)

        Returns:
            GebaeudeKennzahlen Objekt mit allen KPIs
        """
        # Hole Ergebnisse
        if ergebnisse is None:
            if sql_file is None:
                raise ValueError("Entweder sql_file oder ergebnisse muss angegeben werden")
            with EnergyPlusSQLParser(sql_file) as parser:
                ergebnisse = parser.get_ergebnis_uebersicht()

        # Berechne spezifische Kennzahlen (pro m²)
        energiekennzahl = ergebnisse.gesamtenergiebedarf_kwh / self.nettoflaeche_m2
        heizkennzahl = ergebnisse.heizbedarf_kwh / self.nettoflaeche_m2
        kuehlkennzahl = ergebnisse.kuehlbedarf_kwh / self.nettoflaeche_m2

        # Spezifische Lasten (W/m²)
        heizlast = (ergebnisse.spitzenlast_heizung_kw * 1000) / self.nettoflaeche_m2
        kuhllast = (ergebnisse.spitzenlast_kuehlung_kw * 1000) / self.nettoflaeche_m2

        # Bewerte thermische Behaglichkeit
        temp_min = ergebnisse.min_raumtemperatur_c
        temp_max = ergebnisse.max_raumtemperatur_c

        if 20 <= temp_min and temp_max <= 26:
            behaglichkeit = "Gut"
        elif 18 <= temp_min and temp_max <= 28:
            behaglichkeit = "Akzeptabel"
        else:
            behaglichkeit = "Problematisch"

        # Bestimme Effizienzklasse
        effizienzklasse = self._bestimme_effizienzklasse(energiekennzahl)

        # Erstelle Bewertung
        bewertung = self._erstelle_bewertung(energiekennzahl, effizienzklasse, behaglichkeit)

        return GebaeudeKennzahlen(
            energiekennzahl_kwh_m2a=energiekennzahl,
            heizkennzahl_kwh_m2a=heizkennzahl,
            kuehlkennzahl_kwh_m2a=kuehlkennzahl,
            heizlast_w_m2=heizlast,
            kuhllast_w_m2=kuhllast,
            mittlere_temp_c=ergebnisse.mittlere_raumtemperatur_c,
            thermische_behaglichkeit=behaglichkeit,
            effizienzklasse=effizienzklasse,
            bewertung=bewertung,
            gesamtflaeche_m2=self.nettoflaeche_m2,
            ergebnisse=ergebnisse,
        )

    def _bestimme_effizienzklasse(self, energiekennzahl: float) -> str:
        """Bestimme Effizienzklasse basierend auf Energiekennzahl.

        Args:
            energiekennzahl: Energiekennzahl in kWh/m²a

        Returns:
            Effizienzklasse (A+ bis H)
        """
        for klasse, grenzwert in self.EFFIZIENZ_GRENZEN.items():
            if energiekennzahl < grenzwert:
                return klasse
        return 'H'

    def _erstelle_bewertung(
        self,
        energiekennzahl: float,
        effizienzklasse: str,
        behaglichkeit: str
    ) -> str:
        """Erstelle textuelle Bewertung.

        Args:
            energiekennzahl: Energiekennzahl in kWh/m²a
            effizienzklasse: Effizienzklasse
            behaglichkeit: Thermische Behaglichkeit

        Returns:
            Textuelle Bewertung
        """
        bewertungen = []

        # Energieeffizienz
        if effizienzklasse in ['A+', 'A']:
            bewertungen.append("Sehr energieeffizientes Gebäude")
        elif effizienzklasse in ['B', 'C']:
            bewertungen.append("Gute Energieeffizienz")
        elif effizienzklasse in ['D', 'E']:
            bewertungen.append("Durchschnittliche Energieeffizienz")
        else:
            bewertungen.append("Verbesserungsbedarf bei der Energieeffizienz")

        # Behaglichkeit
        if behaglichkeit == "Gut":
            bewertungen.append("Optimaler thermischer Komfort")
        elif behaglichkeit == "Akzeptabel":
            bewertungen.append("Akzeptabler thermischer Komfort")
        else:
            bewertungen.append("Thermischer Komfort sollte verbessert werden")

        return ". ".join(bewertungen) + "."


def berechne_vergleich(
    kennzahlen_liste: list[GebaeudeKennzahlen]
) -> dict:
    """Vergleiche mehrere Gebäude/Varianten.

    Args:
        kennzahlen_liste: Liste von GebaeudeKennzahlen

    Returns:
        Dictionary mit Vergleichsdaten
    """
    if not kennzahlen_liste:
        return {}

    energiekennzahlen = [k.energiekennzahl_kwh_m2a for k in kennzahlen_liste]

    return {
        'anzahl_varianten': len(kennzahlen_liste),
        'beste_energiekennzahl': min(energiekennzahlen),
        'schlechteste_energiekennzahl': max(energiekennzahlen),
        'durchschnitt_energiekennzahl': sum(energiekennzahlen) / len(energiekennzahlen),
        'einsparung_prozent': ((max(energiekennzahlen) - min(energiekennzahlen)) / max(energiekennzahlen) * 100)
        if max(energiekennzahlen) > 0 else 0,
    }
