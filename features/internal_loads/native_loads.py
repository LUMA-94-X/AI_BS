"""Native Internal Loads - Direct eppy object creation (NO templates!)

This module uses the SAME proven approach as features/hvac/ideal_loads.py:
- Create objects directly via idf.newidfobject()
- NO template files needed
- NO ExpandObjects needed
- Works immediately without preprocessing

Based on EnergyPlus Input Output Reference and verified working examples.
"""

from eppy.modeleditor import IDF
from typing import Dict, Optional
from pathlib import Path


class NativeInternalLoadsManager:
    """Manager for adding internal loads using native EnergyPlus objects.

    Uses eppy.newidfobject() - same approach as working HVAC system.
    """

    # Building type parameters (people/m², W/m² for lights and equipment)
    BUILDING_TYPES = {
        "office": {
            "people_per_area": 0.05,  # people/m² (1 person per 20m²)
            "lights_watts_per_area": 10.0,  # W/m²
            "equipment_watts_per_area": 8.0,  # W/m²
            "activity_level": 120.0,  # W/person (seated office work)
        },
        "residential": {
            "people_per_area": 0.02,  # people/m² (1 person per 50m²)
            "lights_watts_per_area": 5.0,  # W/m²
            "equipment_watts_per_area": 4.0,  # W/m²
            "activity_level": 100.0,  # W/person (light activity)
        },
    }

    def __init__(self):
        """Initialize the native internal loads manager."""
        pass

    def add_schedules(self, idf: IDF, building_type: str = "office") -> Dict[str, str]:
        """Add schedule objects needed for internal loads.

        Creates SCHEDULETYPELIMITS and SCHEDULE:CONSTANT objects.
        Simple approach: Always-on schedules for testing.

        Args:
            idf: IDF object
            building_type: Type of building ("office" or "residential")

        Returns:
            Dict mapping schedule type to schedule name
        """
        schedules = {}

        # Add ScheduleTypeLimits for Fraction (0-1)
        existing_fraction_limits = idf.idfobjects.get("SCHEDULETYPELIMITS", [])
        has_fraction = any(obj.Name == "Fraction" for obj in existing_fraction_limits)

        if not has_fraction:
            idf.newidfobject(
                "SCHEDULETYPELIMITS",
                Name="Fraction",
                Lower_Limit_Value=0.0,
                Upper_Limit_Value=1.0,
                Numeric_Type="Continuous",
            )

        # Add ScheduleTypeLimits for ActivityLevel (W/person)
        has_activity = any(obj.Name == "ActivityLevel" for obj in existing_fraction_limits)
        if not has_activity:
            idf.newidfobject(
                "SCHEDULETYPELIMITS",
                Name="ActivityLevel",
                Lower_Limit_Value=0.0,
                Upper_Limit_Value="",  # no upper limit
                Numeric_Type="Continuous",
                Unit_Type="ActivityLevel",
            )

        # Simple always-on schedule for occupancy (testing)
        # TODO: Replace with realistic schedules later
        if building_type == "office":
            schedule_value = 0.8  # 80% occupied during work hours
        else:
            schedule_value = 1.0  # 100% occupied for residential

        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="Always_On_Occupancy",
            Schedule_Type_Limits_Name="Fraction",
            Hourly_Value=schedule_value,
        )
        schedules["occupancy"] = "Always_On_Occupancy"

        # Activity level schedule
        activity_level = self.BUILDING_TYPES[building_type]["activity_level"]
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="Activity_Level_Schedule",
            Schedule_Type_Limits_Name="ActivityLevel",
            Hourly_Value=activity_level,
        )
        schedules["activity"] = "Activity_Level_Schedule"

        # Realistic schedules based on OIB RL6 / ÖNORM B 8110-6
        # Lights: Average 30% utilization (6h full use / 24h)
        # Equipment: Average 40% utilization (background loads + active use)
        if building_type == "office":
            lights_fraction = 0.4  # Office: 40% average (8-10h workday)
            equipment_fraction = 0.5  # Office: 50% average (computers, etc.)
        else:  # residential
            lights_fraction = 0.3  # Residential: 30% average (evening use)
            equipment_fraction = 0.4  # Residential: 40% average (fridge, standby, etc.)

        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="Realistic_Lights",  # Renamed from Always_On
            Schedule_Type_Limits_Name="Fraction",
            Hourly_Value=lights_fraction,
        )
        schedules["lights"] = "Realistic_Lights"

        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="Realistic_Equipment",  # Renamed from Always_On
            Schedule_Type_Limits_Name="Fraction",
            Hourly_Value=equipment_fraction,
        )
        schedules["equipment"] = "Realistic_Equipment"

        return schedules

    def add_people_to_zone(
        self,
        idf: IDF,
        zone_name: str,
        zone_area: float,
        building_type: str = "office",
        schedule_name: str = "Always_On_Occupancy",
        activity_schedule: str = "Activity_Level_Schedule",
    ) -> None:
        """Add PEOPLE object to a zone using native eppy approach.

        Args:
            idf: IDF object
            zone_name: Name of the zone
            zone_area: Floor area of the zone in m²
            building_type: Building type for defaults
            schedule_name: Occupancy schedule name
            activity_schedule: Activity level schedule name
        """
        params = self.BUILDING_TYPES.get(building_type, self.BUILDING_TYPES["office"])
        people_per_area = params["people_per_area"]

        # Create PEOPLE object
        # Based on EnergyPlus Input Output Reference Section: People
        idf.newidfobject(
            "PEOPLE",
            Name=f"{zone_name}_People",
            Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
            Number_of_People_Schedule_Name=schedule_name,
            Number_of_People_Calculation_Method="People/Area",
            Number_of_People="",  # blank when using People/Area method
            People_per_Floor_Area=people_per_area,
            Floor_Area_per_Person="",  # blank when using People/Area method
            Fraction_Radiant=0.3,  # 30% radiant heat
            Sensible_Heat_Fraction="autocalculate",
            Activity_Level_Schedule_Name=activity_schedule,
            # Optional fields left blank - simplified approach
        )

        print(f"   ✅ Added PEOPLE to zone '{zone_name}' ({people_per_area:.3f} people/m²)")

    def add_lights_to_zone(
        self,
        idf: IDF,
        zone_name: str,
        zone_area: float,
        building_type: str = "office",
        schedule_name: str = "Realistic_Lights",
    ) -> None:
        """Add LIGHTS object to a zone using native eppy approach.

        Args:
            idf: IDF object
            zone_name: Name of the zone
            zone_area: Floor area of the zone in m²
            building_type: Building type for defaults
            schedule_name: Lights schedule name
        """
        params = self.BUILDING_TYPES.get(building_type, self.BUILDING_TYPES["office"])
        watts_per_area = params["lights_watts_per_area"]

        # Create LIGHTS object
        idf.newidfobject(
            "LIGHTS",
            Name=f"{zone_name}_Lights",
            Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
            Schedule_Name=schedule_name,
            Design_Level_Calculation_Method="Watts/Area",
            Lighting_Level="",  # blank when using Watts/Area
            Watts_per_Floor_Area=watts_per_area,
            Watts_per_Person="",  # blank
            Return_Air_Fraction=0.0,
            Fraction_Radiant=0.42,  # typical for fluorescent lights
            Fraction_Visible=0.18,
            Fraction_Replaceable=1.0,
        )

        print(f"   ✅ Added LIGHTS to zone '{zone_name}' ({watts_per_area:.1f} W/m²)")

    def add_equipment_to_zone(
        self,
        idf: IDF,
        zone_name: str,
        zone_area: float,
        building_type: str = "office",
        schedule_name: str = "Realistic_Equipment",
    ) -> None:
        """Add ELECTRICEQUIPMENT object to a zone using native eppy approach.

        Args:
            idf: IDF object
            zone_name: Name of the zone
            zone_area: Floor area of the zone in m²
            building_type: Building type for defaults
            schedule_name: Equipment schedule name
        """
        params = self.BUILDING_TYPES.get(building_type, self.BUILDING_TYPES["office"])
        watts_per_area = params["equipment_watts_per_area"]

        # Create ELECTRICEQUIPMENT object
        idf.newidfobject(
            "ELECTRICEQUIPMENT",
            Name=f"{zone_name}_Equipment",
            Zone_or_ZoneList_or_Space_or_SpaceList_Name=zone_name,
            Schedule_Name=schedule_name,
            Design_Level_Calculation_Method="Watts/Area",
            Design_Level="",  # blank when using Watts/Area
            Watts_per_Floor_Area=watts_per_area,
            Watts_per_Person="",  # blank
            Fraction_Latent=0.0,
            Fraction_Radiant=0.3,
            Fraction_Lost=0.0,
        )

        print(f"   ✅ Added EQUIPMENT to zone '{zone_name}' ({watts_per_area:.1f} W/m²)")

    def add_all_loads_to_building(
        self,
        idf: IDF,
        zone_names: list,
        zone_areas: Dict[str, float],
        building_type: str = "office",
    ) -> None:
        """Add all internal loads (people, lights, equipment) to all zones.

        Args:
            idf: IDF object
            zone_names: List of zone names
            zone_areas: Dict mapping zone_name -> area in m²
            building_type: Building type for defaults
        """
        print(f"\n🔥 Adding internal loads to {len(zone_names)} zones ({building_type})...")

        # 1. Add schedules (once globally)
        schedules = self.add_schedules(idf, building_type)
        print(f"   ✅ Added {len(schedules)} schedules")

        # 2. Add loads to each zone
        for zone_name in zone_names:
            area = zone_areas.get(zone_name, 100.0)  # default 100m² if not found

            self.add_people_to_zone(
                idf, zone_name, area, building_type,
                schedules["occupancy"], schedules["activity"]
            )
            self.add_lights_to_zone(
                idf, zone_name, area, building_type, schedules["lights"]
            )
            self.add_equipment_to_zone(
                idf, zone_name, area, building_type, schedules["equipment"]
            )

        print(f"✅ Internal loads added to all zones!")
