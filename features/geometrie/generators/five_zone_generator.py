"""5-Zone Generator für EnergyPlus-Modelle aus Energieausweis-Daten."""

from typing import Optional, Dict, Tuple, List
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

# NEW: Import refactored components
from .components import (
    EppyBugFixer,
    MetadataGenerator,
    ZoneGenerator,
    MaterialsGenerator,
    SurfaceGenerator
)
from features.geometrie.types import MetadataConfig, ZoneInfo


class FiveZoneGenerator:
    """Generator für 5-Zonen-Gebäudemodelle (Perimeter N/E/S/W + Kern)."""

    def __init__(self, config=None):
        """
        Initialisiert den Generator.

        Args:
            config: Configuration object. If None, uses global config.
        """
        self.config = config or get_config()

        # Geometry utilities
        self.geometry_solver = GeometrySolver()
        self.perimeter_calc = PerimeterCalculator()
        self.fenster_dist = FensterDistribution()

        # NEW: Generator components
        self.metadata_gen = MetadataGenerator(MetadataConfig())
        self.materials_gen = MaterialsGenerator()
        self.zone_gen = ZoneGenerator()
        self.surface_gen = SurfaceGenerator()
        self.eppy_fixer = EppyBugFixer(debug=False)  # Set to True for debugging

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
        """Delegiert zu EppyBugFixer."""
        return self.eppy_fixer.collect_boundary_map(idf)

    def _fix_eppy_boundary_objects(self, boundary_map: dict, output_path: Path) -> None:
        """Delegiert zu EppyBugFixer."""
        self.eppy_fixer.fix_eppy_boundary_objects(boundary_map, output_path)

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
        """Delegiert zu MaterialsGenerator."""
        self.materials_gen.add_constructions_from_u_values(idf, ea_data)

    # ========================================================================
    # SIMULATION SETTINGS
    # ========================================================================

    def _add_simulation_settings(
        self,
        idf: IDF,
        geo_solution: GeometrySolution
    ) -> None:
        """Delegiert zu MetadataGenerator."""
        self.metadata_gen.add_simulation_settings(idf, geo_solution)
        self.metadata_gen.add_site_location(idf)

    # ========================================================================
    # ZONES
    # ========================================================================

    def _add_zones(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout]
    ) -> List[ZoneInfo]:
        """Delegiert zu ZoneGenerator. Returns ZoneInfo list."""
        return self.zone_gen.add_zones(idf, layouts)

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
        """Delegiert zu SurfaceGenerator."""
        self.surface_gen.add_surfaces_5_zone(idf, layouts, geo_solution, orientation_wwr)

    # ========================================================================
    # SCHEDULES & INTERNAL LOADS
    # ========================================================================

    def _add_schedules(self, idf: IDF, building_type) -> Dict[str, str]:
        """Fügt Standard-Schedules hinzu via NativeInternalLoadsManager.

        Args:
            idf: IDF object
            building_type: GebaeudeTyp enum or string

        Returns:
            Dict mapping schedule type to schedule name
        """
        # Map GebaeudeTyp enum to internal building types
        from features.geometrie.models.energieausweis_input import GebaeudeTyp

        if isinstance(building_type, GebaeudeTyp):
            # EFH/MFH -> residential, NWG -> office
            if building_type in (GebaeudeTyp.EFH, GebaeudeTyp.MFH):
                building_type_str = "residential"
            else:  # NWG
                building_type_str = "office"
        else:
            building_type_str = str(building_type)

        # Use proven native approach for schedules
        manager = NativeInternalLoadsManager()
        schedules = manager.add_schedules(idf, building_type_str)

        return schedules

    def _add_internal_loads(
        self,
        idf: IDF,
        layouts: Dict[int, ZoneLayout],
        gebaeudetyp,
        schedules: Dict[str, str]
    ) -> None:
        """Fügt Internal Loads (People, Lights, Equipment) hinzu.

        Uses NativeInternalLoadsManager for proven, stable implementation.

        Args:
            idf: IDF object
            layouts: Zone layouts per floor
            gebaeudetyp: GebaeudeTyp enum
            schedules: Schedule names dict from _add_schedules()
        """
        # Map GebaeudeTyp enum to internal types
        from features.geometrie.models.energieausweis_input import GebaeudeTyp

        if isinstance(gebaeudetyp, GebaeudeTyp):
            # EFH/MFH -> residential, NWG -> office
            if gebaeudetyp in (GebaeudeTyp.EFH, GebaeudeTyp.MFH):
                building_type = "residential"
            else:  # NWG
                building_type = "office"
        else:
            building_type = "office"  # fallback

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
        """Delegiert zu MetadataGenerator."""
        self.metadata_gen.add_output_variables(idf)
