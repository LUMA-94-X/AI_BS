"""Simple box geometry generator for EnergyPlus models."""

from typing import Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path

from eppy.modeleditor import IDF
from src.utils.config import get_config
from src.materials.standard_constructions import add_basic_constructions


@dataclass
class BuildingGeometry:
    """Parameters for simple box building geometry."""

    length: float  # meters (X dimension)
    width: float  # meters (Y dimension)
    height: float  # meters (Z dimension)
    num_floors: int = 1
    window_wall_ratio: float = 0.3
    orientation: float = 0.0  # degrees from North

    def __post_init__(self):
        """Validate parameters."""
        if self.length <= 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("Dimensions must be positive")
        if self.num_floors < 1:
            raise ValueError("Number of floors must be at least 1")
        if not 0 <= self.window_wall_ratio <= 1:
            raise ValueError("Window-to-wall ratio must be between 0 and 1")
        if not 0 <= self.orientation < 360:
            raise ValueError("Orientation must be between 0 and 360 degrees")

    @property
    def floor_height(self) -> float:
        """Calculate height per floor."""
        return self.height / self.num_floors

    @property
    def floor_area(self) -> float:
        """Calculate floor area."""
        return self.length * self.width

    @property
    def total_floor_area(self) -> float:
        """Calculate total floor area for all floors."""
        return self.floor_area * self.num_floors

    @property
    def volume(self) -> float:
        """Calculate building volume."""
        return self.length * self.width * self.height


