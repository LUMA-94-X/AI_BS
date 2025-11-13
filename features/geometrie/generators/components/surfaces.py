"""Surface Generator für Gebäude-Hüllflächen.

Erstellt alle Surfaces (Walls, Floors, Ceilings, Roofs) und Windows
für 5-Zonen Perimeter+Core Modelle.

KRITISCHE ANFORDERUNGEN:
- Counter-clockwise Vertex-Ordering (EnergyPlus Requirement!)
- Floor vertices: REVERSED [3,2,1,0] (normal points DOWN)
- Ceiling vertices: NORMAL [0,1,2,3] (normal points UP)
- Interior wall pairs: Vertices reversed between zones
"""

from typing import Any, Dict, List, Tuple, Optional

from features.geometrie.types import SurfaceInfo, WindowInfo


class SurfaceGenerator:
    """Generiert Surfaces und Windows für EnergyPlus IDFs.

    Dieser Generator ist spezifisch für das 5-Zonen Perimeter+Core Layout,
    kann aber als Basis für andere Generator-Typen dienen.
    """

    def add_surfaces_5_zone(
        self,
        idf: Any,  # eppy IDF
        layouts: Dict[int, Any],  # Dict[int, ZoneLayout]
        geo_solution: Any,  # GeometrySolution
        orientation_wwr: Any  # OrientationWWR
    ) -> None:
        """Erstellt alle Surfaces für 5-Zonen-Modell.

        Args:
            idf: eppy IDF-Objekt
            layouts: Dictionary {floor_number: ZoneLayout}
            geo_solution: GeometrySolution mit Gebäudedimensionen
            orientation_wwr: OrientationWWR mit WWR pro Orientierung

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
            self._add_ceilings_5_zone(
                idf, layout, floor_num, geo_solution.num_floors, z_top
            )

            # === AUßENWÄNDE (nur Perimeter) ===
            self._add_exterior_walls_5_zone(
                idf, layout, z_base, z_top, orientation_wwr, geo_solution
            )

            # === INNENWÄNDE (zwischen Zonen) ===
            self._add_interior_walls_5_zone(idf, layout, z_base, z_top)

    def _add_floors_5_zone(
        self,
        idf: Any,
        layout: Any,  # ZoneLayout
        floor_num: int,
        z_base: float
    ) -> None:
        """Erstellt Böden für alle 5 Zonen.

        CRITICAL: Floor vertices must be REVERSED [3,2,1,0] for downward normal!

        Args:
            idf: eppy IDF-Objekt
            layout: ZoneLayout für dieses Geschoss
            floor_num: Geschoss-Nummer (0-basiert)
            z_base: Z-Koordinate der Basis
        """
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
                boundary_object = (
                    zone_geom.name.replace(f"_F{floor_num+1}", f"_F{floor_num}")
                    + "_Ceiling"
                )
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
        idf: Any,
        layout: Any,  # ZoneLayout
        floor_num: int,
        num_floors: int,
        z_top: float
    ) -> None:
        """Erstellt Decken/Dächer für alle 5 Zonen.

        CRITICAL: Ceiling/Roof normal must point UP [0,1,2,3]!

        Args:
            idf: eppy IDF-Objekt
            layout: ZoneLayout für dieses Geschoss
            floor_num: Geschoss-Nummer (0-basiert)
            num_floors: Gesamtanzahl Geschosse
            z_top: Z-Koordinate der Decke
        """
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
                boundary_object = (
                    zone_geom.name.replace(f"_F{floor_num+1}", f"_F{floor_num+2}")
                    + "_Floor"
                )
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
        idf: Any,
        layout: Any,  # ZoneLayout
        z_base: float,
        z_top: float,
        orientation_wwr: Any,  # OrientationWWR
        geo_solution: Any  # GeometrySolution
    ) -> None:
        """Erstellt Außenwände mit Fenstern für Perimeter-Zonen.

        Nur Perimeter-Zonen haben Außenwände!

        Args:
            idf: eppy IDF-Objekt
            layout: ZoneLayout für dieses Geschoss
            z_base: Z-Koordinate Boden
            z_top: Z-Koordinate Decke
            orientation_wwr: WWR pro Orientierung
            geo_solution: GeometrySolution
        """
        from features.geometrie.utils.fenster_distribution import Orientation

        L = geo_solution.length
        W = geo_solution.width

        # North Perimeter - Außenwand an Y=W (Nordseite)
        # Counter-clockwise vertex order
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
        idf: Any,
        zone_name: str,
        wall_name: str,
        vertices: List[Tuple[float, float, float]],
        orientation: Any,  # Orientation enum
        wwr: float
    ) -> None:
        """Erstellt eine Außenwand mit Fenster.

        Args:
            idf: eppy IDF-Objekt
            zone_name: Zone-Name
            wall_name: Wall-Name
            vertices: 4 Vertices (counter-clockwise)
            orientation: Orientation (NORTH, EAST, SOUTH, WEST)
            wwr: Window-Wall-Ratio
        """
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
        idf: Any,
        wall_name: str,
        wall_vertices: List[Tuple[float, float, float]],
        wwr: float
    ) -> None:
        """Erstellt Fenster auf einer Wand.

        Algorithmus:
            - Proportional scaling mit sqrt(wwr)
            - Sill height: 0.9m
            - Max height: wall_height - 0.3m (ceiling clearance)
            - Horizontal zentriert

        Args:
            idf: eppy IDF-Objekt
            wall_name: Parent wall name
            wall_vertices: 4 Wall vertices (counter-clockwise)
            wwr: Window-Wall-Ratio (0-1)
        """
        v1, v2, v3, v4 = wall_vertices

        # Calculate wall dimensions
        # Wall width (horizontal distance v1 → v2)
        wall_width = ((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)**0.5

        # Wall height (vertical distance v1 → v4)
        # For counter-clockwise walls: v1 and v2 are at bottom (same Z)
        # Height is from v1 (bottom) to v4 (top)
        wall_height = abs(v4[2] - v1[2])

        # Window dimensions (maintaining aspect ratio)
        # sqrt(wwr) approach for proportional scaling
        scale_factor = wwr**0.5
        window_width = wall_width * scale_factor
        window_height = wall_height * scale_factor

        # Limit window height
        sill_height = 0.9  # 90cm sill
        ceiling_clearance = 0.3  # 30cm from ceiling
        max_available_height = wall_height - sill_height - ceiling_clearance
        window_height = min(window_height, max_available_height)

        # Center window horizontally
        h_offset = (wall_width - window_width) / 2
        v_offset = sill_height

        # Base point (bottom-left of wall = v1)
        base_x = v1[0]
        base_y = v1[1]
        base_z = v1[2]

        # Direction vectors
        # Horizontal direction (along wall from v1 to v2)
        h_dir_x = (v2[0] - v1[0]) / wall_width if wall_width > 0 else 0
        h_dir_y = (v2[1] - v1[1]) / wall_width if wall_width > 0 else 0

        # Window corners (counter-clockwise)
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
        idf: Any,
        layout: Any,  # ZoneLayout
        z_base: float,
        z_top: float
    ) -> None:
        """Erstellt Innenwände zwischen Zonen.

        Inter-Zone-Wände (8 Paare):
            - Perimeter North ↔ Core
            - Perimeter East ↔ Core
            - Perimeter South ↔ Core
            - Perimeter West ↔ Core
            - Perimeter North ↔ East (Ecke)
            - Perimeter North ↔ West (Ecke)
            - Perimeter South ↔ East (Ecke)
            - Perimeter South ↔ West (Ecke)

        Args:
            idf: eppy IDF-Objekt
            layout: ZoneLayout für dieses Geschoss
            z_base: Z-Koordinate Boden
            z_top: Z-Koordinate Decke
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
        idf: Any,
        zone_a: str,
        zone_b: str,
        wall_a_name: str,
        wall_b_name: str,
        vertices_a: List[Tuple[float, float, float]]
    ) -> None:
        """Erstellt Paar von Inter-Zone-Wänden (A→B und B→A).

        CRITICAL: Wall B vertices must be REVERSED from Wall A!

        Args:
            idf: eppy IDF-Objekt
            zone_a: Zone A Name
            zone_b: Zone B Name
            wall_a_name: Name der Wand in Zone A
            wall_b_name: Name der Wand in Zone B
            vertices_a: Vertices von Wand A (counter-clockwise from Zone A)
        """
        # Wall A (in Zone A, sieht nach Zone B)
        idf.newidfobject(
            "BUILDINGSURFACE:DETAILED",
            Name=wall_a_name,
            Surface_Type="Wall",
            Construction_Name="WallConstruction",
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
            Construction_Name="WallConstruction",
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
