"""
Tabular Reports Parser

Extrahiert vorgefertigte EnergyPlus Summary-Reports aus der SQL-Datenbank.

Diese Reports sind bereits aggregiert und enthalten wertvolle Metriken ohne
dass Zeitreihen manuell summiert werden müssen.

Verfügbare Reports:
- AnnualBuildingUtilityPerformanceSummary (End Uses, Site/Source Energy)
- EnvelopeSummary (U-Werte, Fensterflächen)
- HVACSizingSummary (Design-Lasten, Auslegungstemperaturen)
- SensibleHeatGainSummary (Solare Gewinne, Innere Lasten)
- DemandEndUseComponentsSummary (Spitzenlasten)
- ClimaticDataSummary (Wetterdaten)
- und 19 weitere...

Author: AI-gestützte Entwicklung
Created: 2025-11-14
"""

import sqlite3
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import pandas as pd


@dataclass
class EndUseSummary:
    """End-Use Breakdown (Beleuchtung, Geräte, HVAC, etc.)"""
    heating_kwh: float = 0.0
    cooling_kwh: float = 0.0
    interior_lighting_kwh: float = 0.0
    interior_equipment_kwh: float = 0.0
    fans_kwh: float = 0.0
    pumps_kwh: float = 0.0
    total_kwh: float = 0.0

    # Aufgeschlüsselt nach Energieträger
    electricity_kwh: float = 0.0
    natural_gas_kwh: float = 0.0

    @property
    def other_kwh(self) -> float:
        """Sonstige Verbräuche"""
        return self.total_kwh - (
            self.heating_kwh +
            self.cooling_kwh +
            self.interior_lighting_kwh +
            self.interior_equipment_kwh
        )


@dataclass
class SiteSourceEnergy:
    """Site und Source Energy (Primärenergie)"""
    total_site_energy_gj: float = 0.0
    total_source_energy_gj: float = 0.0
    site_energy_per_m2_mj: float = 0.0
    source_energy_per_m2_mj: float = 0.0

    @property
    def total_site_energy_kwh(self) -> float:
        """Site Energy in kWh"""
        return self.total_site_energy_gj * 277.778

    @property
    def total_source_energy_kwh(self) -> float:
        """Source Energy in kWh"""
        return self.total_source_energy_gj * 277.778

    @property
    def site_energy_per_m2_kwh(self) -> float:
        """Site Energy pro m² in kWh/m²"""
        return self.site_energy_per_m2_mj / 3.6


@dataclass
class HVACSizing:
    """HVAC Auslegungsgrößen"""
    heating_design_load_w: float = 0.0
    cooling_design_load_w: float = 0.0
    heating_design_load_per_area_w_m2: float = 0.0
    cooling_design_load_per_area_w_m2: float = 0.0
    heating_design_day: str = ""
    cooling_design_day: str = ""

    @property
    def heating_design_load_kw(self) -> float:
        """Heizlast in kW"""
        return self.heating_design_load_w / 1000.0

    @property
    def cooling_design_load_kw(self) -> float:
        """Kühllast in kW"""
        return self.cooling_design_load_w / 1000.0


@dataclass
class EnvelopePerformance:
    """Gebäudehülle Performance (aus Simulation)"""
    gross_wall_area_m2: float = 0.0
    gross_window_area_m2: float = 0.0
    gross_roof_area_m2: float = 0.0
    window_wall_ratio: float = 0.0

    # U-Werte (falls verfügbar)
    window_u_value: Optional[float] = None
    wall_u_value: Optional[float] = None
    roof_u_value: Optional[float] = None


