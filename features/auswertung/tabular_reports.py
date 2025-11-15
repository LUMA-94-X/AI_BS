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


@dataclass
class ZoneData:
    """Daten für eine einzelne Zone (aggregiert über alle Geschosse)"""
    zone_name: str = ""
    orientation: str = ""  # North, East, South, West, Core
    floor_area_m2: float = 0.0  # Zonenfläche [m²]

    # Temperaturen
    avg_temperature_c: float = 0.0
    min_temperature_c: float = 0.0
    max_temperature_c: float = 0.0

    # Lasten (kWh)
    heating_kwh: float = 0.0
    cooling_kwh: float = 0.0

    # Gewinne (kWh)
    solar_gains_kwh: float = 0.0
    internal_gains_kwh: float = 0.0  # Lights + Equipment + People
    lights_kwh: float = 0.0
    equipment_kwh: float = 0.0
    people_kwh: float = 0.0

    # Pro-m² Werte (computed properties)
    @property
    def heating_kwh_m2(self) -> float:
        """Heizenergie pro m² [kWh/m²a]"""
        return self.heating_kwh / self.floor_area_m2 if self.floor_area_m2 > 0 else 0.0

    @property
    def cooling_kwh_m2(self) -> float:
        """Kühlenergie pro m² [kWh/m²a]"""
        return self.cooling_kwh / self.floor_area_m2 if self.floor_area_m2 > 0 else 0.0

    @property
    def solar_gains_kwh_m2(self) -> float:
        """Solare Gewinne pro m² [kWh/m²a]"""
        return self.solar_gains_kwh / self.floor_area_m2 if self.floor_area_m2 > 0 else 0.0

    @property
    def internal_gains_kwh_m2(self) -> float:
        """Innere Gewinne pro m² [kWh/m²a]"""
        return self.internal_gains_kwh / self.floor_area_m2 if self.floor_area_m2 > 0 else 0.0


