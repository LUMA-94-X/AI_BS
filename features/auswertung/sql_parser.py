"""SQL Parser for EnergyPlus simulation results."""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from .tabular_reports import (
    TabularReportParser,
    EndUseSummary,
    SiteSourceEnergy,
    HVACSizing,
    EnvelopePerformance
)


@dataclass
class ErgebnisUebersicht:
    """Übersicht über Simulationsergebnisse."""

    gesamtenergiebedarf_kwh: float
    heizbedarf_kwh: float
    kuehlbedarf_kwh: float
    beleuchtung_kwh: float
    geraete_kwh: float

    spitzenlast_heizung_kw: float
    spitzenlast_kuehlung_kw: float

    mittlere_raumtemperatur_c: float
    min_raumtemperatur_c: float
    max_raumtemperatur_c: float

    # Austrian Energieausweis metrics
    transmissionswaermeverluste_kwh: float = 0.0
    lueftungswaermeverluste_kwh: float = 0.0
    solare_waermegewinne_kwh: float = 0.0
    innere_waermegewinne_kwh: float = 0.0


class EnergyPlusSQLParser:
    """Parser for EnergyPlus SQL output files."""

    def __init__(self, sql_file: Path | str):
        """Initialize parser with SQL file path.

        Args:
            sql_file: Path to eplusout.sql file
        """
        self.sql_file = Path(sql_file)
        if not self.sql_file.exists():
            raise FileNotFoundError(f"SQL-Datei nicht gefunden: {sql_file}")

        self.conn = sqlite3.connect(str(self.sql_file))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def get_ergebnis_uebersicht(self) -> ErgebnisUebersicht:
        """Hole Ergebnisübersicht aus der SQL-Datenbank.

        Returns:
            ErgebnisUebersicht mit allen wichtigen Kennzahlen
        """
        # Energiebedarf in kWh
        heizbedarf = self._get_annual_value("Zone Air System Sensible Heating Energy") / 3.6e6  # J to kWh
        kuehlbedarf = self._get_annual_value("Zone Air System Sensible Cooling Energy") / 3.6e6
        beleuchtung = self._get_annual_value("Zone Lights Electric Energy") / 3.6e6
        geraete = self._get_annual_value("Zone Electric Equipment Electric Energy") / 3.6e6

        gesamtenergie = heizbedarf + kuehlbedarf + beleuchtung + geraete

        # Spitzenlasten in kW
        # Note: Using "Zone Ideal Loads" variables which work with HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM
        spitzenlast_heizung = self._get_peak_value("Zone Ideal Loads Zone Total Heating Rate") / 1000  # W to kW
        spitzenlast_kuehlung = self._get_peak_value("Zone Ideal Loads Zone Total Cooling Rate") / 1000

        # Temperaturen
        temp_data = self._get_temperature_stats()

        # Austrian Energieausweis metrics
        # Transmission heat losses (QT) - negative values indicate heat loss
        transmissions_verluste = abs(self._get_annual_value("Surface Average Face Conduction Heat Transfer Energy")) / 3.6e6  # J to kWh

        # Ventilation heat losses (QV) - infiltration + ventilation
        infiltration_gain = self._get_annual_value("Zone Infiltration Sensible Heat Gain Energy") / 3.6e6
        ventilation_gain = self._get_annual_value("Zone Ventilation Sensible Heat Gain Energy") / 3.6e6
        # Negative gain = heat loss
        lueftungs_verluste = abs(min(0, infiltration_gain)) + abs(min(0, ventilation_gain))

        # Solar heat gains (from windows)
        solar_gewinne = max(0, self._get_annual_value("Zone Windows Total Heat Gain Energy") / 3.6e6)

        # Internal heat gains (lights + equipment + people)
        lights_heating = self._get_annual_value("Zone Lights Total Heating Energy") / 3.6e6
        equipment_heating = self._get_annual_value("Zone Electric Equipment Total Heating Energy") / 3.6e6
        people_heating = self._get_annual_value("Zone People Total Heating Energy") / 3.6e6
        innere_gewinne = lights_heating + equipment_heating + people_heating

        return ErgebnisUebersicht(
            gesamtenergiebedarf_kwh=gesamtenergie,
            heizbedarf_kwh=heizbedarf,
            kuehlbedarf_kwh=kuehlbedarf,
            beleuchtung_kwh=beleuchtung,
            geraete_kwh=geraete,
            spitzenlast_heizung_kw=spitzenlast_heizung,
            spitzenlast_kuehlung_kw=spitzenlast_kuehlung,
            mittlere_raumtemperatur_c=temp_data['mean'],
            min_raumtemperatur_c=temp_data['min'],
            max_raumtemperatur_c=temp_data['max'],
            transmissionswaermeverluste_kwh=transmissions_verluste,
            lueftungswaermeverluste_kwh=lueftungs_verluste,
            solare_waermegewinne_kwh=solar_gewinne,
            innere_waermegewinne_kwh=innere_gewinne,
        )

    def _get_annual_value(self, variable_name: str) -> float:
        """Get annual sum for a variable.

        Args:
            variable_name: Name of the output variable

        Returns:
            Sum of all values for the year
        """
        query = """
        SELECT SUM(rd.Value)
        FROM ReportData rd
        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
        WHERE rdd.Name = ?
        """

        cursor = self.conn.execute(query, (variable_name,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0.0

    def _get_peak_value(self, variable_name: str) -> float:
        """Get peak (maximum) value for a variable.

        Args:
            variable_name: Name of the output variable

        Returns:
            Maximum value
        """
        query = """
        SELECT MAX(rd.Value)
        FROM ReportData rd
        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
        WHERE rdd.Name = ?
        """

        cursor = self.conn.execute(query, (variable_name,))
        result = cursor.fetchone()[0]
        return result if result is not None else 0.0

    def _get_temperature_stats(self) -> Dict[str, float]:
        """Get temperature statistics.

        Returns:
            Dictionary with mean, min, max temperature
        """
        query = """
        SELECT AVG(rd.Value), MIN(rd.Value), MAX(rd.Value)
        FROM ReportData rd
        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
        WHERE rdd.Name = 'Zone Mean Air Temperature'
        """

        cursor = self.conn.execute(query)
        result = cursor.fetchone()

        if result and result[0] is not None:
            return {
                'mean': result[0],
                'min': result[1],
                'max': result[2],
            }
        return {'mean': 0.0, 'min': 0.0, 'max': 0.0}

    def get_timeseries_data(self, variable_name: str) -> pd.DataFrame:
        """Get time series data for a variable.

        Args:
            variable_name: Name of the output variable

        Returns:
            DataFrame with timestamps and values
        """
        query = """
        SELECT t.Month, t.Day, t.Hour, t.Minute, rd.Value
        FROM ReportData rd
        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
        JOIN Time t ON rd.TimeIndex = t.TimeIndex
        WHERE rdd.Name = ?
        ORDER BY t.Month, t.Day, t.Hour, t.Minute
        """

        df = pd.read_sql_query(query, self.conn, params=(variable_name,))

        if not df.empty:
            # Create datetime column (add year for proper datetime)
            df['Year'] = 2023  # Use a standard year for simulation data
            df['datetime'] = pd.to_datetime(
                df[['Year', 'Month', 'Day', 'Hour', 'Minute']].rename(
                    columns={'Year': 'year', 'Month': 'month', 'Day': 'day', 'Hour': 'hour', 'Minute': 'minute'}
                )
            )
            df = df[['datetime', 'Value']].rename(columns={'Value': variable_name})

        return df

    def get_monthly_summary(self) -> pd.DataFrame:
        """Get monthly energy summary.

        Returns:
            DataFrame with monthly breakdown
        """
        query = """
        SELECT
            t.Month,
            SUM(CASE WHEN rdd.Name = 'Zone Air System Sensible Heating Energy' THEN rd.Value ELSE 0 END) / 3600000.0 AS Heizung_kWh,
            SUM(CASE WHEN rdd.Name = 'Zone Air System Sensible Cooling Energy' THEN rd.Value ELSE 0 END) / 3600000.0 AS Kuehlung_kWh,
            SUM(CASE WHEN rdd.Name = 'Zone Lights Electric Energy' THEN rd.Value ELSE 0 END) / 3600000.0 AS Beleuchtung_kWh,
            SUM(CASE WHEN rdd.Name = 'Zone Electric Equipment Electric Energy' THEN rd.Value ELSE 0 END) / 3600000.0 AS Geraete_kWh
        FROM ReportData rd
        JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
        JOIN Time t ON rd.TimeIndex = t.TimeIndex
        GROUP BY t.Month
        ORDER BY t.Month
        """

        df = pd.read_sql_query(query, self.conn)

        # Add month names
        month_names = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        if not df.empty:
            df['Monat'] = df['Month'].apply(lambda x: month_names[int(x)-1] if 1 <= x <= 12 else str(x))

        return df

    def get_available_variables(self) -> List[str]:
        """Get list of all available output variables in the SQL file.

        Returns:
            List of variable names
        """
        query = "SELECT DISTINCT Name FROM ReportDataDictionary ORDER BY Name"
        cursor = self.conn.execute(query)
        return [row[0] for row in cursor.fetchall()]

    def get_tabular_summaries(self) -> Dict[str, any]:
        """Get pre-aggregated tabular summaries from EnergyPlus reports.

        Diese Methode nutzt vorgefertigte EnergyPlus Summary Reports,
        die bereits in der SQL-Datenbank aggregiert sind. Keine manuelle
        Summierung von Zeitreihen erforderlich!

        Returns:
            Dictionary mit allen verfügbaren Summaries:
            - 'end_uses': EndUseSummary (Verbrauchsaufteilung)
            - 'site_source_energy': SiteSourceEnergy (Primärenergie)
            - 'hvac_sizing': HVACSizing (Design-Lasten)
            - 'envelope': EnvelopePerformance (Gebäudehülle)
        """
        parser = TabularReportParser(self.sql_file)
        return parser.get_all_summaries()

    def get_end_use_breakdown(self) -> EndUseSummary:
        """Get detailed end-use breakdown from tabular reports.

        Returns:
            EndUseSummary mit Aufteilung nach Verwendungszweck
        """
        parser = TabularReportParser(self.sql_file)
        return parser.get_end_use_summary()

    def get_hvac_design_loads(self) -> HVACSizing:
        """Get HVAC design loads from tabular reports.

        Returns:
            HVACSizing mit Auslegungslasten
        """
        parser = TabularReportParser(self.sql_file)
        return parser.get_hvac_sizing()


def parse_ergebnisse(sql_file: Path | str) -> ErgebnisUebersicht:
    """Convenience function to quickly parse results.

    Args:
        sql_file: Path to SQL file

    Returns:
        ErgebnisUebersicht object
    """
    with EnergyPlusSQLParser(sql_file) as parser:
        return parser.get_ergebnis_uebersicht()