class TabularReportParser:
    """
    Parser für EnergyPlus Tabular Reports.

    Extrahiert vorgefertigte Summary-Reports aus der SQL-Datenbank
    ohne aufwendiges Parsing von Zeitreihen.

    Usage:
        parser = TabularReportParser(sql_file)
        end_uses = parser.get_end_use_summary()
        site_energy = parser.get_site_source_energy()
    """

    def __init__(self, sql_file: Path):
        """
        Initialize parser.

        Args:
            sql_file: Path to eplusout.sql
        """
        self.sql_file = Path(sql_file)
        if not self.sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file}")

    def _get_tabular_data(self, report_name: str) -> pd.DataFrame:
        """
        Holt alle Daten für einen Report.

        Args:
            report_name: Name des Reports (z.B. 'AnnualBuildingUtilityPerformanceSummary')

        Returns:
            DataFrame mit Spalten: TableName, RowName, ColumnName, Value, Units
        """
        conn = sqlite3.connect(self.sql_file)

        query = """
        SELECT
            tn.Value AS TableName,
            rn.Value AS RowName,
            cn.Value AS ColumnName,
            td.Value AS Value,
            u.Value AS Units
        FROM TabularData td
        LEFT JOIN Strings rs ON td.ReportNameIndex = rs.StringIndex
        LEFT JOIN Strings tn ON td.TableNameIndex = tn.StringIndex
        LEFT JOIN Strings rn ON td.RowNameIndex = rn.StringIndex
        LEFT JOIN Strings cn ON td.ColumnNameIndex = cn.StringIndex
        LEFT JOIN Strings u ON td.UnitsIndex = u.StringIndex
        WHERE rs.Value = ?
        """

        df = pd.read_sql_query(query, conn, params=(report_name,))
        conn.close()

        return df

    def get_available_reports(self) -> List[str]:
        """
        Liste aller verfügbaren Reports.

        Returns:
            Liste von Report-Namen
        """
        conn = sqlite3.connect(self.sql_file)

        query = """
        SELECT DISTINCT rs.Value AS ReportName
        FROM TabularData td
        LEFT JOIN Strings rs ON td.ReportNameIndex = rs.StringIndex
        ORDER BY rs.Value
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df['ReportName'].tolist()

    def get_end_use_summary(self) -> EndUseSummary:
        """
        End-Use Breakdown (Beleuchtung, Geräte, HVAC).

        Extrahiert aus 'AnnualBuildingUtilityPerformanceSummary' → 'End Uses'.

        Returns:
            EndUseSummary mit allen Verbräuchen
        """
        df = self._get_tabular_data('AnnualBuildingUtilityPerformanceSummary')

        # Filtern auf End Uses Table
        end_uses = df[df['TableName'] == 'End Uses'].copy()

        if end_uses.empty:
            return EndUseSummary()

        # GJ → kWh Konversion
        GJ_TO_KWH = 277.778

        # Helper: Wert extrahieren
        def get_value(row_name: str, col_name: str = 'Electricity') -> float:
            row = end_uses[
                (end_uses['RowName'] == row_name) &
                (end_uses['ColumnName'] == col_name)
            ]
            if row.empty:
                return 0.0
            try:
                return float(row.iloc[0]['Value']) * GJ_TO_KWH
            except (ValueError, TypeError):
                return 0.0

        # Extrahieren
        summary = EndUseSummary(
            heating_kwh=get_value('Heating'),
            cooling_kwh=get_value('Cooling'),
            interior_lighting_kwh=get_value('Interior Lighting'),
            interior_equipment_kwh=get_value('Interior Equipment'),
            fans_kwh=get_value('Fans'),
            pumps_kwh=get_value('Pumps'),

            # Totals
            electricity_kwh=get_value('Total End Uses', 'Electricity'),
            natural_gas_kwh=get_value('Total End Uses', 'Natural Gas'),
        )

        summary.total_kwh = summary.electricity_kwh + summary.natural_gas_kwh

        return summary

    def get_site_source_energy(self) -> SiteSourceEnergy:
        """
        Site und Source Energy (Primärenergie).

        Extrahiert aus 'AnnualBuildingUtilityPerformanceSummary' → 'Site and Source Energy'.

        Returns:
            SiteSourceEnergy mit Primärenergie-Kennzahlen
        """
        df = self._get_tabular_data('AnnualBuildingUtilityPerformanceSummary')

        # Filtern auf Site and Source Energy Table
        energy = df[df['TableName'] == 'Site and Source Energy'].copy()

        if energy.empty:
            return SiteSourceEnergy()

        # Helper
        def get_value(row_name: str, col_name: str = 'Total Energy') -> float:
            row = energy[
                (energy['RowName'] == row_name) &
                (energy['ColumnName'] == col_name)
            ]
            if row.empty:
                return 0.0
            try:
                return float(row.iloc[0]['Value'])
            except (ValueError, TypeError):
                return 0.0

        return SiteSourceEnergy(
            total_site_energy_gj=get_value('Total Site Energy', 'Total Energy'),
            total_source_energy_gj=get_value('Total Source Energy', 'Total Energy'),
            site_energy_per_m2_mj=get_value('Total Site Energy', 'Energy Per Total Building Area'),
            source_energy_per_m2_mj=get_value('Total Source Energy', 'Energy Per Total Building Area')
        )

    def get_hvac_sizing(self) -> HVACSizing:
        """
        HVAC Auslegungsgrößen (Design-Lasten).

        Extrahiert aus 'HVACSizingSummary'.

        Returns:
            HVACSizing mit Design-Lasten
        """
        df = self._get_tabular_data('HVACSizingSummary')

        if df.empty:
            return HVACSizing()

        # Helper
        def get_value(table_name: str, property_name: str) -> float:
            row = df[
                (df['TableName'] == table_name) &
                (df['ColumnName'] == property_name)
            ]
            if row.empty:
                return 0.0
            try:
                # Summiere über alle Zonen
                return float(row['Value'].astype(float).sum())
            except (ValueError, TypeError):
                return 0.0

        def get_string(table_name: str, property_name: str) -> str:
            row = df[
                (df['TableName'] == table_name) &
                (df['ColumnName'] == property_name)
            ]
            if row.empty:
                return ""
            return str(row.iloc[0]['Value'])

        return HVACSizing(
            heating_design_load_w=get_value('Zone Sensible Heating', 'Calculated Design Load'),
            cooling_design_load_w=get_value('Zone Sensible Cooling', 'Calculated Design Load'),
            heating_design_load_per_area_w_m2=get_value('Zone Sensible Heating', 'Calculated Design Load per Area'),
            cooling_design_load_per_area_w_m2=get_value('Zone Sensible Cooling', 'Calculated Design Load per Area'),
            heating_design_day=get_string('Zone Sensible Heating', 'Design Day Name'),
            cooling_design_day=get_string('Zone Sensible Cooling', 'Design Day Name')
        )

    def get_envelope_performance(self) -> EnvelopePerformance:
        """
        Gebäudehülle Performance.

        Extrahiert aus 'EnvelopeSummary'.

        Returns:
            EnvelopePerformance mit Hüllflächen
        """
        df = self._get_tabular_data('EnvelopeSummary')

        if df.empty:
            return EnvelopePerformance()

        # Helper
        def get_value(table_name: str, row_name: str, col_name: str) -> float:
            row = df[
                (df['TableName'] == table_name) &
                (df['RowName'] == row_name) &
                (df['ColumnName'] == col_name)
            ]
            if row.empty:
                return 0.0
            try:
                return float(row.iloc[0]['Value'])
            except (ValueError, TypeError):
                return 0.0

        # Flächen summieren
        wall_area = get_value('Opaque Exterior', 'Total', 'Gross Area')
        window_area = get_value('Fenestration', 'Total', 'Area of Multiplied Openings')
        roof_area = get_value('Opaque Exterior', 'Total', 'Gross Area')  # TODO: Dach separat

        wwr = 0.0
        if wall_area > 0:
            wwr = window_area / (wall_area + window_area)

        return EnvelopePerformance(
            gross_wall_area_m2=wall_area,
            gross_window_area_m2=window_area,
            gross_roof_area_m2=roof_area,
            window_wall_ratio=wwr
        )

    def get_all_summaries(self) -> Dict[str, any]:
        """
        Holt ALLE verfügbaren Summaries.

        Returns:
            Dict mit allen Summaries
        """
        return {
            'end_uses': self.get_end_use_summary(),
            'site_source_energy': self.get_site_source_energy(),
            'hvac_sizing': self.get_hvac_sizing(),
            'envelope': self.get_envelope_performance()
        }

    def get_raw_dataframe(self, report_name: str) -> pd.DataFrame:
        """
        Holt rohe Daten als DataFrame für eigene Analysen.

        Args:
            report_name: Name des Reports

        Returns:
            DataFrame mit allen Daten des Reports
        """
        return self._get_tabular_data(report_name)
