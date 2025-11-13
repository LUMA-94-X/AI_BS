"""Metadata und Simulation-Settings Generator.

Dieses Modul erstellt alle Gebäude-Metadaten und Simulations-Einstellungen:
- Building-Objekt
- SimulationControl
- Timestep
- RunPeriod
- Design Days
- Site:Location
- Output Variables
"""

from typing import Any, List, Tuple

from features.geometrie.types import MetadataConfig, OutputConfig, LocationData


class MetadataGenerator:
    """Generiert Metadaten und Simulations-Einstellungen für EnergyPlus IDFs."""

    def __init__(self, config: MetadataConfig = None):
        """
        Args:
            config: Metadata-Konfiguration (verwendet Defaults falls None)
        """
        self.config = config or MetadataConfig()

    def add_simulation_settings(
        self,
        idf: Any,
        geo_solution: Any = None
    ) -> None:
        """Fügt Simulation Control, Building, Timestep, etc. hinzu.

        Args:
            idf: eppy IDF-Objekt
            geo_solution: GeometrySolution (aktuell nicht verwendet, für zukünftige Erweiterungen)

        Note:
            Zone/System Sizing ist auf "No" gesetzt, da IdealLoads HVAC verwendet wird.
            IdealLoads braucht kein Sizing - es liefert unbegrenzt Heiz-/Kühlleistung.
        """
        # SimulationControl - Nur Annual Simulation (Weather File)
        idf.newidfobject(
            "SIMULATIONCONTROL",
            Do_Zone_Sizing_Calculation="No",  # Disabled: IdealLoads braucht kein Sizing
            Do_System_Sizing_Calculation="No",
            Do_Plant_Sizing_Calculation="No",
            Run_Simulation_for_Sizing_Periods="No",  # Design Days werden nicht simuliert
            Run_Simulation_for_Weather_File_Run_Periods="Yes",  # Annual Simulation!
        )

        # HeatBalanceAlgorithm
        idf.newidfobject(
            "HEATBALANCEALGORITHM",
            Algorithm="ConductionTransferFunction",
        )

        # Building
        idf.newidfobject(
            "BUILDING",
            Name=self.config.building_name,
            North_Axis=0.0,  # Orientation handled via surface coordinates
            Terrain=self.config.terrain,
            Loads_Convergence_Tolerance_Value=0.04,
            Temperature_Convergence_Tolerance_Value=0.4,
            Solar_Distribution=self.config.solar_distribution,
            Maximum_Number_of_Warmup_Days=self.config.warmup_days,
            Minimum_Number_of_Warmup_Days=6,
        )

        # Timestep
        idf.newidfobject(
            "TIMESTEP",
            Number_of_Timesteps_per_Hour=self.config.timestep
        )

        # RunPeriod (Jahressimulation)
        self._add_run_period(idf)

        # Design Days (für HVAC-Sizing, falls zukünftig benötigt)
        if self.config.include_design_days:
            self._add_design_days(idf)

    def add_site_location(
        self,
        idf: Any,
        location: LocationData = None
    ) -> None:
        """Fügt Site:Location hinzu.

        Args:
            idf: eppy IDF-Objekt
            location: LocationData (verwendet Defaults falls None)
        """
        loc = location or LocationData()

        idf.newidfobject(
            "SITE:LOCATION",
            Name=loc.name,
            Latitude=loc.latitude,
            Longitude=loc.longitude,
            Time_Zone=loc.time_zone,
            Elevation=loc.elevation,
        )

    def add_output_variables(
        self,
        idf: Any,
        output_config: OutputConfig = None
    ) -> None:
        """Fügt Output Variables hinzu.

        Args:
            idf: eppy IDF-Objekt
            output_config: Output-Konfiguration (verwendet Standard falls None)
        """
        config = output_config or OutputConfig.standard_outputs()

        # Output-Variablen
        for var in config.variables:
            idf.newidfobject(
                "OUTPUT:VARIABLE",
                **var.to_idf_args()
            )

        # Output:SQLite für Ergebnis-Analyse
        if config.include_sqlite:
            idf.newidfobject(
                "OUTPUT:SQLITE",
                Option_Type="SimpleAndTabular",
            )

        # Output:Table:SummaryReports
        idf.newidfobject(
            "OUTPUT:TABLE:SUMMARYREPORTS",
            Report_1_Name="AllSummary",
        )

    def _add_run_period(self, idf: Any) -> None:
        """Fügt RunPeriod hinzu (intern).

        Args:
            idf: eppy IDF-Objekt
        """
        # Parse start/end dates (format: "MM/DD")
        start_month, start_day = map(int, self.config.run_period_start.split('/'))
        end_month, end_day = map(int, self.config.run_period_end.split('/'))

        idf.newidfobject(
            "RUNPERIOD",
            Name="Annual",
            Begin_Month=start_month,
            Begin_Day_of_Month=start_day,
            Begin_Year=2024,  # Jahr ist für meiste Simulationen irrelevant
            End_Month=end_month,
            End_Day_of_Month=end_day,
            End_Year=2024,
            Day_of_Week_for_Start_Day="Monday",
            Use_Weather_File_Holidays_and_Special_Days="Yes",
            Use_Weather_File_Daylight_Saving_Period="Yes",
            Apply_Weekend_Holiday_Rule="No",
            Use_Weather_File_Rain_Indicators="Yes",
            Use_Weather_File_Snow_Indicators="Yes",
        )

    def _add_design_days(self, idf: Any) -> None:
        """Fügt Design Days hinzu (intern).

        Design Days werden für HVAC-Sizing benötigt, aber da wir IdealLoads
        verwenden, sind sie aktuell optional. Sie bleiben hier für zukünftige
        Kompatibilität mit echten HVAC-Systemen.

        Args:
            idf: eppy IDF-Objekt
        """
        # Heating Design Day (Winter)
        idf.newidfobject(
            "SIZINGPERIOD:DESIGNDAY",
            Name="Heating_Design_Day",
            Month=1,
            Day_of_Month=21,
            Day_Type="WinterDesignDay",
            Maximum_DryBulb_Temperature=-10.0,
            Daily_DryBulb_Temperature_Range=0.0,
            DryBulb_Temperature_Range_Modifier_Type="",
            DryBulb_Temperature_Range_Modifier_Day_Schedule_Name="",
            Humidity_Condition_Type="WetBulb",
            Wetbulb_or_DewPoint_at_Maximum_DryBulb="-10.0",
            Humidity_Condition_Day_Schedule_Name="",
            Humidity_Ratio_at_Maximum_DryBulb="",
            Enthalpy_at_Maximum_DryBulb="",
            Daily_WetBulb_Temperature_Range="",
            Barometric_Pressure=101325,
            Wind_Speed=4.5,
            Wind_Direction=0,
            Rain_Indicator="No",
            Snow_Indicator="No",
            Daylight_Saving_Time_Indicator="No",
            Solar_Model_Indicator="ASHRAEClearSky",
            Beam_Solar_Day_Schedule_Name="",
            Diffuse_Solar_Day_Schedule_Name="",
            ASHRAE_Clear_Sky_Optical_Depth_for_Beam_Irradiance_taub="",
            ASHRAE_Clear_Sky_Optical_Depth_for_Diffuse_Irradiance_taud="",
            Sky_Clearness="",
        )

        # Cooling Design Day (Sommer)
        idf.newidfobject(
            "SIZINGPERIOD:DESIGNDAY",
            Name="Cooling_Design_Day",
            Month=7,
            Day_of_Month=21,
            Day_Type="SummerDesignDay",
            Maximum_DryBulb_Temperature=32.0,
            Daily_DryBulb_Temperature_Range=10.0,
            DryBulb_Temperature_Range_Modifier_Type="",
            DryBulb_Temperature_Range_Modifier_Day_Schedule_Name="",
            Humidity_Condition_Type="WetBulb",
            Wetbulb_or_DewPoint_at_Maximum_DryBulb="23.0",
            Humidity_Condition_Day_Schedule_Name="",
            Humidity_Ratio_at_Maximum_DryBulb="",
            Enthalpy_at_Maximum_DryBulb="",
            Daily_WetBulb_Temperature_Range="",
            Barometric_Pressure=101325,
            Wind_Speed=4.0,
            Wind_Direction=180,
            Rain_Indicator="No",
            Snow_Indicator="No",
            Daylight_Saving_Time_Indicator="No",
            Solar_Model_Indicator="ASHRAEClearSky",
            Beam_Solar_Day_Schedule_Name="",
            Diffuse_Solar_Day_Schedule_Name="",
            ASHRAE_Clear_Sky_Optical_Depth_for_Beam_Irradiance_taub="",
            ASHRAE_Clear_Sky_Optical_Depth_for_Diffuse_Irradiance_taud="",
            Sky_Clearness="",
        )
