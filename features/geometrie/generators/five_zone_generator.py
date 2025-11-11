"""5-Zone Generator für EnergyPlus-Modelle aus Energieausweis-Daten."""

from typing import Optional, Dict, Tuple
from pathlib import Path
import tempfile

from eppy.modeleditor import IDF
from core.config import get_config
from core.materialien import add_basic_constructions

from features.geometrie.models.energieausweis_input import EnergieausweisInput
from features.geometrie.utils.geometry_solver import GeometrySolver, GeometrySolution
from features.geometrie.utils.perimeter_calculator import (
    PerimeterCalculator,
    ZoneLayout,
    ZoneGeometry
)
from features.geometrie.utils.fenster_distribution import (
    FensterDistribution,
    OrientationWWR,
    Orientation
)


class FiveZoneGenerator:
    """Generator für 5-Zonen-Gebäudemodelle (Perimeter N/E/S/W + Kern)."""

    def __init__(self, config=None):
        """
        Initialisiert den Generator.

        Args:
            config: Configuration object. If None, uses global config.
        """
        self.config = config or get_config()
        self.geometry_solver = GeometrySolver()
        self.perimeter_calc = PerimeterCalculator()
        self.fenster_dist = FensterDistribution()

    def create_from_energieausweis(
        self,
        ea_data: EnergieausweisInput,
        output_path: Optional[Path] = None
    ) -> IDF:
        """
        Erstellt 5-Zonen-IDF aus Energieausweis-Daten.

        Args:
            ea_data: Energieausweis-Eingabedaten
            output_path: Pfad zum Speichern des IDF (optional)

        Returns:
            IDF-Objekt
        """

        # 1. Geometrie rekonstruieren
        geo_solution = self.geometry_solver.solve(ea_data)

        # 2. Multi-Floor Zonen-Layouts erstellen
        wwr_avg = ea_data.fenster.window_wall_ratio or 0.3
        layouts = self.perimeter_calc.create_multi_floor_layout(
            building_length=geo_solution.length,
            building_width=geo_solution.width,
            floor_height=geo_solution.floor_height,
            num_floors=geo_solution.num_floors,
            wwr=wwr_avg
        )

        # 3. Fensterverteilung berechnen
        wall_areas = self.fenster_dist.estimate_wall_areas_from_geometry(
            building_length=geo_solution.length,
            building_width=geo_solution.width,
            building_height=geo_solution.height
        )

        orientation_wwr = self.fenster_dist.calculate_orientation_wwr(
            fenster_data=ea_data.fenster,
            wall_areas=wall_areas,
            gebaeudetyp=ea_data.gebaeudetyp
        )

        # 4. IDF erstellen
        idf = self._initialize_idf()

        # 5. Materialien & Konstruktionen (mit U-Werten)
        self._add_constructions_from_u_values(idf, ea_data)

        # 6. Simulation Control & Settings
        self._add_simulation_settings(idf, geo_solution)

        # 7. Zonen erstellen
        self._add_zones(idf, layouts)

        # 8. Surfaces erstellen
        self._add_surfaces_5_zone(idf, layouts, geo_solution, orientation_wwr)

        # 9. Schedules & Internal Loads
        self._add_schedules(idf)
        self._add_internal_loads(idf, layouts, ea_data.gebaeudetyp)

        # 10. Infiltration
        if ea_data.effective_infiltration > 0:
            self._add_infiltration(idf, layouts, ea_data.effective_infiltration)

        # 11. Output Variables
        self._add_output_variables(idf)

        # 12. Speichern falls Pfad angegeben
        if output_path:
            idf.save(str(output_path))

        return idf

    # ========================================================================
    # IDF INITIALIZATION
    # ========================================================================

    def _initialize_idf(self) -> IDF:
        """Initialisiert leeres IDF."""
        idd_file = self._get_idd_file()
        IDF.setiddname(idd_file)

        # Create minimal IDF template
        minimal_idf_content = "VERSION,\n  23.2;\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False) as f:
            f.write(minimal_idf_content)
            temp_idf_path = f.name

        idf = IDF(temp_idf_path)
        Path(temp_idf_path).unlink()

        return idf

    def _get_idd_file(self) -> str:
        """Gibt Pfad zur IDD-Datei zurück."""
        ep_path_str = self.config.energyplus.installation_path

        # Konvertiere Windows-Pfad zu WSL-Pfad falls nötig
        if ep_path_str.startswith("C:/") or ep_path_str.startswith("C:\\"):
            ep_path_str = ep_path_str.replace("C:/", "/mnt/c/").replace("C:\\", "/mnt/c/").replace("\\", "/")

        ep_path = Path(ep_path_str)
        idd_path = ep_path / "Energy+.idd"

        if not idd_path.exists():
            # Use as_posix() to ensure forward slashes in error message
            raise FileNotFoundError(
                f"IDD file not found at {idd_path.as_posix()}. "
                f"Check EnergyPlus installation path in config."
            )

        # Use as_posix() to ensure forward slashes for WSL/Linux compatibility
        return idd_path.as_posix()

    # ========================================================================
    # MATERIALS & CONSTRUCTIONS
    # ========================================================================

    def _add_constructions_from_u_values(
        self,
        idf: IDF,
        ea_data: EnergieausweisInput
    ) -> None:
        """
        Erstellt Konstruktionen basierend auf U-Werten aus Energieausweis.

        Verwendet reverse-engineering: Passt Dämmstoffdicke an U-Wert an.
        """
        # Für jetzt: Nutze Standard-Konstruktionen
        # TODO Sprint 4: U-Wert-Mapping implementieren
        add_basic_constructions(idf)

        # Platzhalter für zukünftige U-Wert-basierte Konstruktionen
        # self._create_construction_from_u_value(idf, "Wall", ea_data.u_wert_wand)
        # self._create_construction_from_u_value(idf, "Roof", ea_data.u_wert_dach)
        # ...

    # ========================================================================
    # SIMULATION SETTINGS
    # ========================================================================

    def _add_simulation_settings(
        self,
        idf: IDF,
        geo_solution: GeometrySolution
    ) -> None:
        """Fügt Simulation Control, Building, Timestep, etc. hinzu."""

        # SimulationControl
        idf.newidfobject(
            "SIMULATIONCONTROL",
            Do_Zone_Sizing_Calculation="Yes",
            Do_System_Sizing_Calculation="Yes",
            Do_Plant_Sizing_Calculation="No",
            Run_Simulation_for_Sizing_Periods="No",
            Run_Simulation_for_Weather_File_Run_Periods="Yes",
        )

        # HeatBalanceAlgorithm
        idf.newidfobject(
            "HEATBALANCEALGORITHM",
            Algorithm="ConductionTransferFunction",
        )

        # Building
        idf.newidfobject(
            "BUILDING",
            Name="5Zone_Building_From_Energieausweis",
            North_Axis=0.0,  # Orientation handled via surface coordinates
            Terrain="Suburbs",
            Loads_Convergence_Tolerance_Value=0.04,
            Temperature_Convergence_Tolerance_Value=0.4,
            Solar_Distribution="FullExterior",
            Maximum_Number_of_Warmup_Days=25,
            Minimum_Number_of_Warmup_Days=6,
        )

        # GlobalGeometryRules
        idf.newidfobject(
            "GLOBALGEOMETRYRULES",
            Starting_Vertex_Position="UpperLeftCorner",
            Vertex_Entry_Direction="Counterclockwise",
            Coordinate_System="Relative",
            Daylighting_Reference_Point_Coordinate_System="Relative",
            Rectangular_Surface_Coordinate_System="Relative",
        )

        # Timestep (4 per hour)
        idf.newidfobject("TIMESTEP", Number_of_Timesteps_per_Hour=4)

        # RunPeriod (Jahressimulation)
        idf.newidfobject(
            "RUNPERIOD",
            Name="Annual",
            Begin_Month=1,
            Begin_Day_of_Month=1,
            Begin_Year=2024,
            End_Month=12,
            End_Day_of_Month=31,
            End_Year=2024,
            Day_of_Week_for_Start_Day="Monday",
            Use_Weather_File_Holidays_and_Special_Days="Yes",
            Use_Weather_File_Daylight_Saving_Period="Yes",
            Apply_Weekend_Holiday_Rule="No",
            Use_Weather_File_Rain_Indicators="Yes",
            Use_Weather_File_Snow_Indicators="Yes",
        )

        # SizingPeriod:DesignDay (Heizen)
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

        # SizingPeriod:DesignDay (Kühlen)
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

        # Site:Location (Placeholder - Deutschland, Mitteleuropa)
        idf.newidfobject(
            "SITE:LOCATION",
            Name="Germany_Central",
            Latitude=51.0,
            Longitude=10.0,
            Time_Zone=1.0,
            Elevation=200.0,
        )

    # ========================================================================
    # ZONES
    # ========================================================================

    def _add_zones(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout]
    ) -> None:
        """Erstellt alle thermischen Zonen."""

        for floor_num, layout in layouts.items():
            for orient, zone_geom in layout.all_zones.items():
                idf.newidfobject(
                    "ZONE",
                    Name=zone_geom.name,
                    Direction_of_Relative_North=0,
                    X_Origin=zone_geom.x_origin,
                    Y_Origin=zone_geom.y_origin,
                    Z_Origin=zone_geom.z_origin,
                    Type="",
                    Multiplier=1,
                    Ceiling_Height=zone_geom.height,
                    Volume=zone_geom.volume,
                    Floor_Area="",
                    Zone_Inside_Convection_Algorithm="",
                    Zone_Outside_Convection_Algorithm="",
                    Part_of_Total_Floor_Area="Yes",
                )

                # Sizing:Zone für HVAC
                idf.newidfobject(
                    "SIZING:ZONE",
                    Zone_or_ZoneList_Name=zone_geom.name,
                    Zone_Cooling_Design_Supply_Air_Temperature_Input_Method="SupplyAirTemperature",
                    Zone_Cooling_Design_Supply_Air_Temperature=13.0,
                    Zone_Heating_Design_Supply_Air_Temperature_Input_Method="SupplyAirTemperature",
                    Zone_Heating_Design_Supply_Air_Temperature=50.0,
                    Zone_Cooling_Design_Supply_Air_Humidity_Ratio=0.008,
                    Zone_Heating_Design_Supply_Air_Humidity_Ratio=0.008,
                    Design_Specification_Outdoor_Air_Object_Name="",
                    Zone_Heating_Sizing_Factor="",
                    Zone_Cooling_Sizing_Factor="",
                    Cooling_Design_Air_Flow_Method="DesignDay",
                    Cooling_Design_Air_Flow_Rate=0.0,
                    Cooling_Minimum_Air_Flow_per_Zone_Floor_Area="",
                    Cooling_Minimum_Air_Flow="",
                    Cooling_Minimum_Air_Flow_Fraction="",
                    Heating_Design_Air_Flow_Method="DesignDay",
                    Heating_Design_Air_Flow_Rate=0.0,
                    Heating_Maximum_Air_Flow_per_Zone_Floor_Area="",
                    Heating_Maximum_Air_Flow="",
                    Heating_Maximum_Air_Flow_Fraction="",
                )

    # ========================================================================
    # SURFACES (WALLS, FLOORS, CEILINGS, WINDOWS)
    # ========================================================================

    def _add_surfaces_5_zone(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout],
        geo_solution: GeometrySolution,
        orientation_wwr: OrientationWWR
    ) -> None:
        """
        Erstellt alle Surfaces für 5-Zonen-Modell.

        Komplex wegen:
        - Außenwände (nur Perimeter)
        - Innenwände (Perimeter ↔ Kern, Perimeter ↔ Perimeter)
        - Decken/Böden (intern zwischen Stockwerken)
        - Fenster (orientierungsspezifisch)
        """

        for floor_num, layout in layouts.items():
            z_base = floor_num * geo_solution.floor_height
            z_top = z_base + geo_solution.floor_height

            # === BÖDEN ===
            self._add_floors_5_zone(idf, layout, floor_num, z_base)

            # === DECKEN ===
            self._add_ceilings_5_zone(idf, layout, floor_num, geo_solution.num_floors, z_top)

            # === AUßENWÄNDE (nur Perimeter) ===
            self._add_exterior_walls_5_zone(
                idf, layout, z_base, z_top, orientation_wwr, geo_solution
            )

            # === INNENWÄNDE (zwischen Zonen) ===
            self._add_interior_walls_5_zone(idf, layout, z_base, z_top)

    def _add_floors_5_zone(
        self,
        idf: IDF,
        layout: ZoneLayout,
        floor_num: int,
        z_base: float
    ) -> None:
        """Erstellt Böden für alle 5 Zonen."""

        is_ground_floor = (floor_num == 0)

        for orient, zone_geom in layout.all_zones.items():
            # Vertices from zone geometry (2D)
            vertices_2d = zone_geom.vertices_2d

            # Floor boundary
            if is_ground_floor:
                boundary = "Ground"
                boundary_object = ""
                construction = "FloorConstruction"
            else:
                # Inter-zone floor (connects to ceiling below)
                boundary = "Surface"
                # Find corresponding ceiling in floor below
                boundary_object = zone_geom.name.replace(f"_F{floor_num+1}", f"_F{floor_num}") + "_Ceiling"
                construction = "CeilingConstruction"

            # Create floor surface
            idf.newidfobject(
                "BUILDINGSURFACE:DETAILED",
                Name=f"{zone_geom.name}_Floor",
                Surface_Type="Floor",
                Construction_Name=construction,
                Zone_Name=zone_geom.name,
                Outside_Boundary_Condition=boundary,
                Outside_Boundary_Condition_Object=boundary_object,
                Sun_Exposure="NoSun",
                Wind_Exposure="NoWind",
                View_Factor_to_Ground="autocalculate",
                Number_of_Vertices=4,
                # Counterclockwise from top-left (floor normal points down)
                Vertex_1_Xcoordinate=vertices_2d[0][0],
                Vertex_1_Ycoordinate=vertices_2d[0][1],
                Vertex_1_Zcoordinate=z_base,
                Vertex_2_Xcoordinate=vertices_2d[1][0],
                Vertex_2_Ycoordinate=vertices_2d[1][1],
                Vertex_2_Zcoordinate=z_base,
                Vertex_3_Xcoordinate=vertices_2d[2][0],
                Vertex_3_Ycoordinate=vertices_2d[2][1],
                Vertex_3_Zcoordinate=z_base,
                Vertex_4_Xcoordinate=vertices_2d[3][0],
                Vertex_4_Ycoordinate=vertices_2d[3][1],
                Vertex_4_Zcoordinate=z_base,
            )

    def _add_ceilings_5_zone(
        self,
        idf: IDF,
        layout: ZoneLayout,
        floor_num: int,
        num_floors: int,
        z_top: float
    ) -> None:
        """Erstellt Decken/Dächer für alle 5 Zonen."""

        is_top_floor = (floor_num == num_floors - 1)

        for orient, zone_geom in layout.all_zones.items():
            vertices_2d = zone_geom.vertices_2d

            if is_top_floor:
                surface_type = "Roof"
                construction = "RoofConstruction"
                boundary = "Outdoors"
                boundary_object = ""
                sun_exposure = "SunExposed"
                wind_exposure = "WindExposed"
            else:
                surface_type = "Ceiling"
                construction = "CeilingConstruction"
                boundary = "Surface"
                # Connect to floor above
                boundary_object = zone_geom.name.replace(f"_F{floor_num+1}", f"_F{floor_num+2}") + "_Floor"
                sun_exposure = "NoSun"
                wind_exposure = "NoWind"

            # Ceiling vertices: clockwise (ceiling normal points up)
            idf.newidfobject(
                "BUILDINGSURFACE:DETAILED",
                Name=f"{zone_geom.name}_Ceiling",
                Surface_Type=surface_type,
                Construction_Name=construction,
                Zone_Name=zone_geom.name,
                Outside_Boundary_Condition=boundary,
                Outside_Boundary_Condition_Object=boundary_object,
                Sun_Exposure=sun_exposure,
                Wind_Exposure=wind_exposure,
                View_Factor_to_Ground="autocalculate",
                Number_of_Vertices=4,
                # Clockwise from bottom-left
                Vertex_1_Xcoordinate=vertices_2d[0][0],
                Vertex_1_Ycoordinate=vertices_2d[0][1],
                Vertex_1_Zcoordinate=z_top,
                Vertex_2_Xcoordinate=vertices_2d[3][0],
                Vertex_2_Ycoordinate=vertices_2d[3][1],
                Vertex_2_Zcoordinate=z_top,
                Vertex_3_Xcoordinate=vertices_2d[2][0],
                Vertex_3_Ycoordinate=vertices_2d[2][1],
                Vertex_3_Zcoordinate=z_top,
                Vertex_4_Xcoordinate=vertices_2d[1][0],
                Vertex_4_Ycoordinate=vertices_2d[1][1],
                Vertex_4_Zcoordinate=z_top,
            )

    def _add_exterior_walls_5_zone(
        self,
        idf: IDF,
        layout: ZoneLayout,
        z_base: float,
        z_top: float,
        orientation_wwr: OrientationWWR,
        geo_solution: GeometrySolution
    ) -> None:
        """
        Erstellt Außenwände mit Fenstern für Perimeter-Zonen.

        Nur Perimeter-Zonen haben Außenwände!
        """

        L = geo_solution.length
        W = geo_solution.width

        # North Perimeter - Außenwand an Y=W (Nordseite)
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_north.name,
            wall_name=f"{layout.perimeter_north.name}_Wall_North",
            vertices=[
                (0, W, z_base),
                (0, W, z_top),
                (L, W, z_top),
                (L, W, z_base),
            ],
            orientation=Orientation.NORTH,
            wwr=orientation_wwr.north
        )

        # South Perimeter - Außenwand an Y=0 (Südseite)
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_south.name,
            wall_name=f"{layout.perimeter_south.name}_Wall_South",
            vertices=[
                (L, 0, z_base),
                (L, 0, z_top),
                (0, 0, z_top),
                (0, 0, z_base),
            ],
            orientation=Orientation.SOUTH,
            wwr=orientation_wwr.south
        )

        # East Perimeter - Außenwand an X=L (Ostseite)
        # Nur der Teil, der nicht von Nord/Süd-Perimeter bedeckt ist
        p = layout.perimeter_north.width  # Perimeter depth
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_east.name,
            wall_name=f"{layout.perimeter_east.name}_Wall_East",
            vertices=[
                (L, p, z_base),
                (L, p, z_top),
                (L, W-p, z_top),
                (L, W-p, z_base),
            ],
            orientation=Orientation.EAST,
            wwr=orientation_wwr.east
        )

        # West Perimeter - Außenwand an X=0 (Westseite)
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_west.name,
            wall_name=f"{layout.perimeter_west.name}_Wall_West",
            vertices=[
                (0, W-p, z_base),
                (0, W-p, z_top),
                (0, p, z_top),
                (0, p, z_base),
            ],
            orientation=Orientation.WEST,
            wwr=orientation_wwr.west
        )

    def _add_exterior_wall(
        self,
        idf: IDF,
        zone_name: str,
        wall_name: str,
        vertices: list,
        orientation: Orientation,
        wwr: float
    ) -> None:
        """Erstellt eine Außenwand mit Fenster."""

        # Wall surface
        idf.newidfobject(
            "BUILDINGSURFACE:DETAILED",
            Name=wall_name,
            Surface_Type="Wall",
            Construction_Name="WallConstruction",
            Zone_Name=zone_name,
            Outside_Boundary_Condition="Outdoors",
            Outside_Boundary_Condition_Object="",
            Sun_Exposure="SunExposed",
            Wind_Exposure="WindExposed",
            View_Factor_to_Ground="autocalculate",
            Number_of_Vertices=4,
            Vertex_1_Xcoordinate=vertices[0][0],
            Vertex_1_Ycoordinate=vertices[0][1],
            Vertex_1_Zcoordinate=vertices[0][2],
            Vertex_2_Xcoordinate=vertices[1][0],
            Vertex_2_Ycoordinate=vertices[1][1],
            Vertex_2_Zcoordinate=vertices[1][2],
            Vertex_3_Xcoordinate=vertices[2][0],
            Vertex_3_Ycoordinate=vertices[2][1],
            Vertex_3_Zcoordinate=vertices[2][2],
            Vertex_4_Xcoordinate=vertices[3][0],
            Vertex_4_Ycoordinate=vertices[3][1],
            Vertex_4_Zcoordinate=vertices[3][2],
        )

        # Window (wenn WWR > 0)
        if wwr > 0.01:  # Mindestens 1% WWR
            self._add_window(idf, wall_name, vertices, wwr)

    def _add_window(
        self,
        idf: IDF,
        wall_name: str,
        wall_vertices: list,
        wwr: float
    ) -> None:
        """
        Erstellt Fenster auf einer Wand.

        Algorithmus aus SimpleBoxGenerator übernommen.
        """

        # Calculate wall dimensions
        v1 = wall_vertices[0]
        v2 = wall_vertices[1]
        v3 = wall_vertices[2]

        # Wall width (horizontal)
        wall_width = ((v1[0] - v3[0])**2 + (v1[1] - v3[1])**2)**0.5

        # Wall height (vertical)
        wall_height = abs(v2[2] - v1[2])

        # Window dimensions (maintaining aspect ratio)
        # sqrt(wwr) approach for proportional scaling
        scale_factor = wwr**0.5
        window_width = wall_width * scale_factor
        window_height = wall_height * scale_factor

        # Limit window height
        max_window_height = wall_height - 0.3  # 30cm from ceiling
        sill_height = 0.9  # 90cm sill
        max_available_height = wall_height - sill_height - 0.3
        window_height = min(window_height, max_available_height)

        # Center window horizontally
        h_offset = (wall_width - window_width) / 2
        v_offset = sill_height

        # Base point (bottom-left of wall)
        base_x = v1[0]
        base_y = v1[1]
        base_z = v1[2]

        # Direction vectors
        # Horizontal direction (along wall)
        h_dir_x = (v3[0] - v1[0]) / wall_width if wall_width > 0 else 0
        h_dir_y = (v3[1] - v1[1]) / wall_width if wall_width > 0 else 0

        # Window corners
        window_vertices = [
            # Bottom-left
            (
                base_x + h_offset * h_dir_x,
                base_y + h_offset * h_dir_y,
                base_z + v_offset
            ),
            # Bottom-right
            (
                base_x + (h_offset + window_width) * h_dir_x,
                base_y + (h_offset + window_width) * h_dir_y,
                base_z + v_offset
            ),
            # Top-right
            (
                base_x + (h_offset + window_width) * h_dir_x,
                base_y + (h_offset + window_width) * h_dir_y,
                base_z + v_offset + window_height
            ),
            # Top-left
            (
                base_x + h_offset * h_dir_x,
                base_y + h_offset * h_dir_y,
                base_z + v_offset + window_height
            ),
        ]

        # Create window
        idf.newidfobject(
            "FENESTRATIONSURFACE:DETAILED",
            Name=f"{wall_name}_Window",
            Surface_Type="Window",
            Construction_Name="WindowConstruction",
            Building_Surface_Name=wall_name,
            Outside_Boundary_Condition_Object="",
            View_Factor_to_Ground="autocalculate",
            Frame_and_Divider_Name="",
            Multiplier=1,
            Number_of_Vertices=4,
            Vertex_1_Xcoordinate=window_vertices[0][0],
            Vertex_1_Ycoordinate=window_vertices[0][1],
            Vertex_1_Zcoordinate=window_vertices[0][2],
            Vertex_2_Xcoordinate=window_vertices[1][0],
            Vertex_2_Ycoordinate=window_vertices[1][1],
            Vertex_2_Zcoordinate=window_vertices[1][2],
            Vertex_3_Xcoordinate=window_vertices[2][0],
            Vertex_3_Ycoordinate=window_vertices[2][1],
            Vertex_3_Zcoordinate=window_vertices[2][2],
            Vertex_4_Xcoordinate=window_vertices[3][0],
            Vertex_4_Ycoordinate=window_vertices[3][1],
            Vertex_4_Zcoordinate=window_vertices[3][2],
        )

    def _add_interior_walls_5_zone(
        self,
        idf: IDF,
        layout: ZoneLayout,
        z_base: float,
        z_top: float
    ) -> None:
        """
        Erstellt Innenwände zwischen Zonen.

        Inter-Zone-Wände:
        - Perimeter North ↔ Core
        - Perimeter East ↔ Core
        - Perimeter South ↔ Core
        - Perimeter West ↔ Core
        - Perimeter North ↔ East (Ecke)
        - Perimeter North ↔ West (Ecke)
        - Perimeter South ↔ East (Ecke)
        - Perimeter South ↔ West (Ecke)
        """

        p_north = layout.perimeter_north
        p_east = layout.perimeter_east
        p_south = layout.perimeter_south
        p_west = layout.perimeter_west
        core = layout.core

        # === Perimeter ↔ Core ===

        # North-Core
        self._add_interior_wall_pair(
            idf,
            zone_a=p_north.name,
            zone_b=core.name,
            wall_a_name=f"{p_north.name}_Wall_To_Core",
            wall_b_name=f"{core.name}_Wall_To_North",
            vertices_a=[
                (core.x_origin, core.y_origin + core.width, z_base),
                (core.x_origin, core.y_origin + core.width, z_top),
                (core.x_origin + core.length, core.y_origin + core.width, z_top),
                (core.x_origin + core.length, core.y_origin + core.width, z_base),
            ]
        )

        # South-Core
        self._add_interior_wall_pair(
            idf,
            zone_a=p_south.name,
            zone_b=core.name,
            wall_a_name=f"{p_south.name}_Wall_To_Core",
            wall_b_name=f"{core.name}_Wall_To_South",
            vertices_a=[
                (core.x_origin + core.length, core.y_origin, z_base),
                (core.x_origin + core.length, core.y_origin, z_top),
                (core.x_origin, core.y_origin, z_top),
                (core.x_origin, core.y_origin, z_base),
            ]
        )

        # East-Core
        self._add_interior_wall_pair(
            idf,
            zone_a=p_east.name,
            zone_b=core.name,
            wall_a_name=f"{p_east.name}_Wall_To_Core",
            wall_b_name=f"{core.name}_Wall_To_East",
            vertices_a=[
                (core.x_origin + core.length, core.y_origin, z_base),
                (core.x_origin + core.length, core.y_origin, z_top),
                (core.x_origin + core.length, core.y_origin + core.width, z_top),
                (core.x_origin + core.length, core.y_origin + core.width, z_base),
            ]
        )

        # West-Core
        self._add_interior_wall_pair(
            idf,
            zone_a=p_west.name,
            zone_b=core.name,
            wall_a_name=f"{p_west.name}_Wall_To_Core",
            wall_b_name=f"{core.name}_Wall_To_West",
            vertices_a=[
                (core.x_origin, core.y_origin + core.width, z_base),
                (core.x_origin, core.y_origin + core.width, z_top),
                (core.x_origin, core.y_origin, z_top),
                (core.x_origin, core.y_origin, z_base),
            ]
        )

        # === Perimeter ↔ Perimeter (Ecken) ===

        p_depth = p_north.width  # Perimeter depth

        # North-East Ecke
        self._add_interior_wall_pair(
            idf,
            zone_a=p_north.name,
            zone_b=p_east.name,
            wall_a_name=f"{p_north.name}_Wall_To_East",
            wall_b_name=f"{p_east.name}_Wall_To_North",
            vertices_a=[
                (core.x_origin + core.length, core.y_origin + core.width, z_base),
                (core.x_origin + core.length, core.y_origin + core.width, z_top),
                (core.x_origin + core.length, core.y_origin + core.width + p_depth, z_top),
                (core.x_origin + core.length, core.y_origin + core.width + p_depth, z_base),
            ]
        )

        # North-West Ecke
        self._add_interior_wall_pair(
            idf,
            zone_a=p_north.name,
            zone_b=p_west.name,
            wall_a_name=f"{p_north.name}_Wall_To_West",
            wall_b_name=f"{p_west.name}_Wall_To_North",
            vertices_a=[
                (core.x_origin, core.y_origin + core.width + p_depth, z_base),
                (core.x_origin, core.y_origin + core.width + p_depth, z_top),
                (core.x_origin, core.y_origin + core.width, z_top),
                (core.x_origin, core.y_origin + core.width, z_base),
            ]
        )

        # South-East Ecke
        self._add_interior_wall_pair(
            idf,
            zone_a=p_south.name,
            zone_b=p_east.name,
            wall_a_name=f"{p_south.name}_Wall_To_East",
            wall_b_name=f"{p_east.name}_Wall_To_South",
            vertices_a=[
                (core.x_origin + core.length, core.y_origin, z_base),
                (core.x_origin + core.length, core.y_origin, z_top),
                (core.x_origin + core.length, core.y_origin - p_depth, z_top),
                (core.x_origin + core.length, core.y_origin - p_depth, z_base),
            ]
        )

        # South-West Ecke
        self._add_interior_wall_pair(
            idf,
            zone_a=p_south.name,
            zone_b=p_west.name,
            wall_a_name=f"{p_south.name}_Wall_To_West",
            wall_b_name=f"{p_west.name}_Wall_To_South",
            vertices_a=[
                (core.x_origin, core.y_origin - p_depth, z_base),
                (core.x_origin, core.y_origin - p_depth, z_top),
                (core.x_origin, core.y_origin, z_top),
                (core.x_origin, core.y_origin, z_base),
            ]
        )

    def _add_interior_wall_pair(
        self,
        idf: IDF,
        zone_a: str,
        zone_b: str,
        wall_a_name: str,
        wall_b_name: str,
        vertices_a: list
    ) -> None:
        """
        Erstellt Paar von Inter-Zone-Wänden (A→B und B→A).

        Args:
            zone_a: Zone A Name
            zone_b: Zone B Name
            wall_a_name: Name der Wand in Zone A
            wall_b_name: Name der Wand in Zone B
            vertices_a: Vertices von Wand A (counterclockwise)
        """

        # Wall A (in Zone A, sieht nach Zone B)
        idf.newidfobject(
            "BUILDINGSURFACE:DETAILED",
            Name=wall_a_name,
            Surface_Type="Wall",
            Construction_Name="CeilingConstruction",  # Interior wall
            Zone_Name=zone_a,
            Outside_Boundary_Condition="Surface",
            Outside_Boundary_Condition_Object=wall_b_name,
            Sun_Exposure="NoSun",
            Wind_Exposure="NoWind",
            View_Factor_to_Ground="autocalculate",
            Number_of_Vertices=4,
            Vertex_1_Xcoordinate=vertices_a[0][0],
            Vertex_1_Ycoordinate=vertices_a[0][1],
            Vertex_1_Zcoordinate=vertices_a[0][2],
            Vertex_2_Xcoordinate=vertices_a[1][0],
            Vertex_2_Ycoordinate=vertices_a[1][1],
            Vertex_2_Zcoordinate=vertices_a[1][2],
            Vertex_3_Xcoordinate=vertices_a[2][0],
            Vertex_3_Ycoordinate=vertices_a[2][1],
            Vertex_3_Zcoordinate=vertices_a[2][2],
            Vertex_4_Xcoordinate=vertices_a[3][0],
            Vertex_4_Ycoordinate=vertices_a[3][1],
            Vertex_4_Zcoordinate=vertices_a[3][2],
        )

        # Wall B (in Zone B, sieht nach Zone A) - REVERSED vertices
        vertices_b = vertices_a[::-1]  # Umgekehrte Reihenfolge

        idf.newidfobject(
            "BUILDINGSURFACE:DETAILED",
            Name=wall_b_name,
            Surface_Type="Wall",
            Construction_Name="CeilingConstruction",
            Zone_Name=zone_b,
            Outside_Boundary_Condition="Surface",
            Outside_Boundary_Condition_Object=wall_a_name,
            Sun_Exposure="NoSun",
            Wind_Exposure="NoWind",
            View_Factor_to_Ground="autocalculate",
            Number_of_Vertices=4,
            Vertex_1_Xcoordinate=vertices_b[0][0],
            Vertex_1_Ycoordinate=vertices_b[0][1],
            Vertex_1_Zcoordinate=vertices_b[0][2],
            Vertex_2_Xcoordinate=vertices_b[1][0],
            Vertex_2_Ycoordinate=vertices_b[1][1],
            Vertex_2_Zcoordinate=vertices_b[1][2],
            Vertex_3_Xcoordinate=vertices_b[2][0],
            Vertex_3_Ycoordinate=vertices_b[2][1],
            Vertex_3_Zcoordinate=vertices_b[2][2],
            Vertex_4_Xcoordinate=vertices_b[3][0],
            Vertex_4_Ycoordinate=vertices_b[3][1],
            Vertex_4_Zcoordinate=vertices_b[3][2],
        )

    # ========================================================================
    # SCHEDULES & INTERNAL LOADS
    # ========================================================================

    def _add_schedules(self, idf: IDF) -> None:
        """Fügt Standard-Schedules hinzu."""

        # Always On
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="AlwaysOn",
            Schedule_Type_Limits_Name="",
            Hourly_Value=1.0,
        )

        # Occupancy (Werktags 8-18 Uhr)
        idf.newidfobject(
            "SCHEDULE:COMPACT",
            Name="OccupancySchedule",
            Schedule_Type_Limits_Name="",
            Field_1="Through: 12/31",
            Field_2="For: Weekdays",
            Field_3="Until: 8:00",
            Field_4="0.0",
            Field_5="Until: 18:00",
            Field_6="1.0",
            Field_7="Until: 24:00",
            Field_8="0.0",
            Field_9="For: Weekend Holidays",
            Field_10="Until: 24:00",
            Field_11="0.0",
        )

        # Activity Level (120 W/Person)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="ActivityLevel",
            Schedule_Type_Limits_Name="",
            Hourly_Value=120.0,
        )

        # Thermostat Schedules
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="HeatingSetpoint",
            Schedule_Type_Limits_Name="",
            Hourly_Value=20.0,
        )

        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="CoolingSetpoint",
            Schedule_Type_Limits_Name="",
            Hourly_Value=24.0,
        )

        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="ThermostatControlType",
            Schedule_Type_Limits_Name="",
            Hourly_Value=4,  # 4 = DualSetpoint
        )

    def _add_internal_loads(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout],
        gebaeudetyp
    ) -> None:
        """Fügt Internal Loads (People, Lights, Equipment) hinzu."""

        # Standard-Werte (können später nach Gebäudetyp differenziert werden)
        people_per_m2 = 0.05  # Personen pro m²
        lights_w_per_m2 = 10.0  # W/m²
        equipment_w_per_m2 = 5.0  # W/m²

        for floor_num, layout in layouts.items():
            for orient, zone_geom in layout.all_zones.items():
                zone_name = zone_geom.name

                # People
                idf.newidfobject(
                    "PEOPLE",
                    Name=f"{zone_name}_People",
                    Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
                    Number_of_People_Schedule_Name="OccupancySchedule",
                    Number_of_People_Calculation_Method="People/Area",
                    Number_of_People="",
                    People_per_Floor_Area=people_per_m2,
                    Floor_Area_per_Person="",
                    Fraction_Radiant=0.3,
                    Sensible_Heat_Fraction="autocalculate",
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
                    Watts_per_Floor_Area=lights_w_per_m2,
                    Watts_per_Person="",
                    Return_Air_Fraction=0.0,
                    Fraction_Radiant=0.4,
                    Fraction_Visible=0.2,
                    Fraction_Replaceable=1.0,
                )

                # Electric Equipment
                idf.newidfobject(
                    "ELECTRICEQUIPMENT",
                    Name=f"{zone_name}_Equipment",
                    Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
                    Schedule_Name="OccupancySchedule",
                    Design_Level_Calculation_Method="Watts/Area",
                    Design_Level="",
                    Watts_per_Floor_Area=equipment_w_per_m2,
                    Watts_per_Person="",
                    Fraction_Latent=0.0,
                    Fraction_Radiant=0.3,
                    Fraction_Lost=0.0,
                )

                # Thermostat
                idf.newidfobject(
                    "HVACTEMPLATE:THERMOSTAT",
                    Name=f"{zone_name}_Thermostat",
                    Heating_Setpoint_Schedule_Name="HeatingSetpoint",
                    Constant_Heating_Setpoint="",
                    Cooling_Setpoint_Schedule_Name="CoolingSetpoint",
                    Constant_Cooling_Setpoint="",
                )

    def _add_infiltration(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout],
        infiltration_ach: float
    ) -> None:
        """Fügt Infiltration zu allen Zonen hinzu."""

        for floor_num, layout in layouts.items():
            for orient, zone_geom in layout.all_zones.items():
                idf.newidfobject(
                    "ZONEINFILTRATION:DESIGNFLOWRATE",
                    Name=f"{zone_geom.name}_Infiltration",
                    Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_geom.name,
                    Schedule_Name="AlwaysOn",
                    Design_Flow_Rate_Calculation_Method="AirChanges/Hour",
                    Design_Flow_Rate="",
                    Flow_Rate_per_Floor_Area="",
                    Flow_Rate_per_Exterior_Surface_Area="",
                    Air_Changes_per_Hour=infiltration_ach,
                    Constant_Term_Coefficient=1.0,
                    Temperature_Term_Coefficient=0.0,
                    Velocity_Term_Coefficient=0.0,
                    Velocity_Squared_Term_Coefficient=0.0,
                )

    # ========================================================================
    # OUTPUT VARIABLES
    # ========================================================================

    def _add_output_variables(self, idf: IDF) -> None:
        """Fügt Output Variables hinzu."""

        outputs = [
            ("Zone Mean Air Temperature", "Hourly"),
            ("Zone Total Internal Latent Gain Rate", "Hourly"),
            ("Zone Total Internal Total Heating Rate", "Hourly"),
            ("Heating:DistrictHeating", "Hourly"),
            ("Cooling:DistrictCooling", "Hourly"),
        ]

        for var_name, freq in outputs:
            idf.newidfobject(
                "OUTPUT:VARIABLE",
                Key_Value="*",
                Variable_Name=var_name,
                Reporting_Frequency=freq,
            )

        # Output:SQLite
        idf.newidfobject(
            "OUTPUT:SQLITE",
            Option_Type="SimpleAndTabular",
        )
