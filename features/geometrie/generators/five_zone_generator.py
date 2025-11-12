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
from features.internal_loads.native_loads import NativeInternalLoadsManager


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
        schedules = self._add_schedules(idf, building_type=ea_data.gebaeudetyp)
        self._add_internal_loads(idf, layouts, ea_data.gebaeudetyp, schedules)

        # 10. Infiltration
        if ea_data.effective_infiltration > 0:
            self._add_infiltration(idf, layouts, ea_data.effective_infiltration)

        # 10.5 HVAC System (IdealLoads)
        self._add_hvac_system(idf)

        # 11. Output Variables
        self._add_output_variables(idf)

        # 12. Speichern falls Pfad angegeben
        if output_path:
            # CRITICAL: Sammle Boundary Objects VOR dem Save (eppy korrumpiert im Save!)
            boundary_map = self._collect_boundary_map(idf)
            idf.save(str(output_path))
            # Fix eppy bug that overwrites Outside_Boundary_Condition_Object
            self._fix_eppy_boundary_objects(boundary_map, output_path)

        return idf

    def create_from_explicit_dimensions(
        self,
        building_length: float,
        building_width: float,
        floor_height: float,
        num_floors: int,
        ea_data: EnergieausweisInput,
        output_path: Optional[Path] = None
    ) -> IDF:
        """
        Erstellt 5-Zonen-IDF mit expliziten Dimensionen (umgeht GeometrySolver).

        Diese Methode ist nützlich für Tests oder wenn die Gebäudedimensionen
        bereits bekannt sind und nicht aus Energieausweis-Daten berechnet werden sollen.

        Args:
            building_length: Gebäudelänge in Metern
            building_width: Gebäudebreite in Metern
            floor_height: Geschosshöhe in Metern
            num_floors: Anzahl Geschosse
            ea_data: Energieausweis-Daten (für U-Werte, WWR, etc.)
            output_path: Pfad zum Speichern des IDF (optional)

        Returns:
            IDF-Objekt
        """
        # Create GeometrySolution manually (bypass solver)
        from features.geometrie.utils.geometry_solver import SolutionMethod
        geo_solution = GeometrySolution(
            length=building_length,
            width=building_width,
            height=floor_height * num_floors,
            num_floors=num_floors,
            confidence=1.0,  # Explicit dimensions = highest confidence
            method=SolutionMethod.EXACT,
            warnings=[]
        )

        # 2. Multi-Floor Zonen-Layouts erstellen
        wwr_avg = ea_data.fenster.window_wall_ratio or 0.3
        layouts = self.perimeter_calc.create_multi_floor_layout(
            building_length=building_length,
            building_width=building_width,
            floor_height=floor_height,
            num_floors=num_floors,
            wwr=wwr_avg
        )

        # 3. Fensterverteilung berechnen
        wall_areas = self.fenster_dist.estimate_wall_areas_from_geometry(
            building_length=building_length,
            building_width=building_width,
            building_height=floor_height * num_floors
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
        schedules = self._add_schedules(idf, building_type=ea_data.gebaeudetyp)
        self._add_internal_loads(idf, layouts, ea_data.gebaeudetyp, schedules)

        # 10. Infiltration
        if ea_data.effective_infiltration > 0:
            self._add_infiltration(idf, layouts, ea_data.effective_infiltration)

        # 10.5 HVAC System (IdealLoads)
        self._add_hvac_system(idf)

        # 11. Output Variables
        self._add_output_variables(idf)

        # 12. Speichern falls Pfad angegeben
        if output_path:
            # CRITICAL: Sammle Boundary Objects VOR dem Save (eppy korrumpiert im Save!)
            boundary_map = self._collect_boundary_map(idf)
            idf.save(str(output_path))
            # Fix eppy bug that overwrites Outside_Boundary_Condition_Object
            self._fix_eppy_boundary_objects(boundary_map, output_path)

        return idf

    def _collect_boundary_map(self, idf: IDF) -> dict:
        """
        Sammelt Boundary Objects VOR dem eppy Save (da save diese korrupt!).

        Returns:
            dict: {surface_name: correct_boundary_object_name}
        """
        boundary_map = {}
        for surf in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
            if surf.Outside_Boundary_Condition == "Surface":
                boundary_map[surf.Name] = surf.Outside_Boundary_Condition_Object
                # DEBUG
                if "Perimeter_North_F1_Wall_To_Core" in surf.Name or "Core_F1_Wall_To_North" in surf.Name:
                    print(f"  DEBUG boundary_map: {surf.Name} → {surf.Outside_Boundary_Condition_Object}")
        return boundary_map

    def _fix_eppy_boundary_objects(self, boundary_map: dict, output_path: Path) -> None:
        """
        WORKAROUND für eppy Bug: Outside_Boundary_Condition_Object wird beim Save überschrieben.

        Eppy setzt fälschlicherweise Outside_Boundary_Condition_Object = Name (Self-Reference).
        Diese Methode korrigiert das IDF-File nach dem Save.

        Args:
            boundary_map: Pre-collected boundary objects BEFORE save
            output_path: Path to the saved IDF file
        """
        # 1. Lese gespeicherte IDF-Datei
        with open(output_path, 'r') as f:
            idf_content = f.read()

        # 2. Korrigiere jede falsche Self-Reference mit den vorher gesammelten Werten
        # WICHTIG: Wir müssen jeden Surface-Block einzeln finden und NUR dessen Boundary-Zeile ersetzen!
        # Nicht nach dem Boundary-Wert suchen (das führt zu Interferenzen zwischen Paaren)!
        corrections = 0
        import re

        for surf_name, correct_boundary in boundary_map.items():
            # Pattern: Finde den BUILDINGSURFACE:DETAILED Block für diese spezifische Surface
            # und ersetze NUR die Boundary Object Zeile IN DIESEM Block
            # Format:
            # BUILDINGSURFACE:DETAILED,
            #     SurfaceName,    !- Name
            #     Wall,           !- Surface Type
            #     ...
            #     Surface,        !- Outside Boundary Condition
            #     <WRONG_VALUE>,  !- Outside Boundary Condition Object  <- DIESE Zeile ersetzen!

            pattern = (
                rf'(BUILDINGSURFACE:DETAILED,\s+'  # Start of block
                rf'{re.escape(surf_name)},\s+!- Name\s+'  # This surface's name
                rf'.*?'  # Any lines in between (non-greedy)
                rf'Surface,\s+!- Outside Boundary Condition\s+'  # The "Surface" boundary condition
                rf')(\S+)(,\s+!- Outside Boundary Condition Object)'  # Capture old value
            )

            # Replacement: Keep everything before, replace value, keep comment
            replacement = rf'\1{correct_boundary}\3'

            new_content, count = re.subn(pattern, replacement, idf_content, flags=re.DOTALL)
            if count > 0:
                idf_content = new_content
                corrections += count
                # DEBUG
                print(f"  DEBUG fixed: {surf_name[:40]:40} → {correct_boundary[:40]:40} (blocks={count})")

        # 3. Schreibe korrigiertes IDF zurück
        if corrections > 0:
            print(f"  DEBUG: Writing corrected IDF to {output_path}")
            print(f"  DEBUG: File size before: {output_path.stat().st_size if output_path.exists() else 0} bytes")
            with open(output_path, 'w') as f:
                f.write(idf_content)
            print(f"  DEBUG: File size after: {output_path.stat().st_size} bytes")

            # DEBUG: Verify the fix was actually written
            with open(output_path, 'r') as f:
                verify_content = f.read()
                # Simple string search for specific corrected values
                if "Core_F1_Wall_To_North," in verify_content:
                    print(f"  ✅ VERIFY: Found 'Core_F1_Wall_To_North' in file")
                else:
                    print(f"  ❌ VERIFY: 'Core_F1_Wall_To_North' NOT found in file!")

                # Check what's actually on the Outside Boundary Condition Object lines
                import re
                # Find lines specifically after "Surface," (Outside Boundary Condition)
                blocks = re.findall(
                    r'(^\s+\S+,\s+!- Name\n(?:.*\n){5}^\s+Surface,\s+!- Outside Boundary Condition\n^\s+(\S+),\s+!- Outside Boundary Condition Object)',
                    verify_content,
                    flags=re.MULTILINE
                )
                print(f"  DEBUG VERIFY: Found {len(blocks)} surface-type blocks")
                for i, (block, boundary) in enumerate(blocks[:3]):
                    print(f"    Block {i+1} boundary: {boundary}")

            print(f"  🔧 Fixed {corrections} eppy boundary object bugs")
        else:
            print(f"  No eppy boundary object bugs found (this is unexpected!)")

    # ========================================================================
    # IDF INITIALIZATION
    # ========================================================================

    def _initialize_idf(self) -> IDF:
        """Initialisiert leeres IDF."""
        idd_file = self._get_idd_file()
        IDF.setiddname(idd_file)

        # Create minimal IDF template with correct version (25.1 for EnergyPlus V25-1-0)
        minimal_idf_content = "VERSION,\n  25.1;\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False) as f:
            f.write(minimal_idf_content)
            temp_idf_path = f.name

        idf = IDF(temp_idf_path)
        Path(temp_idf_path).unlink()

        # CRITICAL: Add GlobalGeometryRules IMMEDIATELY after VERSION
        # Must be before any geometry objects (surfaces, zones, etc.)
        # Using 3 fields to match working EnergyPlus examples
        idf.newidfobject(
            "GLOBALGEOMETRYRULES",
            Starting_Vertex_Position="UpperLeftCorner",
            Vertex_Entry_Direction="Counterclockwise",
            Coordinate_System="Relative",
        )

        return idf

    def _get_idd_file(self) -> str:
        """Gibt Pfad zur IDD-Datei zurück."""
        import os
        import platform

        ep_path_str = self.config.energyplus.installation_path

        # Erkenne ob wir in WSL laufen
        cwd = os.getcwd()
        running_in_wsl = cwd.startswith("/mnt/") or (platform.system() == "Linux" and os.path.exists("/mnt/c"))

        if running_in_wsl:
            # Wir sind in WSL: Konvertiere C:/ zu /mnt/c/
            if ep_path_str.startswith("C:/") or ep_path_str.startswith("C:\\"):
                ep_path_str = ep_path_str.replace("C:/", "/mnt/c/").replace("C:\\", "/mnt/c/").replace("\\", "/")
        else:
            # Wir sind in Windows: Konvertiere /mnt/c/ zu C:/
            if ep_path_str.startswith("/mnt/c/"):
                ep_path_str = ep_path_str.replace("/mnt/c/", "C:/")
            elif ep_path_str.startswith("/mnt/"):
                # Andere Laufwerke: /mnt/d/ -> D:/, etc.
                parts = ep_path_str[5:].split("/", 1)  # Skip "/mnt/"
                if len(parts) >= 1:
                    drive = parts[0].upper()
                    rest = parts[1] if len(parts) > 1 else ""
                    ep_path_str = f"{drive}:/{rest}"

        ep_path = Path(ep_path_str)
        idd_path = ep_path / "Energy+.idd"

        if not idd_path.exists():
            raise FileNotFoundError(
                f"IDD file not found at {idd_path}. "
                f"Check EnergyPlus installation path in config.\n"
                f"Debug Info:\n"
                f"  Running in WSL: {running_in_wsl}\n"
                f"  Platform: {platform.system()}\n"
                f"  Working directory: {cwd}\n"
                f"  Original config path: {self.config.energyplus.installation_path}\n"
                f"  Final path: {ep_path_str}\n"
                f"  IDD path: {idd_path}\n"
                f"  Path exists: {idd_path.exists()}"
            )

        return str(idd_path)

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
        # NOTE: Zone/System Sizing auf No, da IdealLoads verwendet wird (braucht kein Sizing)
        # Nur Annual Simulation (Weather File Run Periods) wird ausgeführt
        idf.newidfobject(
            "SIMULATIONCONTROL",
            Do_Zone_Sizing_Calculation="No",  # Disabled: IdealLoads braucht kein Sizing
            Do_System_Sizing_Calculation="No",  # Disabled: IdealLoads braucht kein Sizing
            Do_Plant_Sizing_Calculation="No",
            Run_Simulation_for_Sizing_Periods="No",
            Run_Simulation_for_Weather_File_Run_Periods="Yes",  # ENABLED: Annual Simulation!
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

        # NOTE: GlobalGeometryRules is now added in _initialize_idf()
        # immediately after VERSION (critical for proper geometry parsing)

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

                # HINWEIS: SIZING:ZONE nicht mehr erstellt, da Sizing deaktiviert ist
                # (IdealLoads braucht kein Sizing, Annual Simulation läuft ohne)

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

            # CRITICAL: Floor vertices must be REVERSED [3,2,1,0] for downward normal
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
                # Floor vertices: REVERSED [3,2,1,0] so normal points DOWN
                Vertex_1_Xcoordinate=vertices_2d[3][0],
                Vertex_1_Ycoordinate=vertices_2d[3][1],
                Vertex_1_Zcoordinate=z_base,
                Vertex_2_Xcoordinate=vertices_2d[2][0],
                Vertex_2_Ycoordinate=vertices_2d[2][1],
                Vertex_2_Zcoordinate=z_base,
                Vertex_3_Xcoordinate=vertices_2d[1][0],
                Vertex_3_Ycoordinate=vertices_2d[1][1],
                Vertex_3_Zcoordinate=z_base,
                Vertex_4_Xcoordinate=vertices_2d[0][0],
                Vertex_4_Ycoordinate=vertices_2d[0][1],
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

            # CRITICAL: Ceiling/Roof normal must point UP [0,1,2,3] for upward normal
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
                # Ceiling vertices: NORMAL [0,1,2,3] so normal points UP
                Vertex_1_Xcoordinate=vertices_2d[0][0],
                Vertex_1_Ycoordinate=vertices_2d[0][1],
                Vertex_1_Zcoordinate=z_top,
                Vertex_2_Xcoordinate=vertices_2d[1][0],
                Vertex_2_Ycoordinate=vertices_2d[1][1],
                Vertex_2_Zcoordinate=z_top,
                Vertex_3_Xcoordinate=vertices_2d[2][0],
                Vertex_3_Ycoordinate=vertices_2d[2][1],
                Vertex_3_Zcoordinate=z_top,
                Vertex_4_Xcoordinate=vertices_2d[3][0],
                Vertex_4_Ycoordinate=vertices_2d[3][1],
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
        # FIXED: Counter-clockwise vertex order (was clockwise!)
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_north.name,
            wall_name=f"{layout.perimeter_north.name}_Wall_North",
            vertices=[
                (0, W, z_base),    # V1: Bottom-Left
                (L, W, z_base),    # V2: Bottom-Right (counter-clockwise!)
                (L, W, z_top),     # V3: Top-Right
                (0, W, z_top),     # V4: Top-Left
            ],
            orientation=Orientation.NORTH,
            wwr=orientation_wwr.north
        )

        # South Perimeter - Außenwand an Y=0 (Südseite)
        # FIXED: Counter-clockwise vertex order
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_south.name,
            wall_name=f"{layout.perimeter_south.name}_Wall_South",
            vertices=[
                (L, 0, z_base),    # V1: Bottom-Right (from inside view)
                (0, 0, z_base),    # V2: Bottom-Left (counter-clockwise!)
                (0, 0, z_top),     # V3: Top-Left
                (L, 0, z_top),     # V4: Top-Right
            ],
            orientation=Orientation.SOUTH,
            wwr=orientation_wwr.south
        )

        # East Perimeter - Außenwand an X=L (Ostseite)
        # Nur der Teil, der nicht von Nord/Süd-Perimeter bedeckt ist
        # FIXED: Counter-clockwise vertex order
        p = layout.perimeter_north.width  # Perimeter depth
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_east.name,
            wall_name=f"{layout.perimeter_east.name}_Wall_East",
            vertices=[
                (L, p, z_base),      # V1: Bottom (South end)
                (L, W-p, z_base),    # V2: Bottom (North end) - counter-clockwise!
                (L, W-p, z_top),     # V3: Top (North end)
                (L, p, z_top),       # V4: Top (South end)
            ],
            orientation=Orientation.EAST,
            wwr=orientation_wwr.east
        )

        # West Perimeter - Außenwand an X=0 (Westseite)
        # FIXED: Counter-clockwise vertex order
        self._add_exterior_wall(
            idf,
            zone_name=layout.perimeter_west.name,
            wall_name=f"{layout.perimeter_west.name}_Wall_West",
            vertices=[
                (0, W-p, z_base),    # V1: Bottom (North end)
                (0, p, z_base),      # V2: Bottom (South end) - counter-clockwise!
                (0, p, z_top),       # V3: Top (South end)
                (0, W-p, z_top),     # V4: Top (North end)
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
        v4 = wall_vertices[3]

        # Wall width (horizontal)
        wall_width = ((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)**0.5

        # Wall height (vertical)
        # FIXED: For counter-clockwise walls, v1 and v2 are at same Z (bottom)
        # Height is from v1 (bottom) to v4 (top), NOT v1 to v2!
        wall_height = abs(v4[2] - v1[2])

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
        # FIXED: For counter-clockwise, horizontal is from v1 (bottom-left) to v2 (bottom-right)
        h_dir_x = (v2[0] - v1[0]) / wall_width if wall_width > 0 else 0
        h_dir_y = (v2[1] - v1[1]) / wall_width if wall_width > 0 else 0

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
            Construction_Name="WallConstruction",  # Interior wall - FIXED: was CeilingConstruction
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
            Construction_Name="WallConstruction",  # FIXED: was CeilingConstruction
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

    def _add_schedules(self, idf: IDF, building_type: str = "office") -> Dict[str, str]:
        """Fügt Standard-Schedules hinzu via NativeInternalLoadsManager.

        Args:
            idf: IDF object
            building_type: Building type (office, residential)

        Returns:
            Dict mapping schedule type to schedule name
        """
        # Use proven native approach for schedules
        manager = NativeInternalLoadsManager()
        schedules = manager.add_schedules(idf, building_type)

        # Add legacy schedule names for backward compatibility
        # Map new schedule names to old expected names
        # OccupancySchedule -> Always_On_Occupancy
        # ActivityLevel -> Activity_Level_Schedule

        return schedules

    def _add_internal_loads(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout],
        gebaeudetyp: str,
        schedules: Dict[str, str]
    ) -> None:
        """Fügt Internal Loads (People, Lights, Equipment) hinzu.

        Uses NativeInternalLoadsManager for proven, stable implementation.

        Args:
            idf: IDF object
            layouts: Zone layouts per floor
            gebaeudetyp: Building type (Wohngebäude, Nichtwohngebäude)
            schedules: Schedule names dict from _add_schedules()
        """
        # Map Energieausweis types to internal types
        building_type_map = {
            "Wohngebäude": "residential",
            "Nichtwohngebäude": "office",
        }
        building_type = building_type_map.get(gebaeudetyp, "office")

        # Use proven NativeInternalLoadsManager
        manager = NativeInternalLoadsManager()

        # Collect all zone names and areas
        zone_names = []
        zone_areas = {}

        for floor_num, layout in layouts.items():
            for orient, zone_geom in layout.all_zones.items():
                zone_name = zone_geom.name
                zone_names.append(zone_name)
                # Calculate zone area from geometry
                zone_areas[zone_name] = zone_geom.floor_area

        # Add all internal loads using proven native approach
        for zone_name in zone_names:
            area = zone_areas[zone_name]

            manager.add_people_to_zone(
                idf, zone_name, area, building_type,
                schedules["occupancy"], schedules["activity"]
            )
            manager.add_lights_to_zone(
                idf, zone_name, area, building_type,
                schedules["lights"]
            )
            manager.add_equipment_to_zone(
                idf, zone_name, area, building_type,
                schedules["equipment"]
            )

                # HINWEIS: HVACTEMPLATE:THERMOSTAT wurde entfernt, weil:
                # 1. create_building_with_hvac() fügt native ZONEHVAC-Objekte hinzu (kein HVACTemplate)
                # 2. HVACTEMPLATE:THERMOSTAT alleine ist nutzlos ohne HVACTEMPLATE:ZONE:*
                # 3. EnergyPlus beschwert sich über unvollständige HVACTemplate-Objekte

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
    # HVAC SYSTEM
    # ========================================================================

    def _add_hvac_system(self, idf: IDF) -> None:
        """Fügt IdealLoads HVAC System zu allen Zonen hinzu."""
        from features.hvac.ideal_loads import HVACTemplateManager

        manager = HVACTemplateManager()
        # Apply ideal loads HVAC template to all zones
        # Note: This modifies the IDF in-place, no need to reassign
        manager.apply_template_simple(idf, template_name="ideal_loads")

    # ========================================================================
    # OUTPUT VARIABLES
    # ========================================================================

    def _add_output_variables(self, idf: IDF) -> None:
        """Fügt Output Variables hinzu - für IdealLoads HVAC System."""

        # Output-Variablen für IdealLoads HVAC
        outputs = [
            ("Zone Mean Air Temperature", "Hourly"),
            ("Zone Air System Sensible Heating Energy", "Hourly"),
            ("Zone Air System Sensible Cooling Energy", "Hourly"),
            ("Zone Ideal Loads Zone Total Heating Energy", "Hourly"),
            ("Zone Ideal Loads Zone Total Cooling Energy", "Hourly"),
            ("Zone Ideal Loads Supply Air Total Heating Energy", "Hourly"),
            ("Zone Ideal Loads Supply Air Total Cooling Energy", "Hourly"),
        ]

        for var_name, freq in outputs:
            idf.newidfobject(
                "OUTPUT:VARIABLE",
                Key_Value="*",
                Variable_Name=var_name,
                Reporting_Frequency=freq,
            )

        # Output:SQLite für Ergebnis-Analyse
        idf.newidfobject(
            "OUTPUT:SQLITE",
            Option_Type="SimpleAndTabular",
        )

        # Output:Table:SummaryReports für Zusammenfassung
        idf.newidfobject(
            "OUTPUT:TABLE:SUMMARYREPORTS",
            Report_1_Name="AllSummary",
        )