class SimpleBoxGenerator:
    """Generator for simple box-shaped building models."""

    def __init__(self, config=None):
        """Initialize the generator.

        Args:
            config: Configuration object. If None, uses global config.
        """
        self.config = config or get_config()

    def create_model(
        self,
        geometry: BuildingGeometry,
        idf_path: Optional[Path | str] = None,
    ) -> IDF:
        """Create a simple box building model.

        Args:
            geometry: Building geometry parameters
            idf_path: Path to save the IDF file (optional)

        Returns:
            IDF object
        """
        # Initialize IDF with EnergyPlus version
        idd_file = self._get_idd_file()
        IDF.setiddname(idd_file)

        # Create minimal IDF template
        import tempfile
        minimal_idf_content = "VERSION,\n  23.2;\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False) as f:
            f.write(minimal_idf_content)
            temp_idf_path = f.name

        # Load the template
        idf = IDF(temp_idf_path)

        # Clean up temp file
        Path(temp_idf_path).unlink()

        # Add materials and constructions
        add_basic_constructions(idf)

        # Add simulation control (REQUIRED for HVAC)
        self._add_simulation_control(idf)

        # Add heat balance algorithm (REQUIRED for HVAC)
        self._add_heat_balance_algorithm(idf)

        # Add building object
        self._add_building(idf, geometry)

        # Add global geometry rules
        self._add_global_geometry_rules(idf)

        # Add timestep
        self._add_timestep(idf)

        # Add run period
        self._add_run_period(idf)

        # Add design days (REQUIRED for HVAC sizing)
        self._add_design_days(idf)

        # Add site location (default)
        self._add_site_location(idf)

        # Add zones
        self._add_zones(idf, geometry)

        # Add zone sizing (REQUIRED for HVAC sizing)
        self._add_zone_sizing(idf, geometry)

        # Add surfaces (walls, floors, ceilings, windows)
        self._add_surfaces(idf, geometry)

        # Add thermostats (REQUIRED for HVAC)
        self._add_thermostats(idf, geometry)

        # Add schedules
        self._add_schedules(idf)

        # Add internal loads
        self._add_internal_loads(idf, geometry)

        # Note: HVAC system not included in basic generator
        # For simulations, use an example IDF with HVAC as a starting point
        # Or add HVAC objects manually after generation

        # Add output variables
        self._add_output_variables(idf)

        # Save if path provided
        if idf_path:
            idf.saveas(str(idf_path), encoding='utf-8')

        return idf

    def _get_idd_file(self) -> str:
        """Get path to Energy+.idd file."""
        ep_path = self.config.energyplus.get_executable_path().parent
        idd_file = ep_path / "Energy+.idd"

        if not idd_file.exists():
            raise FileNotFoundError(
                f"Energy+.idd not found at {idd_file}. "
                "Please check your EnergyPlus installation."
            )

        return str(idd_file)

    def _add_simulation_control(self, idf: IDF) -> None:
        """Add SimulationControl object (required for HVAC)."""
        idf.newidfobject(
            "SIMULATIONCONTROL",
            Do_Zone_Sizing_Calculation="Yes",
            Do_System_Sizing_Calculation="Yes",
            Do_Plant_Sizing_Calculation="No",
            Run_Simulation_for_Sizing_Periods="No",
            Run_Simulation_for_Weather_File_Run_Periods="Yes",
            Do_HVAC_Sizing_Simulation_for_Sizing_Periods="No",
            Maximum_Number_of_HVAC_Sizing_Simulation_Passes=1,
        )

    def _add_heat_balance_algorithm(self, idf: IDF) -> None:
        """Add HeatBalanceAlgorithm object (required for HVAC)."""
        idf.newidfobject(
            "HEATBALANCEALGORITHM",
            Algorithm="ConductionTransferFunction",
            Surface_Temperature_Upper_Limit="",
            Minimum_Surface_Convection_Heat_Transfer_Coefficient_Value="",
            Maximum_Surface_Convection_Heat_Transfer_Coefficient_Value="",
        )

    def _add_building(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add Building object."""
        idf.newidfobject(
            "BUILDING",
            Name="SimpleBoxBuilding",
            North_Axis=geometry.orientation,
            Terrain="Suburbs",
            Loads_Convergence_Tolerance_Value=0.04,
            Temperature_Convergence_Tolerance_Value=0.4,
            Solar_Distribution="FullExterior",
            Maximum_Number_of_Warmup_Days=25,
        )

    def _add_global_geometry_rules(self, idf: IDF) -> None:
        """Add GlobalGeometryRules."""
        idf.newidfobject(
            "GLOBALGEOMETRYRULES",
            Starting_Vertex_Position="UpperLeftCorner",
            Vertex_Entry_Direction="Counterclockwise",
            Coordinate_System="Relative",
        )

    def _add_timestep(self, idf: IDF) -> None:
        """Add Timestep object."""
        idf.newidfobject("TIMESTEP", Number_of_Timesteps_per_Hour=4)

    def _add_run_period(self, idf: IDF) -> None:
        """Add RunPeriod for annual simulation."""
        idf.newidfobject(
            "RUNPERIOD",
            Name="AnnualSimulation",
            Begin_Month=1,
            Begin_Day_of_Month=1,
            End_Month=12,
            End_Day_of_Month=31,
            Day_of_Week_for_Start_Day="Monday",
            Use_Weather_File_Holidays_and_Special_Days="Yes",
            Use_Weather_File_Daylight_Saving_Period="Yes",
        )

    def _add_site_location(self, idf: IDF) -> None:
        """Add Site:Location (default values, will be overridden by weather file)."""
        idf.newidfobject(
            "SITE:LOCATION",
            Name="Default Location",
            Latitude=50.0,
            Longitude=10.0,
            Time_Zone=1.0,
            Elevation=100.0,
        )

    def _add_design_days(self, idf: IDF) -> None:
        """Add SizingPeriod:DesignDay objects (required for HVAC sizing).

        These are generic design days. They will be overridden by actual
        weather file data if present, but are required for HVAC system sizing.
        """
        # Summer Design Day (Cooling)
        idf.newidfobject(
            "SIZINGPERIOD:DESIGNDAY",
            Name="Summer Design Day",
            Month=7,
            Day_of_Month=21,
            Day_Type="SummerDesignDay",
            Maximum_DryBulb_Temperature=32.0,
            Daily_DryBulb_Temperature_Range=10.0,
            DryBulb_Temperature_Range_Modifier_Type="DefaultMultipliers",
            DryBulb_Temperature_Range_Modifier_Day_Schedule_Name="",
            Humidity_Condition_Type="Wetbulb",
            Wetbulb_or_DewPoint_at_Maximum_DryBulb=23.0,
            Humidity_Condition_Day_Schedule_Name="",
            Humidity_Ratio_at_Maximum_DryBulb="",
            Enthalpy_at_Maximum_DryBulb="",
            Daily_WetBulb_Temperature_Range="",
            Barometric_Pressure="",
            Wind_Speed=3.5,
            Wind_Direction=230,
            Rain_Indicator="No",
            Snow_Indicator="No",
            Daylight_Saving_Time_Indicator="Yes",
            Solar_Model_Indicator="ASHRAEClearSky",
            Beam_Solar_Day_Schedule_Name="",
            Diffuse_Solar_Day_Schedule_Name="",
            ASHRAE_Clear_Sky_Optical_Depth_for_Beam_Irradiance_taub=0.564,
            ASHRAE_Clear_Sky_Optical_Depth_for_Diffuse_Irradiance_taud=1.918,
            Sky_Clearness=1.0,  # Clear sky for maximum solar gains (cooling load)
        )

        # Winter Design Day (Heating)
        idf.newidfobject(
            "SIZINGPERIOD:DESIGNDAY",
            Name="Winter Design Day",
            Month=1,
            Day_of_Month=21,
            Day_Type="WinterDesignDay",
            Maximum_DryBulb_Temperature=-10.0,
            Daily_DryBulb_Temperature_Range=0.0,
            DryBulb_Temperature_Range_Modifier_Type="DefaultMultipliers",
            DryBulb_Temperature_Range_Modifier_Day_Schedule_Name="",
            Humidity_Condition_Type="Wetbulb",
            Wetbulb_or_DewPoint_at_Maximum_DryBulb=-12.0,
            Humidity_Condition_Day_Schedule_Name="",
            Humidity_Ratio_at_Maximum_DryBulb="",
            Enthalpy_at_Maximum_DryBulb="",
            Daily_WetBulb_Temperature_Range="",
            Barometric_Pressure="",
            Wind_Speed=5.0,
            Wind_Direction=270,
            Rain_Indicator="No",
            Snow_Indicator="No",
            Daylight_Saving_Time_Indicator="No",
            Solar_Model_Indicator="ASHRAEClearSky",
            Beam_Solar_Day_Schedule_Name="",
            Diffuse_Solar_Day_Schedule_Name="",
            ASHRAE_Clear_Sky_Optical_Depth_for_Beam_Irradiance_taub=0.313,
            ASHRAE_Clear_Sky_Optical_Depth_for_Diffuse_Irradiance_taud=2.303,
            Sky_Clearness=0.0,  # Overcast for minimum solar gains (heating load)
        )

    def _add_zones(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add thermal zones for each floor."""
        for floor in range(geometry.num_floors):
            idf.newidfobject(
                "ZONE",
                Name=f"Zone_Floor_{floor+1}",
                Direction_of_Relative_North=0,
                X_Origin=0,
                Y_Origin=0,
                Z_Origin=floor * geometry.floor_height,
                Type=1,
                Multiplier=1,
                Ceiling_Height=geometry.floor_height,
                Volume=geometry.floor_area * geometry.floor_height,
            )

    def _add_zone_sizing(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add Sizing:Zone objects for each zone (required for HVAC sizing)."""
        for floor in range(geometry.num_floors):
            zone_name = f"Zone_Floor_{floor+1}"
            idf.newidfobject(
                "SIZING:ZONE",
                Zone_or_ZoneList_Name=zone_name,
                Zone_Cooling_Design_Supply_Air_Temperature_Input_Method="SupplyAirTemperature",
                Zone_Cooling_Design_Supply_Air_Temperature=13.0,
                Zone_Cooling_Design_Supply_Air_Temperature_Difference="",
                Zone_Heating_Design_Supply_Air_Temperature_Input_Method="SupplyAirTemperature",
                Zone_Heating_Design_Supply_Air_Temperature=50.0,
                Zone_Heating_Design_Supply_Air_Temperature_Difference="",
                Zone_Cooling_Design_Supply_Air_Humidity_Ratio=0.010,
                Zone_Heating_Design_Supply_Air_Humidity_Ratio=0.008,
                Design_Specification_Outdoor_Air_Object_Name="",
                Zone_Heating_Sizing_Factor="",
                Zone_Cooling_Sizing_Factor="",
                Cooling_Design_Air_Flow_Method="DesignDayWithLimit",
                Cooling_Design_Air_Flow_Rate="",
                Cooling_Minimum_Air_Flow_per_Zone_Floor_Area="",
                Cooling_Minimum_Air_Flow="",
                Cooling_Minimum_Air_Flow_Fraction="",
                Heating_Design_Air_Flow_Method="DesignDay",
                Heating_Design_Air_Flow_Rate="",
                Heating_Maximum_Air_Flow_per_Zone_Floor_Area="",
                Heating_Maximum_Air_Flow="",
                Heating_Maximum_Air_Flow_Fraction="",
                Design_Specification_Zone_Air_Distribution_Object_Name="",
                Account_for_Dedicated_Outdoor_Air_System="No",
                Dedicated_Outdoor_Air_System_Control_Strategy="NeutralSupplyAir",
                Dedicated_Outdoor_Air_Low_Setpoint_Temperature_for_Design="autosize",
                Dedicated_Outdoor_Air_High_Setpoint_Temperature_for_Design="autosize",
            )

    def _add_surfaces(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add surfaces (walls, floors, ceilings) and windows."""
        for floor in range(geometry.num_floors):
            zone_name = f"Zone_Floor_{floor+1}"
            z_base = floor * geometry.floor_height
            z_top = z_base + geometry.floor_height

            # Floor
            floor_boundary = "Ground" if floor == 0 else "Surface"
            floor_boundary_object = "" if floor == 0 else f"Zone_Floor_{floor}_Ceiling"
            floor_sun_exposed = "NoSun"
            floor_wind_exposed = "NoWind"
            # Use same construction for interzone floors as ceilings
            floor_construction = "FloorConstruction" if floor == 0 else "CeilingConstruction"

            # Floor vertices: counterclockwise when viewed from above (normal points down, tilt=180)
            idf.newidfobject(
                "BUILDINGSURFACE:DETAILED",
                Name=f"{zone_name}_Floor",
                Surface_Type="Floor",
                Construction_Name=floor_construction,
                Zone_Name=zone_name,
                Space_Name="",
                Outside_Boundary_Condition=floor_boundary,
                Outside_Boundary_Condition_Object=floor_boundary_object,
                Sun_Exposure=floor_sun_exposed,
                Wind_Exposure=floor_wind_exposed,
                View_Factor_to_Ground="autocalculate",
                Number_of_Vertices=4,
                Vertex_1_Xcoordinate=0,
                Vertex_1_Ycoordinate=0,
                Vertex_1_Zcoordinate=z_base,
                Vertex_2_Xcoordinate=0,
                Vertex_2_Ycoordinate=geometry.width,
                Vertex_2_Zcoordinate=z_base,
                Vertex_3_Xcoordinate=geometry.length,
                Vertex_3_Ycoordinate=geometry.width,
                Vertex_3_Zcoordinate=z_base,
                Vertex_4_Xcoordinate=geometry.length,
                Vertex_4_Ycoordinate=0,
                Vertex_4_Zcoordinate=z_base,
            )

            # Ceiling
            is_top_floor = (floor == geometry.num_floors - 1)
            ceiling_type = "Roof" if is_top_floor else "Ceiling"
            ceiling_boundary = "Outdoors" if is_top_floor else "Surface"
            ceiling_boundary_object = "" if is_top_floor else f"Zone_Floor_{floor+2}_Floor"
            ceiling_sun_exposed = "SunExposed" if is_top_floor else "NoSun"
            ceiling_wind_exposed = "WindExposed" if is_top_floor else "NoWind"

            # Ceiling vertices: clockwise when viewed from above (normal points up, tilt=0)
            idf.newidfobject(
                "BUILDINGSURFACE:DETAILED",
                Name=f"{zone_name}_Ceiling",
                Surface_Type=ceiling_type,
                Construction_Name="RoofConstruction" if ceiling_type == "Roof" else "CeilingConstruction",
                Zone_Name=zone_name,
                Space_Name="",
                Outside_Boundary_Condition=ceiling_boundary,
                Outside_Boundary_Condition_Object=ceiling_boundary_object,
                Sun_Exposure=ceiling_sun_exposed,
                Wind_Exposure=ceiling_wind_exposed,
                View_Factor_to_Ground="autocalculate",
                Number_of_Vertices=4,
                Vertex_1_Xcoordinate=0,
                Vertex_1_Ycoordinate=0,
                Vertex_1_Zcoordinate=z_top,
                Vertex_2_Xcoordinate=geometry.length,
                Vertex_2_Ycoordinate=0,
                Vertex_2_Zcoordinate=z_top,
                Vertex_3_Xcoordinate=geometry.length,
                Vertex_3_Ycoordinate=geometry.width,
                Vertex_3_Zcoordinate=z_top,
                Vertex_4_Xcoordinate=0,
                Vertex_4_Ycoordinate=geometry.width,
                Vertex_4_Zcoordinate=z_top,
            )

            # Walls (4 walls: North, East, South, West)
            walls = [
                {
                    "name": "North",
                    "vertices": [
                        (0, geometry.width, z_base),
                        (0, geometry.width, z_top),
                        (geometry.length, geometry.width, z_top),
                        (geometry.length, geometry.width, z_base),
                    ],
                },
                {
                    "name": "East",
                    "vertices": [
                        (geometry.length, geometry.width, z_base),
                        (geometry.length, geometry.width, z_top),
                        (geometry.length, 0, z_top),
                        (geometry.length, 0, z_base),
                    ],
                },
                {
                    "name": "South",
                    "vertices": [
                        (geometry.length, 0, z_base),
                        (geometry.length, 0, z_top),
                        (0, 0, z_top),
                        (0, 0, z_base),
                    ],
                },
                {
                    "name": "West",
                    "vertices": [
                        (0, 0, z_base),
                        (0, 0, z_top),
                        (0, geometry.width, z_top),
                        (0, geometry.width, z_base),
                    ],
                },
            ]

            for wall in walls:
                wall_name = f"{zone_name}_Wall_{wall['name']}"

                idf.newidfobject(
                    "BUILDINGSURFACE:DETAILED",
                    Name=wall_name,
                    Surface_Type="Wall",
                    Construction_Name="WallConstruction",
                    Zone_Name=zone_name,
                    Space_Name="",
                    Outside_Boundary_Condition="Outdoors",
                    Outside_Boundary_Condition_Object="",
                    Sun_Exposure="SunExposed",
                    Wind_Exposure="WindExposed",
                    View_Factor_to_Ground="autocalculate",
                    Number_of_Vertices=4,
                    Vertex_1_Xcoordinate=wall["vertices"][0][0],
                    Vertex_1_Ycoordinate=wall["vertices"][0][1],
                    Vertex_1_Zcoordinate=wall["vertices"][0][2],
                    Vertex_2_Xcoordinate=wall["vertices"][1][0],
                    Vertex_2_Ycoordinate=wall["vertices"][1][1],
                    Vertex_2_Zcoordinate=wall["vertices"][1][2],
                    Vertex_3_Xcoordinate=wall["vertices"][2][0],
                    Vertex_3_Ycoordinate=wall["vertices"][2][1],
                    Vertex_3_Zcoordinate=wall["vertices"][2][2],
                    Vertex_4_Xcoordinate=wall["vertices"][3][0],
                    Vertex_4_Ycoordinate=wall["vertices"][3][1],
                    Vertex_4_Zcoordinate=wall["vertices"][3][2],
                )

                # Add window if WWR > 0
                if geometry.window_wall_ratio > 0:
                    self._add_window(idf, wall_name, wall["vertices"], geometry.window_wall_ratio)

    def _add_window(
        self, idf: IDF, wall_name: str, wall_vertices: List[Tuple[float, float, float]], wwr: float
    ) -> None:
        """Add a window to a wall.

        Args:
            idf: IDF object
            wall_name: Name of the wall surface
            wall_vertices: List of 4 vertices defining the wall (counter-clockwise from bottom-left)
            wwr: Window-to-wall ratio (0.0 to 1.0)
        """
        v1, v2, v3, v4 = wall_vertices

        # Calculate wall dimensions
        # Wall vertices are: bottom-left, top-left, top-right, bottom-right (counter-clockwise)
        wall_width = ((v4[0] - v1[0])**2 + (v4[1] - v1[1])**2 + (v4[2] - v1[2])**2)**0.5
        wall_height = ((v2[0] - v1[0])**2 + (v2[1] - v1[1])**2 + (v2[2] - v1[2])**2)**0.5

        # Calculate window dimensions maintaining WWR
        # Use square root approach: if WWR=0.3, window is 0.547 of wall width/height
        window_width = wall_width * (wwr ** 0.5)
        window_height = wall_height * (wwr ** 0.5)

        # Ensure reasonable dimensions
        sill_height = 0.9  # meters above floor
        head_height = min(wall_height - 0.3, sill_height + window_height)  # At least 0.3m from ceiling
        window_height = head_height - sill_height

        # Center window horizontally
        h_offset = (wall_width - window_width) / 2

        # Calculate unit vectors for the wall
        # Horizontal direction (along bottom edge)
        dx_h = (v4[0] - v1[0]) / wall_width if wall_width > 0 else 0
        dy_h = (v4[1] - v1[1]) / wall_width if wall_width > 0 else 0
        dz_h = (v4[2] - v1[2]) / wall_width if wall_width > 0 else 0

        # Vertical direction (along left edge)
        dx_v = (v2[0] - v1[0]) / wall_height if wall_height > 0 else 0
        dy_v = (v2[1] - v1[1]) / wall_height if wall_height > 0 else 0
        dz_v = (v2[2] - v1[2]) / wall_height if wall_height > 0 else 0

        # Calculate window corner positions
        # Start from bottom-left corner of window
        w_bl_x = v1[0] + h_offset * dx_h + sill_height * dx_v
        w_bl_y = v1[1] + h_offset * dy_h + sill_height * dy_v
        w_bl_z = v1[2] + h_offset * dz_h + sill_height * dz_v

        # Bottom-right corner
        w_br_x = w_bl_x + window_width * dx_h
        w_br_y = w_bl_y + window_width * dy_h
        w_br_z = w_bl_z + window_width * dz_h

        # Top-left corner
        w_tl_x = w_bl_x + window_height * dx_v
        w_tl_y = w_bl_y + window_height * dy_v
        w_tl_z = w_bl_z + window_height * dz_v

        # Top-right corner
        w_tr_x = w_tl_x + window_width * dx_h
        w_tr_y = w_tl_y + window_width * dy_h
        w_tr_z = w_tl_z + window_width * dz_h

        window_name = f"{wall_name}_Window"

        # Create window with calculated vertices (counter-clockwise from bottom-left)
        idf.newidfobject(
            "FENESTRATIONSURFACE:DETAILED",
            Name=window_name,
            Surface_Type="Window",
            Construction_Name="WindowConstruction",
            Building_Surface_Name=wall_name,
            Outside_Boundary_Condition_Object="",
            View_Factor_to_Ground="autocalculate",
            Frame_and_Divider_Name="",
            Multiplier=1,
            Number_of_Vertices=4,
            Vertex_1_Xcoordinate=w_bl_x,
            Vertex_1_Ycoordinate=w_bl_y,
            Vertex_1_Zcoordinate=w_bl_z,
            Vertex_2_Xcoordinate=w_tl_x,
            Vertex_2_Ycoordinate=w_tl_y,
            Vertex_2_Zcoordinate=w_tl_z,
            Vertex_3_Xcoordinate=w_tr_x,
            Vertex_3_Ycoordinate=w_tr_y,
            Vertex_3_Zcoordinate=w_tr_z,
            Vertex_4_Xcoordinate=w_br_x,
            Vertex_4_Ycoordinate=w_br_y,
            Vertex_4_Zcoordinate=w_br_z,
        )

    def _add_schedules(self, idf: IDF) -> None:
        """Add basic schedules."""
        # Always on schedule
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="AlwaysOn",
            Schedule_Type_Limits_Name="",
            Hourly_Value=1.0,
        )

        # Office occupancy schedule (simplified)
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="OccupancySchedule",
            Schedule_Type_Limits_Name="",
            Field_1="Through: 12/31",
            Field_2="For: Weekdays",
            Field_3="Until: 08:00", Field_4="0.0",
            Field_5="Until: 18:00", Field_6="1.0",
            Field_7="Until: 24:00", Field_8="0.0",
            Field_9="For: AllOtherDays",
            Field_10="Until: 24:00", Field_11="0.0",
        )

        # Activity level schedule (120 W per person - typical office)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="ActivityLevel",
            Schedule_Type_Limits_Name="",
            Hourly_Value=120.0,
        )

        # Heating setpoint schedule (20°C when occupied)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="HeatingSetpoint",
            Schedule_Type_Limits_Name="",
            Hourly_Value=20.0,
        )

        # Cooling setpoint schedule (24°C when occupied)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="CoolingSetpoint",
            Schedule_Type_Limits_Name="",
            Hourly_Value=24.0,
        )

        # Thermostat control type schedule
        # Value 4 = DualSetpointWithDeadband (for ThermostatSetpoint:DualSetpoint)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="ThermostatControlType",
            Schedule_Type_Limits_Name="",
            Hourly_Value=4.0,
        )

    def _add_thermostats(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add thermostats for each zone (REQUIRED for HVAC)."""
        # First add the dual setpoint definition
        idf.newidfobject(
            "THERMOSTATSETPOINT:DUALSETPOINT",
            Name="DualSetpoint",
            Heating_Setpoint_Temperature_Schedule_Name="HeatingSetpoint",
            Cooling_Setpoint_Temperature_Schedule_Name="CoolingSetpoint",
        )

        # Add thermostat control for each zone
        for floor in range(geometry.num_floors):
            zone_name = f"Zone_Floor_{floor+1}"

            idf.newidfobject(
                "ZONECONTROL:THERMOSTAT",
                Name=f"{zone_name}_Thermostat",
                Zone_or_ZoneList_Name=zone_name,
                Control_Type_Schedule_Name="ThermostatControlType",  # Value 4 = DualSetpoint
                Control_1_Object_Type="ThermostatSetpoint:DualSetpoint",
                Control_1_Name="DualSetpoint",
                Control_2_Object_Type="",
                Control_2_Name="",
                Control_3_Object_Type="",
                Control_3_Name="",
                Control_4_Object_Type="",
                Control_4_Name="",
            )

    def _add_internal_loads(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add internal loads (people, lights, equipment)."""
        for floor in range(geometry.num_floors):
            zone_name = f"Zone_Floor_{floor+1}"

            # People
            idf.newidfobject(
                "PEOPLE",
                Name=f"{zone_name}_People",
                Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
                Number_of_People_Schedule_Name="OccupancySchedule",
                Number_of_People_Calculation_Method="People/Area",
                Number_of_People="",
                People_per_Floor_Area=0.05,  # 5 people per 100 m² (0.05 people/m²)
                Floor_Area_per_Person="",
                Fraction_Radiant=0.3,
                Activity_Level_Schedule_Name="ActivityLevel",
            )

            # Lights
            idf.newidfobject(
                "LIGHTS",
                Name=f"{zone_name}_Lights",
                Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
                Schedule_Name="OccupancySchedule",
                Design_Level_Calculation_Method="Watts/Area",
                Lighting_Level="",
                Watts_per_Zone_Floor_Area=10.0,  # 10 W/m²
                Watts_per_Person="",
                Return_Air_Fraction=0.0,
                Fraction_Radiant=0.7,
                Fraction_Visible=0.2,
            )

            # Electric Equipment
            idf.newidfobject(
                "ELECTRICEQUIPMENT",
                Name=f"{zone_name}_Equipment",
                Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
                Schedule_Name="OccupancySchedule",
                Design_Level_Calculation_Method="Watts/Area",
                Design_Level="",
                Watts_per_Zone_Floor_Area=15.0,  # 15 W/m²
                Watts_per_Person="",
                Fraction_Latent=0.0,
                Fraction_Radiant=0.3,
                Fraction_Lost=0.0,
            )

    def _add_ideal_loads(self, idf: IDF, geometry: BuildingGeometry) -> None:
        """Add ideal loads air system for HVAC (direct objects, not templates).

        NOTE: This method is currently not used due to configuration issues with
        ZoneHVAC:IdealLoadsAirSystem in EnergyPlus 23.2. For simulations with HVAC,
        it's recommended to start with an example IDF that has a working HVAC system.
        """
        # Method kept for reference but not called from create_model()
        for floor in range(geometry.num_floors):
            zone_name = f"Zone_Floor_{floor+1}"

            # Use ZoneHVAC:IdealLoadsAirSystem (direct object) instead of template
            idf.newidfobject(
                "ZONEHVAC:IDEALLOADSAIRSYSTEM",
                Name=f"{zone_name}_IdealLoads",
                Zone_Supply_Air_Node_Name=f"{zone_name}_Supply",
                Zone_Exhaust_Air_Node_Name="",
                System_Inlet_Air_Node_Name="",
                Maximum_Heating_Supply_Air_Temperature=50.0,
                Minimum_Cooling_Supply_Air_Temperature=13.0,
                Maximum_Heating_Supply_Air_Humidity_Ratio=0.015,
                Minimum_Cooling_Supply_Air_Humidity_Ratio=0.010,
                Heating_Limit="NoLimit",
                Maximum_Heating_Air_Flow_Rate="",
                Maximum_Sensible_Heating_Capacity="",
                Cooling_Limit="NoLimit",
                Maximum_Cooling_Air_Flow_Rate="",
                Maximum_Total_Cooling_Capacity="",
                Heating_Availability_Schedule_Name="AlwaysOn",
                Cooling_Availability_Schedule_Name="AlwaysOn",
                Dehumidification_Control_Type="None",
                Cooling_Sensible_Heat_Ratio="",
                Humidification_Control_Type="None",
                Design_Specification_Outdoor_Air_Object_Name="",
                Demand_Controlled_Ventilation_Type="None",
                Outdoor_Air_Economizer_Type="NoEconomizer",
                Heat_Recovery_Type="None",
                Sensible_Heat_Recovery_Effectiveness=0.70,
                Latent_Heat_Recovery_Effectiveness=0.65,
            )

            # Add zone equipment list
            idf.newidfobject(
                "ZONEHVAC:EQUIPMENTLIST",
                Name=f"{zone_name}_Equipment",
                Load_Distribution_Scheme="SequentialLoad",
                Zone_Equipment_1_Object_Type="ZoneHVAC:IdealLoadsAirSystem",
                Zone_Equipment_1_Name=f"{zone_name}_IdealLoads",
                Zone_Equipment_1_Cooling_Sequence=1,
                Zone_Equipment_1_Heating_or_NoLoad_Sequence=1,
                Zone_Equipment_1_Sequential_Cooling_Fraction_Schedule_Name="",
                Zone_Equipment_1_Sequential_Heating_Fraction_Schedule_Name="",
            )

            # Add zone equipment connections
            idf.newidfobject(
                "ZONEHVAC:EQUIPMENTCONNECTIONS",
                Zone_Name=zone_name,
                Zone_Conditioning_Equipment_List_Name=f"{zone_name}_Equipment",
                Zone_Air_Inlet_Node_or_NodeList_Name=f"{zone_name}_Supply",
                Zone_Air_Exhaust_Node_or_NodeList_Name="",
                Zone_Air_Node_Name=f"{zone_name}_Air",
                Zone_Return_Air_Node_or_NodeList_Name="",
            )

    def _add_output_variables(self, idf: IDF) -> None:
        """Add output variables for results."""
        output_vars = [
            "Zone Mean Air Temperature",
            "Zone Air System Sensible Heating Energy",
            "Zone Air System Sensible Cooling Energy",
            "Zone Lights Electric Energy",
            "Zone Electric Equipment Electric Energy",
        ]

        for var in output_vars:
            idf.newidfobject(
                "OUTPUT:VARIABLE",
                Key_Value="*",
                Variable_Name=var,
                Reporting_Frequency="Hourly",
            )

        # Add summary reports
        idf.newidfobject(
            "OUTPUT:TABLE:SUMMARYREPORTS",
            Report_1_Name="AllSummary",
        )

        # Add SQL output
        idf.newidfobject(
            "OUTPUT:SQLITE",
            Option_Type="SimpleAndTabular",
        )
