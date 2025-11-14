"""KPI (Kennzahlen) Berechnung für Gebäudesimulationen."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys

from features.auswertung.sql_parser import EnergyPlusSQLParser, ErgebnisUebersicht
from features.auswertung.tabular_reports import (
    EndUseSummary,
    SiteSourceEnergy,
    HVACSizing,
    EnvelopePerformance
)

# Import OIB Konversionsfaktoren
try:
    from data.oib_konversionsfaktoren import berechne_peb, berechne_co2, get_konversionsfaktor_fuer_hvac
except ImportError:
    # Fallback wenn Pfad nicht funktioniert
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from data.oib_konversionsfaktoren import berechne_peb, berechne_co2, get_konversionsfaktor_fuer_hvac


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

    # Rohdaten (ohne Defaults müssen vor Feldern mit Defaults stehen)
    gesamtflaeche_m2: float
    ergebnisse: ErgebnisUebersicht

    # Austrian Energieausweis metrics (in kWh/m²a)
    hwb_kwh_m2a: float = 0.0  # Heizwärmebedarf (= heizkennzahl)
    wwwb_kwh_m2a: Optional[float] = None  # Warmwasserwärmebedarf (not available)
    eeb_kwh_m2a: float = 0.0  # Endenergiebedarf (= energiekennzahl)
    heb_kwh_m2a: Optional[float] = None  # Haushaltsenergiebedarf (not available)
    peb_kwh_m2a: Optional[float] = None  # Primärenergiebedarf (not available)
    co2_kg_m2a: Optional[float] = None  # CO2-Emissionen (not available)
    f_gee: Optional[float] = None  # Gesamtenergieeffizienz-Faktor (not available)

    # OIB RL6 specific metrics
    oib_effizienzklasse: str = "k.A."  # Nach OIB RL6 Tabelle 8
    kompaktheit_av: Optional[float] = None  # A/V [m⁻¹]
    char_laenge_lc: Optional[float] = None  # ℓc [m]
    mittlerer_u_wert: Optional[float] = None  # Ū [W/m²K]

    # Heat losses and gains (in kWh/a absolute values)
    transmissionswaermeverluste_kwh: float = 0.0  # QT
    lueftungswaermeverluste_kwh: float = 0.0  # QV
    solare_waermegewinne_kwh: float = 0.0  # Solar gains
    innere_waermegewinne_kwh: float = 0.0  # Internal gains


@dataclass
class ErweiterteKennzahlen:
    """Erweiterte Kennzahlen mit Tabular Reports."""

    # Standard-Kennzahlen
    basis_kennzahlen: GebaeudeKennzahlen

    # Tabular Reports (vorgefertigte EnergyPlus Summaries)
    end_uses: Optional[EndUseSummary] = None
    site_source_energy: Optional[SiteSourceEnergy] = None
    hvac_sizing: Optional[HVACSizing] = None
    envelope: Optional[EnvelopePerformance] = None


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

    # OIB RL6 Energieeffizienzklassen (Tabelle 8)
    # Klassengrenzen nach HWB, PEB, CO2, fGEE
    OIB_EFFIZIENZ_GRENZEN = {
        'A++': {'hwb': 10, 'peb': 60, 'co2': 8, 'f_gee': 0.55},
        'A+': {'hwb': 15, 'peb': 70, 'co2': 10, 'f_gee': 0.70},
        'A': {'hwb': 25, 'peb': 80, 'co2': 15, 'f_gee': 0.85},
        'B': {'hwb': 50, 'peb': 160, 'co2': 30, 'f_gee': 1.00},
        'C': {'hwb': 100, 'peb': 220, 'co2': 40, 'f_gee': 1.75},
        'D': {'hwb': 150, 'peb': 280, 'co2': 50, 'f_gee': 2.50},
        'E': {'hwb': 200, 'peb': 340, 'co2': 60, 'f_gee': 3.25},
        'F': {'hwb': 250, 'peb': 400, 'co2': 70, 'f_gee': 4.00},
        'G': {'hwb': float('inf'), 'peb': float('inf'), 'co2': float('inf'), 'f_gee': float('inf')},
    }

    def __init__(self, nettoflaeche_m2: float, building_model=None):
        """Initialisiere Rechner.

        Args:
            nettoflaeche_m2: Nettogrundfläche des Gebäudes in m²
            building_model: Optional - BuildingModel für OIB-Metadaten
        """
        self.nettoflaeche_m2 = nettoflaeche_m2
        self.building_model = building_model

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

        # OIB-Metadaten aus BuildingModel extrahieren (falls vorhanden)
        kompaktheit_av = None
        char_laenge_lc = None
        mittlerer_u_wert = None
        hvac_type = None

        if self.building_model:
            # Handle dict or object
            if isinstance(self.building_model, dict):
                geom_summary = self.building_model.get('geometry_summary', {})
                hvac_config = self.building_model.get('hvac_config', {})
            else:
                geom_summary = getattr(self.building_model, 'geometry_summary', {})
                hvac_config = getattr(self.building_model, 'hvac_config', {})

            kompaktheit_av = geom_summary.get('av_ratio') or geom_summary.get('oib_kompaktheit')
            char_laenge_lc = geom_summary.get('oib_char_laenge')
            mittlerer_u_wert = geom_summary.get('oib_mittlerer_u_wert')

            # HVAC-Typ für Primärenergie-Berechnung (Heizsystem)
            if hvac_config:
                # Verwende 'type' oder 'heating_system' (neue Struktur)
                hvac_type = hvac_config.get('heating_system') or hvac_config.get('type')

        # ========== OIB-KENNZAHLEN BERECHNUNG ==========

        # HEB (Heizenergiebedarf) = HWB + Verluste der gebäudetechnischen Systeme
        # Falls Verluste unbekannt: HEB ≈ HWB (konservative Annahme)
        heb_kwh_m2a = heizkennzahl

        # WWWB (Warmwasserwärmebedarf) = 0 (nicht simuliert)
        wwwb_kwh_m2a = None  # Oder 0, wenn explizit gefordert

        # EEB (Endenergiebedarf) = HEB + WWWB - Erträge
        # Falls WWWB = 0: EEB ≈ HEB ≈ HWB (+ Kühlung!)
        # WICHTIG: In der Simulation ist energiekennzahl = Heizung + Kühlung
        # Daher: EEB sollte Heizung + Kühlung sein
        eeb_kwh_m2a = energiekennzahl  # = Heizung + Kühlung

        # PEB (Primärenergiebedarf) = EEB × f_PE
        # Kann berechnet werden wenn HVAC-System bekannt
        peb_kwh_m2a = None
        co2_kg_m2a = None

        if hvac_type:
            try:
                peb_kwh_m2a = berechne_peb(eeb_kwh_m2a, hvac_type)
                co2_kg_m2a = berechne_co2(eeb_kwh_m2a, self.nettoflaeche_m2, hvac_type)
            except Exception:
                # Falls Konversionsfaktoren nicht verfügbar
                pass

        # Bestimme OIB-Effizienzklasse
        oib_effizienzklasse = self._bestimme_oib_effizienzklasse(
            hwb=heizkennzahl,
            peb=peb_kwh_m2a,
            co2=co2_kg_m2a,
            f_gee=None  # fGEE-Berechnung noch nicht implementiert
        )

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
            # Rohdaten (müssen vor optionalen Feldern stehen)
            gesamtflaeche_m2=self.nettoflaeche_m2,
            ergebnisse=ergebnisse,
            # Austrian Energieausweis metrics (specific values per m²a)
            hwb_kwh_m2a=heizkennzahl,  # Heizwärmebedarf
            wwwb_kwh_m2a=wwwb_kwh_m2a,  # Warmwasserwärmebedarf (nicht simuliert)
            eeb_kwh_m2a=eeb_kwh_m2a,  # Endenergiebedarf (Heizung + Kühlung)
            heb_kwh_m2a=heb_kwh_m2a,  # Heizenergiebedarf ≈ HWB (wenn Verluste unbekannt)
            peb_kwh_m2a=peb_kwh_m2a,  # Primärenergiebedarf (berechnet wenn HVAC bekannt)
            co2_kg_m2a=co2_kg_m2a,  # CO₂-Emissionen (berechnet wenn HVAC bekannt)
            f_gee=None,  # fGEE-Berechnung noch nicht implementiert
            # OIB RL6 specific
            oib_effizienzklasse=oib_effizienzklasse,
            kompaktheit_av=kompaktheit_av,
            char_laenge_lc=char_laenge_lc,
            mittlerer_u_wert=mittlerer_u_wert,
            # Heat losses and gains (absolute values in kWh/a)
            transmissionswaermeverluste_kwh=ergebnisse.transmissionswaermeverluste_kwh,
            lueftungswaermeverluste_kwh=ergebnisse.lueftungswaermeverluste_kwh,
            solare_waermegewinne_kwh=ergebnisse.solare_waermegewinne_kwh,
            innere_waermegewinne_kwh=ergebnisse.innere_waermegewinne_kwh,
        )

    def _bestimme_effizienzklasse(self, energiekennzahl: float) -> str:
        """Bestimme Effizienzklasse basierend auf Energiekennzahl.

        Args:
            energiekennzahl: Energiekennzahl in kWh/m²a

        Returns:
            Effizienzklasse (A+ bis H)
        """
        for klasse, grenzwert in self.EFFIZIENZ_GRENZEN.items():
            if energiekennzahl <= grenzwert:
                return klasse
        return 'H'

    def _bestimme_oib_effizienzklasse(
        self,
        hwb: float,
        peb: Optional[float] = None,
        co2: Optional[float] = None,
        f_gee: Optional[float] = None
    ) -> str:
        """Bestimme OIB RL6 Effizienzklasse nach Tabelle 8.

        Die Klasse wird primär nach HWB bestimmt. Falls verfügbar, werden
        auch PEB, CO2 und fGEE berücksichtigt (schlechteste Klasse gilt).

        Args:
            hwb: Heizwärmebedarf [kWh/m²a]
            peb: Primärenergiebedarf [kWh/m²a] (optional)
            co2: CO2-Emissionen [kg/m²a] (optional)
            f_gee: Gesamtenergieeffizienz-Faktor [-] (optional)

        Returns:
            OIB-Effizienzklasse (A++ bis G)
        """
        klassen = []

        # HWB-basierte Klassifizierung (immer verfügbar)
        for klasse, grenzen in self.OIB_EFFIZIENZ_GRENZEN.items():
            if hwb <= grenzen['hwb']:
                klassen.append(klasse)
                break

        # PEB-basierte Klassifizierung (falls verfügbar)
        if peb is not None:
            for klasse, grenzen in self.OIB_EFFIZIENZ_GRENZEN.items():
                if peb <= grenzen['peb']:
                    klassen.append(klasse)
                    break

        # CO2-basierte Klassifizierung (falls verfügbar)
        if co2 is not None:
            for klasse, grenzen in self.OIB_EFFIZIENZ_GRENZEN.items():
                if co2 <= grenzen['co2']:
                    klassen.append(klasse)
                    break

        # fGEE-basierte Klassifizierung (falls verfügbar)
        if f_gee is not None:
            for klasse, grenzen in self.OIB_EFFIZIENZ_GRENZEN.items():
                if f_gee <= grenzen['f_gee']:
                    klassen.append(klasse)
                    break

        # Schlechteste Klasse gilt (konservative Bewertung)
        if not klassen:
            return 'G'

        # Mapping für Sortierung
        klassen_order = ['A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
        return max(klassen, key=lambda k: klassen_order.index(k) if k in klassen_order else 999)

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

    def berechne_erweiterte_kennzahlen(
        self,
        sql_file: Path | str
    ) -> ErweiterteKennzahlen:
        """Berechne erweiterte Kennzahlen mit Tabular Reports.

        Diese Methode holt zusätzlich zu den Standard-Kennzahlen auch die
        vorgefertigten EnergyPlus Summary Reports (Tabular Data).

        Args:
            sql_file: Path zur SQL-Ergebnisdatei

        Returns:
            ErweiterteKennzahlen mit allen Standard- und Tabular-Daten
        """
        # Standard-Kennzahlen berechnen
        basis_kennzahlen = self.berechne_kennzahlen(sql_file=sql_file)

        # Tabular Summaries holen
        with EnergyPlusSQLParser(sql_file) as parser:
            try:
                tabular_summaries = parser.get_tabular_summaries()
                end_uses = tabular_summaries.get('end_uses')
                site_source_energy = tabular_summaries.get('site_source_energy')
                hvac_sizing = tabular_summaries.get('hvac_sizing')
                envelope = tabular_summaries.get('envelope')
            except Exception:
                # Falls Tabular Reports nicht verfügbar
                end_uses = None
                site_source_energy = None
                hvac_sizing = None
                envelope = None

        return ErweiterteKennzahlen(
            basis_kennzahlen=basis_kennzahlen,
            end_uses=end_uses,
            site_source_energy=site_source_energy,
            hvac_sizing=hvac_sizing,
            envelope=envelope
        )


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