@dataclass
class ZonalComparison:
    """Vergleich aller Zonen"""
    zones: Dict[str, ZoneData]  # zone_name -> ZoneData

    @property
    def north_zone(self) -> Optional[ZoneData]:
        return next((z for z in self.zones.values() if z.orientation == "North"), None)

    @property
    def east_zone(self) -> Optional[ZoneData]:
        return next((z for z in self.zones.values() if z.orientation == "East"), None)

    @property
    def south_zone(self) -> Optional[ZoneData]:
        return next((z for z in self.zones.values() if z.orientation == "South"), None)

    @property
    def west_zone(self) -> Optional[ZoneData]:
        return next((z for z in self.zones.values() if z.orientation == "West"), None)

    @property
    def core_zone(self) -> Optional[ZoneData]:
        return next((z for z in self.zones.values() if z.orientation == "Core"), None)


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

    def _get_design_loads_from_timeseries(self) -> Optional[HVACSizing]:
        """
        Fallback: Extrahiert Design Loads aus Zeitreihen-Daten.

        Wird verwendet, wenn Tabular Reports leer sind (z.B. bei IdealLoadsAirSystem).

        Returns:
            HVACSizing mit Max-Werten aus Zeitreihen, oder None bei Fehler
        """
        conn = sqlite3.connect(self.sql_file)
        try:
            query = """
            SELECT
                d.VariableName,
                MAX(v.VariableValue) as MaxValue
            FROM ReportVariableData v
            JOIN ReportVariableDataDictionary d
                ON v.ReportVariableDataDictionaryIndex = d.ReportVariableDataDictionaryIndex
            WHERE d.VariableName LIKE '%Ideal Loads Zone Total Heating Rate%'
               OR d.VariableName LIKE '%Ideal Loads Zone Total Cooling Rate%'
            GROUP BY d.VariableName
            """

            df = pd.read_sql_query(query, conn)

            if df.empty:
                return None

            heating_w = 0.0
            cooling_w = 0.0

            for _, row in df.iterrows():
                if 'Heating' in row['VariableName']:
                    heating_w += row['MaxValue']
                elif 'Cooling' in row['VariableName']:
                    cooling_w += row['MaxValue']

            # Design Days aus SizingPeriod:DesignDay TabularData
            query_dd = """
            SELECT RowName, Value
            FROM TabularDataWithStrings
            WHERE TableName = 'SizingPeriod:DesignDay'
            LIMIT 10
            """
            df_dd = pd.read_sql_query(query_dd, conn)

            # Parse Design Day Namen (falls verfügbar)
            heating_dd = ""
            cooling_dd = ""
            if not df_dd.empty:
                # Erste zwei Zeilen sind typischerweise Heating und Cooling Design Days
                days = df_dd['Value'].dropna().unique()
                if len(days) >= 1:
                    heating_dd = str(days[0])
                if len(days) >= 2:
                    cooling_dd = str(days[1])

            return HVACSizing(
                heating_design_load_w=heating_w,
                cooling_design_load_w=cooling_w,
                heating_design_load_per_area_w_m2=0.0,  # Nicht verfügbar aus Zeitreihen
                cooling_design_load_per_area_w_m2=0.0,
                heating_design_day=heating_dd,
                cooling_design_day=cooling_dd
            )
        except Exception as e:
            print(f"Warning: Could not extract design loads from timeseries: {e}")
            return None
        finally:
            conn.close()

    def get_hvac_sizing(self) -> HVACSizing:
        """
        HVAC Auslegungsgrößen (Design-Lasten).

        Extrahiert aus 'HVACSizingSummary'. Falls leer (z.B. bei IdealLoadsAirSystem),
        wird auf Zeitreihen-Daten zurückgegriffen.

        Returns:
            HVACSizing mit Design-Lasten
        """
        df = self._get_tabular_data('HVACSizingSummary')

        if df.empty:
            # Fallback auf Zeitreihen
            fallback = self._get_design_loads_from_timeseries()
            return fallback if fallback else HVACSizing()

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

        sizing = HVACSizing(
            heating_design_load_w=get_value('Zone Sensible Heating', 'Calculated Design Load'),
            cooling_design_load_w=get_value('Zone Sensible Cooling', 'Calculated Design Load'),
            heating_design_load_per_area_w_m2=get_value('Zone Sensible Heating', 'Calculated Design Load per Area'),
            cooling_design_load_per_area_w_m2=get_value('Zone Sensible Cooling', 'Calculated Design Load per Area'),
            heating_design_day=get_string('Zone Sensible Heating', 'Design Day Name'),
            cooling_design_day=get_string('Zone Sensible Cooling', 'Design Day Name')
        )

        # Wenn Tabular Reports existieren aber leer sind (alle Werte = 0),
        # verwende Fallback
        if (sizing.heating_design_load_w == 0.0 and
            sizing.cooling_design_load_w == 0.0):
            fallback = self._get_design_loads_from_timeseries()
            if fallback:
                return fallback

        return sizing

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

    def get_zonal_comparison(self) -> ZonalComparison:
        """
        Extrahiert zonale Daten für Vergleich (Nord/Ost/Süd/West/Kern).

        ERWEITERT (2025-11-15):
        - Multi-Floor Support: Aggregiert über alle Geschosse
        - Pro-m² Werte: Extrahiert Zonenflächen aus TabularData
        - Dynamische Zone-Erkennung: Keine hardcoded Floor-Namen

        Returns:
            ZonalComparison mit aggregierten Daten pro Orientierung
        """
        conn = sqlite3.connect(self.sql_file)
        try:
            # 1. Extrahiere alle Zonenflächen aus TabularData
            area_query = """
            SELECT
                rn.Value AS ZoneName,
                td.Value AS Area_m2
            FROM TabularData td
            LEFT JOIN Strings rs ON td.ReportNameIndex = rs.StringIndex
            LEFT JOIN Strings tn ON td.TableNameIndex = tn.StringIndex
            LEFT JOIN Strings rn ON td.RowNameIndex = rn.StringIndex
            LEFT JOIN Strings cn ON td.ColumnNameIndex = cn.StringIndex
            WHERE rs.Value = 'InputVerificationandResultsSummary'
              AND tn.Value = 'Zone Summary'
              AND cn.Value = 'Area'
              AND rn.Value NOT LIKE '%Total%'
            """
            df_areas = pd.read_sql_query(area_query, conn)
            zone_areas = {row['ZoneName']: float(row['Area_m2']) for _, row in df_areas.iterrows()}

            # 2. Finde alle Zonen-Namen dynamisch (Perimeter + Core, alle Floors)
            zones_query = """
            SELECT DISTINCT d.KeyValue as ZoneName
            FROM ReportVariableDataDictionary d
            WHERE d.KeyValue LIKE 'PERIMETER_%' OR d.KeyValue LIKE 'CORE_%'
            """
            df_zones = pd.read_sql_query(zones_query, conn)
            all_zone_names = [row['ZoneName'] for _, row in df_zones.iterrows()]

            # 3. Query für alle Zonen (alle Floors)
            zone_list_str = "'" + "', '".join(all_zone_names) + "'"
            query = f"""
            SELECT
                d.KeyValue as ZoneName,
                d.VariableName,
                AVG(v.VariableValue) as AvgValue,
                MIN(v.VariableValue) as MinValue,
                MAX(v.VariableValue) as MaxValue,
                SUM(v.VariableValue) as SumValue
            FROM ReportVariableData v
            JOIN ReportVariableDataDictionary d
                ON v.ReportVariableDataDictionaryIndex = d.ReportVariableDataDictionaryIndex
            WHERE d.KeyValue IN ({zone_list_str})
              AND (
                  d.VariableName LIKE '%Zone Mean Air Temperature%'
                  OR d.VariableName LIKE '%Ideal Loads Zone Total Heating Rate%'
                  OR d.VariableName LIKE '%Ideal Loads Zone Total Cooling Rate%'
                  OR d.VariableName LIKE '%Zone Lights Total Heating Energy%'
                  OR d.VariableName LIKE '%Zone Electric Equipment Total Heating Energy%'
                  OR d.VariableName LIKE '%Zone People Total Heating Energy%'
                  OR d.VariableName LIKE '%Zone Windows Total Heat Gain Energy%'
              )
            GROUP BY d.KeyValue, d.VariableName
            """

            df = pd.read_sql_query(query, conn)

            if df.empty:
                return ZonalComparison(zones={})

            # Helper: Parse Orientierung aus ZoneName
            def get_orientation(zone_name: str) -> str:
                zone_lower = zone_name.lower()
                if 'north' in zone_lower:
                    return 'North'
                elif 'east' in zone_lower:
                    return 'East'
                elif 'south' in zone_lower:
                    return 'South'
                elif 'west' in zone_lower:
                    return 'West'
                elif 'core' in zone_lower:
                    return 'Core'
                return 'Unknown'

            # 4. Aggregiere Daten pro Orientierung (über alle Floors)
            J_TO_KWH = 1 / 3600000.0  # J → kWh

            # Group by orientation
            orientation_groups = {}
            for zone_name in df['ZoneName'].unique():
                orientation = get_orientation(zone_name)
                if orientation not in orientation_groups:
                    orientation_groups[orientation] = []
                orientation_groups[orientation].append(zone_name)

            # Aggregiere pro Orientierung
            zones_data = {}
            for orientation, zone_names_list in orientation_groups.items():
                # Filter für diese Orientierung
                df_orient = df[df['ZoneName'].isin(zone_names_list)]

                # Gesamtfläche dieser Orientierung
                total_area = sum(zone_areas.get(zn, 0.0) for zn in zone_names_list)

                # Helper: Aggregiere Werte über alle Zonen dieser Orientierung
                def agg_val(var_pattern: str, stat: str, agg_func) -> float:
                    """Aggregiere über alle Zonen dieser Orientierung"""
                    values = []
                    for zn in zone_names_list:
                        zone_df = df_orient[df_orient['ZoneName'] == zn]
                        row = zone_df[zone_df['VariableName'].str.contains(var_pattern, na=False)]
                        if not row.empty:
                            values.append(float(row.iloc[0][stat]))
                    return agg_func(values) if values else 0.0

                # Temperaturen: Durchschnitt über alle Zonen
                avg_temp = agg_val('Zone Mean Air Temperature', 'AvgValue', lambda v: sum(v)/len(v))
                # Min/Max: Global über alle Zonen
                min_temp = agg_val('Zone Mean Air Temperature', 'MinValue', min)
                max_temp = agg_val('Zone Mean Air Temperature', 'MaxValue', max)

                # Lasten & Gewinne: SUMME über alle Zonen
                heating_kwh = agg_val('Heating Rate', 'SumValue', sum) / 1000.0
                cooling_kwh = agg_val('Cooling Rate', 'SumValue', sum) / 1000.0
                solar_gains_kwh = agg_val('Windows Total Heat Gain Energy', 'SumValue', sum) * J_TO_KWH
                lights_kwh = agg_val('Lights Total Heating Energy', 'SumValue', sum) * J_TO_KWH
                equipment_kwh = agg_val('Electric Equipment Total Heating Energy', 'SumValue', sum) * J_TO_KWH
                people_kwh = agg_val('People Total Heating Energy', 'SumValue', sum) * J_TO_KWH

                zone_data = ZoneData(
                    zone_name=f"{orientation} (all floors)",
                    orientation=orientation,
                    floor_area_m2=total_area,
                    avg_temperature_c=avg_temp,
                    min_temperature_c=min_temp,
                    max_temperature_c=max_temp,
                    heating_kwh=heating_kwh,
                    cooling_kwh=cooling_kwh,
                    solar_gains_kwh=solar_gains_kwh,
                    lights_kwh=lights_kwh,
                    equipment_kwh=equipment_kwh,
                    people_kwh=people_kwh,
                )

                zone_data.internal_gains_kwh = (
                    zone_data.lights_kwh +
                    zone_data.equipment_kwh +
                    zone_data.people_kwh
                )

                zones_data[orientation] = zone_data

            return ZonalComparison(zones=zones_data)

        except Exception as e:
            print(f"Warning: Could not extract zonal comparison: {e}")
            import traceback
            traceback.print_exc()
            return ZonalComparison(zones={})
        finally:
            conn.close()
