"""HVAC Template Manager for applying different HVAC system types to buildings."""

from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
import shutil

from eppy.modeleditor import IDF


@dataclass
class HVACTemplate:
    """Represents an HVAC system template."""

    name: str
    description: str
    template_file: Path
    suitable_for: List[str]  # Building types this is suitable for
    complexity: str  # "simple", "medium", "complex"


class HVACTemplateManager:
    """Manager for HVAC system templates."""

    # Available HVAC templates
    TEMPLATES = {
        "ideal_loads": HVACTemplate(
            name="ideal_loads",
            description="Ideal Loads Air System - Unlimited heating/cooling capacity",
            template_file=Path("templates/hvac/ideal_loads.idf"),
            suitable_for=["office", "residential", "commercial", "any"],
            complexity="simple"
        ),
        "vav_reheat": HVACTemplate(
            name="vav_reheat",
            description="Variable Air Volume with Reheat - Standard for large offices",
            template_file=Path("templates/hvac/vav_reheat.idf"),
            suitable_for=["office", "commercial"],
            complexity="complex"
        ),
        "packaged_rooftop": HVACTemplate(
            name="packaged_rooftop",
            description="Packaged Rooftop Unit - Common for small commercial buildings",
            template_file=Path("templates/hvac/packaged_rooftop.idf"),
            suitable_for=["office", "retail", "commercial"],
            complexity="medium"
        ),
        "fan_coil": HVACTemplate(
            name="fan_coil",
            description="Fan Coil Units with Central Plant - Hotels, apartments",
            template_file=Path("templates/hvac/fan_coil.idf"),
            suitable_for=["residential", "hotel"],
            complexity="medium"
        ),
    }

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the HVAC template manager.

        Args:
            templates_dir: Directory containing HVAC templates.
                          If None, uses project default.
        """
        if templates_dir is None:
            # Default to project templates directory
            self.templates_dir = Path(__file__).parent.parent.parent / "templates" / "hvac"
        else:
            self.templates_dir = Path(templates_dir)

        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> Dict[str, HVACTemplate]:
        """List all available HVAC templates.

        Returns:
            Dictionary of template name -> HVACTemplate
        """
        return self.TEMPLATES.copy()

    def get_template(self, template_name: str) -> HVACTemplate:
        """Get a specific HVAC template.

        Args:
            template_name: Name of the template

        Returns:
            HVACTemplate object

        Raises:
            ValueError: If template not found
        """
        if template_name not in self.TEMPLATES:
            available = ", ".join(self.TEMPLATES.keys())
            raise ValueError(
                f"Unknown HVAC template '{template_name}'. "
                f"Available templates: {available}"
            )
        return self.TEMPLATES[template_name]

    def apply_template_simple(
        self,
        idf: IDF,
        template_name: str = "ideal_loads"
    ) -> IDF:
        """Apply HVAC template to an IDF using simple ideal loads system.

        This method adds a simple ideal loads air system to all zones in the IDF.
        It's the most straightforward approach and works for most building types.

        Args:
            idf: IDF object to add HVAC to
            template_name: Name of template (currently only "ideal_loads" fully supported)

        Returns:
            Modified IDF object
        """
        if template_name != "ideal_loads":
            print(f"⚠️  Template '{template_name}' not yet implemented. Using 'ideal_loads'.")

        # Get all zones
        zones = idf.idfobjects.get('ZONE', [])

        if not zones:
            raise ValueError("No zones found in IDF. Cannot add HVAC system.")

        print(f"\n🔧 Applying HVAC template '{template_name}' to {len(zones)} zones...")

        # Add global objects required for IdealLoads HVAC
        self._ensure_global_objects(idf)

        # Add schedules if not present
        self._ensure_schedules(idf)

        # Add HVAC for each zone
        for zone in zones:
            zone_name = zone.Name
            self._add_ideal_loads_to_zone(idf, zone_name)

        print(f"✅ HVAC system applied to all zones")

        return idf

    def _ensure_global_objects(self, idf: IDF) -> None:
        """Ensure global objects required for IdealLoads HVAC exist.

        These are critical objects that must exist for EnergyPlus to run properly.
        """
        # Add SurfaceConvectionAlgorithm objects if missing
        if not idf.idfobjects.get('SURFACECONVECTIONALGORITHM:INSIDE', []):
            idf.newidfobject(
                "SURFACECONVECTIONALGORITHM:INSIDE",
                Algorithm="Simple"
            )

        if not idf.idfobjects.get('SURFACECONVECTIONALGORITHM:OUTSIDE', []):
            idf.newidfobject(
                "SURFACECONVECTIONALGORITHM:OUTSIDE",
                Algorithm="SimpleCombined"
            )

        # Add Output:Diagnostics for better error reporting
        if not idf.idfobjects.get('OUTPUT:DIAGNOSTICS', []):
            idf.newidfobject(
                "OUTPUT:DIAGNOSTICS",
                Key_1="DisplayExtraWarnings"
            )

    def _ensure_schedule_type_limits(self, idf: IDF) -> None:
        """Ensure ScheduleTypeLimits objects exist.

        These define valid ranges and types for schedule values.
        Critical for thermostat schedules to work properly.
        """
        # Remove existing type limits we'll recreate
        for limit_name in ["Temperature", "Control Type"]:
            existing = [
                obj for obj in idf.idfobjects.get('SCHEDULETYPELIMITS', [])
                if obj.Name == limit_name
            ]
            for obj in existing:
                idf.removeidfobject(obj)

        # Temperature type limits (for heating/cooling setpoints)
        idf.newidfobject(
            "SCHEDULETYPELIMITS",
            Name="Temperature",
            Lower_Limit_Value=-60,
            Upper_Limit_Value=200,
            Numeric_Type="CONTINUOUS",
            Unit_Type="Temperature"
        )

        # Control Type limits (for thermostat control schedule)
        idf.newidfobject(
            "SCHEDULETYPELIMITS",
            Name="Control Type",
            Lower_Limit_Value=0,
            Upper_Limit_Value=4,
            Numeric_Type="DISCRETE"
        )

    def _ensure_schedules(self, idf: IDF) -> None:
        """Ensure required schedules exist in IDF.

        Creates schedules following the pattern from EnergyPlus example.
        Removes and recreates schedules to ensure correct values.
        """
        # First ensure ScheduleTypeLimits exist
        self._ensure_schedule_type_limits(idf)

        # Remove existing schedules that we need to recreate with correct values
        for sch_name in ["AlwaysOn", "HeatingSetpoint", "CoolingSetpoint"]:
            existing = [
                sch for sch in idf.idfobjects.get('SCHEDULE:CONSTANT', [])
                if sch.Name == sch_name
            ]
            for sch in existing:
                idf.removeidfobject(sch)

        # Remove existing DualSetpoint
        existing_dsp = [
            obj for obj in idf.idfobjects.get('THERMOSTATSETPOINT:DUALSETPOINT', [])
            if obj.Name == "DualSetPoint"
        ]
        for obj in existing_dsp:
            idf.removeidfobject(obj)

        # Create AlwaysOn schedule (value = 4 for DualSetpoint control type)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="AlwaysOn",
            Schedule_Type_Limits_Name="Control Type",  # Must be discrete 0-4
            Hourly_Value=4.0,  # 4 = DualSetpoint control type
        )

        # Create Heating setpoint schedule (constant 20°C)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="HeatingSetpoint",
            Schedule_Type_Limits_Name="Temperature",  # Temperature range
            Hourly_Value=20.0,  # 20°C heating setpoint
        )

        # Create Cooling setpoint schedule (constant 26°C)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="CoolingSetpoint",
            Schedule_Type_Limits_Name="Temperature",  # Temperature range
            Hourly_Value=26.0,  # 26°C cooling setpoint
        )

        # Create shared ThermostatSetpoint:DualSetpoint object
        # All zones reference this same setpoint object
        idf.newidfobject(
            "THERMOSTATSETPOINT:DUALSETPOINT",
            Name="DualSetPoint",
            Heating_Setpoint_Temperature_Schedule_Name="HeatingSetpoint",
            Cooling_Setpoint_Temperature_Schedule_Name="CoolingSetpoint",
        )

    def _add_ideal_loads_to_zone(self, idf: IDF, zone_name: str) -> None:
        """Add ideal loads air system to a specific zone.

        Uses the proven approach from EnergyPlus example file:
        5Zone_IdealLoadsAirSystems_ReturnPlenum.idf

        This creates direct ZONEHVAC objects with the exact syntax
        that EnergyPlus expects (verified to work in v25.1).

        Args:
            idf: IDF object
            zone_name: Name of the zone
        """
        # Check if HVAC already exists for this zone
        existing_hvac = [
            obj for obj in idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', [])
            if zone_name in obj.Name
        ]

        if existing_hvac:
            print(f"   ⚠️  Zone '{zone_name}' already has HVAC, skipping")
            return

        # Add ZoneHVAC:IdealLoadsAirSystem
        # Syntax from working EnergyPlus example (5Zone_IdealLoadsAirSystems_ReturnPlenum.idf)
        idf.newidfobject(
            "ZONEHVAC:IDEALLOADSAIRSYSTEM",
            Name=f"{zone_name}_IdealLoads",
            Availability_Schedule_Name="",  # blank = always available
            Zone_Supply_Air_Node_Name=f"{zone_name}_Supply_Node",
            Zone_Exhaust_Air_Node_Name="",
            System_Inlet_Air_Node_Name="",
            Maximum_Heating_Supply_Air_Temperature=50.0,
            Minimum_Cooling_Supply_Air_Temperature=13.0,
            Maximum_Heating_Supply_Air_Humidity_Ratio=0.015,
            Minimum_Cooling_Supply_Air_Humidity_Ratio=0.009,
            Heating_Limit="NoLimit",
            Maximum_Heating_Air_Flow_Rate="autosize",  # IMPORTANT: "autosize" not blank!
            Maximum_Sensible_Heating_Capacity="",
            Cooling_Limit="NoLimit",
            Maximum_Cooling_Air_Flow_Rate="autosize",  # IMPORTANT: "autosize" not blank!
            Maximum_Total_Cooling_Capacity="",
            Heating_Availability_Schedule_Name="",
            Cooling_Availability_Schedule_Name="",
            Dehumidification_Control_Type="ConstantSupplyHumidityRatio",  # From example!
            Cooling_Sensible_Heat_Ratio="",
            Humidification_Control_Type="ConstantSupplyHumidityRatio",  # From example!
            Design_Specification_Outdoor_Air_Object_Name="",
            Outdoor_Air_Inlet_Node_Name="",
            Demand_Controlled_Ventilation_Type="",
            Outdoor_Air_Economizer_Type="",
            Heat_Recovery_Type="",
            Sensible_Heat_Recovery_Effectiveness="",
            Latent_Heat_Recovery_Effectiveness="",
        )

        # Add ZoneHVAC:EquipmentList
        idf.newidfobject(
            "ZONEHVAC:EQUIPMENTLIST",
            Name=f"{zone_name}_Equipment_List",
            Load_Distribution_Scheme="SequentialLoad",
            Zone_Equipment_1_Object_Type="ZoneHVAC:IdealLoadsAirSystem",
            Zone_Equipment_1_Name=f"{zone_name}_IdealLoads",
            Zone_Equipment_1_Cooling_Sequence=1,
            Zone_Equipment_1_Heating_or_NoLoad_Sequence=1,
            Zone_Equipment_1_Sequential_Cooling_Fraction_Schedule_Name="",
            Zone_Equipment_1_Sequential_Heating_Fraction_Schedule_Name="",
        )

        # Add ZoneHVAC:EquipmentConnections
        idf.newidfobject(
            "ZONEHVAC:EQUIPMENTCONNECTIONS",
            Zone_Name=zone_name,
            Zone_Conditioning_Equipment_List_Name=f"{zone_name}_Equipment_List",
            Zone_Air_Inlet_Node_or_NodeList_Name=f"{zone_name}_Supply_Node",
            Zone_Air_Exhaust_Node_or_NodeList_Name="",
            Zone_Air_Node_Name=f"{zone_name}_Air_Node",
            Zone_Return_Air_Node_or_NodeList_Name=f"{zone_name}_Return_Node",
        )

        # CRITICAL: Add ZoneControl:Thermostat
        # IdealLoads HVAC requires thermostats to control heating/cooling
        # Without this, EnergyPlus will crash during initialization!
        idf.newidfobject(
            "ZONECONTROL:THERMOSTAT",
            Name=f"{zone_name}_Thermostat",
            Zone_or_ZoneList_Name=zone_name,
            Control_Type_Schedule_Name="AlwaysOn",  # Schedule that = 4 (Dual Setpoint)
            Control_1_Object_Type="ThermostatSetpoint:DualSetpoint",
            Control_1_Name="DualSetPoint",  # Shared setpoint for all zones
        )

        print(f"   ✅ Added ideal loads HVAC to zone '{zone_name}'")

    def copy_hvac_from_example(
        self,
        source_idf_path: Path,
        target_idf: IDF,
        zone_mapping: Optional[Dict[str, str]] = None
    ) -> IDF:
        """Copy HVAC system from an example IDF to target IDF.

        This is useful for copying complex HVAC systems from EnergyPlus examples.

        Args:
            source_idf_path: Path to source IDF with HVAC system
            target_idf: Target IDF to copy HVAC to
            zone_mapping: Optional mapping of source zone names to target zone names
                         Format: {"source_zone": "target_zone"}
                         If None, assumes zone names match

        Returns:
            Modified target IDF

        Note:
            This is a complex operation and may require manual adjustments.
            It's recommended to review the resulting IDF before simulation.
        """
        print(f"\n🔧 Copying HVAC system from {source_idf_path}...")
        print("⚠️  Note: This is an advanced operation that may require manual review")

        # Load source IDF
        source_idf = IDF(str(source_idf_path))

        # Object types to copy (HVAC-related)
        hvac_object_types = [
            "ZONEHVAC:IDEALLOADSAIRSYSTEM",
            "ZONEHVAC:EQUIPMENTLIST",
            "ZONEHVAC:EQUIPMENTCONNECTIONS",
            "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
            # Add more as needed for complex systems
            # "COIL:HEATING:ELECTRIC",
            # "COIL:COOLING:DX:SINGLESPEED",
            # etc.
        ]

        copied_count = 0

        for obj_type in hvac_object_types:
            source_objects = source_idf.idfobjects.get(obj_type, [])

            for obj in source_objects:
                # Create copy in target
                new_obj = target_idf.newidfobject(obj_type)

                # Copy all fields
                for field in dir(obj):
                    if not field.startswith('_') and field[0].isupper():
                        try:
                            value = getattr(obj, field)

                            # Apply zone mapping if applicable
                            if zone_mapping and 'Zone' in field and isinstance(value, str):
                                value = zone_mapping.get(value, value)

                            setattr(new_obj, field, value)
                        except:
                            pass

                copied_count += 1

        print(f"✅ Copied {copied_count} HVAC objects")

        return target_idf


def create_building_with_hvac(
    geometry_idf: IDF,
    hvac_template: str = "ideal_loads"
) -> IDF:
    """Convenience function to add HVAC to a geometry IDF.

    Args:
        geometry_idf: IDF with building geometry (from SimpleBoxGenerator)
        hvac_template: Name of HVAC template to apply

    Returns:
        IDF with HVAC system added
    """
    manager = HVACTemplateManager()
    return manager.apply_template_simple(geometry_idf, hvac_template)
