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
            template_file=Path("resources/energyplus/templates/hvac/ideal_loads.idf"),
            suitable_for=["office", "residential", "commercial", "any"],
            complexity="simple"
        ),
        "vav_reheat": HVACTemplate(
            name="vav_reheat",
            description="Variable Air Volume with Reheat - Standard for large offices",
            template_file=Path("resources/energyplus/templates/hvac/vav_reheat.idf"),
            suitable_for=["office", "commercial"],
            complexity="complex"
        ),
        "packaged_rooftop": HVACTemplate(
            name="packaged_rooftop",
            description="Packaged Rooftop Unit - Common for small commercial buildings",
            template_file=Path("resources/energyplus/templates/hvac/packaged_rooftop.idf"),
            suitable_for=["office", "retail", "commercial"],
            complexity="medium"
        ),
        "fan_coil": HVACTemplate(
            name="fan_coil",
            description="Fan Coil Units with Central Plant - Hotels, apartments",
            template_file=Path("resources/energyplus/templates/hvac/fan_coil.idf"),
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
        template_name: str = "ideal_loads",
        heating_setpoint: float = 20.0,
        cooling_setpoint: float = 26.0
    ) -> IDF:
        """Apply HVAC template to an IDF using simple ideal loads system.

        This method adds a simple ideal loads air system to all zones in the IDF.
        It's the most straightforward approach and works for most building types.

        Args:
            idf: IDF object to add HVAC to
            template_name: Name of template (currently only "ideal_loads" fully supported)
            heating_setpoint: Heating setpoint temperature in °C (default: 20.0)
            cooling_setpoint: Cooling setpoint temperature in °C (default: 26.0)

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

        # IMPORTANT: Remove any existing manual thermostats first!
        # When using HVACTEMPLATE, ExpandObjects will generate thermostats automatically.
        # Pre-existing manual thermostats will conflict and cause "field previously assigned" errors.
        self._remove_manual_thermostats(idf)

        # Add global objects required for IdealLoads HVAC
        self._ensure_global_objects(idf)

        # Add schedules if not present
        self._ensure_schedules(idf, heating_setpoint, cooling_setpoint)

        # Add shared thermostat ONCE for all zones
        self._add_shared_thermostat(idf, heating_setpoint, cooling_setpoint)

        # Add HVAC for each zone
        for zone in zones:
            zone_name = zone.Name
            self._add_ideal_loads_to_zone(idf, zone_name)

        print(f"✅ HVAC system applied to all zones")

        return idf

    def _remove_manual_thermostats(self, idf: IDF) -> None:
        """Remove manual ZoneControl:Thermostat objects before applying HVACTEMPLATE.

        When using HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM, ExpandObjects will automatically
        generate ZoneControl:Thermostat objects. Any pre-existing manual thermostats will
        conflict with these auto-generated ones, causing "field previously assigned" errors.

        This method removes:
        - ZONECONTROL:THERMOSTAT objects (manual thermostat assignments)
        - THERMOSTATSETPOINT:DUALSETPOINT objects (will be recreated by templates)

        Note: HVACTEMPLATE:THERMOSTAT objects are kept - those are the templates we want!
        """
        # Remove manual ZoneControl:Thermostat objects
        # IMPORTANT: Create a list copy to avoid iteration issues when removing
        manual_thermostats = list(idf.idfobjects.get('ZONECONTROL:THERMOSTAT', []))
        if manual_thermostats:
            print(f"   🧹 Removing {len(manual_thermostats)} manual thermostat(s)...")
            for obj in manual_thermostats:
                idf.removeidfobject(obj)

        # Also remove manual ThermostatSetpoint:DualSetpoint (will be recreated by ExpandObjects)
        # IMPORTANT: Create a list copy here too
        manual_setpoints = list(idf.idfobjects.get('THERMOSTATSETPOINT:DUALSETPOINT', []))
        if manual_setpoints:
            for obj in manual_setpoints:
                idf.removeidfobject(obj)

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

    def _ensure_schedules(
        self,
        idf: IDF,
        heating_setpoint: float = 20.0,
        cooling_setpoint: float = 26.0
    ) -> None:
        """Ensure required schedules exist in IDF.

        Creates schedules following the pattern from EnergyPlus example.
        Removes and recreates schedules to ensure correct values.

        Args:
            idf: IDF object
            heating_setpoint: Heating setpoint temperature in °C
            cooling_setpoint: Cooling setpoint temperature in °C
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

        # Note: ThermostatSetpoint:DualSetpoint is now removed in _remove_manual_thermostats()
        # and will be auto-generated by ExpandObjects from HVACTEMPLATE objects

        # Create AlwaysOn schedule (value = 4 for DualSetpoint control type)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="AlwaysOn",
            Schedule_Type_Limits_Name="Control Type",  # Must be discrete 0-4
            Hourly_Value=4.0,  # 4 = DualSetpoint control type
        )

        # Create Heating setpoint schedule (user-defined temperature)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="HeatingSetpoint",
            Schedule_Type_Limits_Name="Temperature",  # Temperature range
            Hourly_Value=heating_setpoint,  # User-defined heating setpoint
        )

        # Create Cooling setpoint schedule (user-defined temperature)
        idf.newidfobject(
            "SCHEDULE:CONSTANT",
            Name="CoolingSetpoint",
            Schedule_Type_Limits_Name="Temperature",  # Temperature range
            Hourly_Value=cooling_setpoint,  # User-defined cooling setpoint
        )

        # NOTE: ThermostatSetpoint:DualSetpoint is NOT created manually anymore!
        # When using HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM, ExpandObjects will
        # automatically generate the necessary ThermostatSetpoint:DualSetpoint objects
        # based on the HVACTEMPLATE:THERMOSTAT settings.
        # Creating it manually would cause conflicts with the auto-generated ones.

    def _load_template_with_zone(self, template_path: Path, zone_name: str) -> str:
        """
        Lädt HVAC-Template und ersetzt ZONE_NAME Platzhalter.

        Args:
            template_path: Pfad zum Template-File
            zone_name: Echter Zone-Name zum Ersetzen

        Returns:
            IDF-Content als String mit ersetztem Zone-Namen
        """
        if not template_path.exists():
            raise FileNotFoundError(f"HVAC Template nicht gefunden: {template_path}")

        content = template_path.read_text(encoding='utf-8')
        return content.replace('ZONE_NAME', zone_name)

    def _merge_template_objects(
        self,
        idf: IDF,
        template_content: str,
        object_types: list[str]
    ) -> None:
        """
        Merged Objekte aus Template-Content in IDF.

        Args:
            idf: Haupt-IDF-Objekt
            template_content: Template-Content als String
            object_types: Liste der zu kopierenden Objekt-Typen
        """
        import tempfile

        # Erstelle temporäres IDF aus Template
        with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False, encoding='utf-8') as tmp:
            tmp.write(template_content)
            tmp_path = tmp.name

        try:
            template_idf = IDF(tmp_path)

            # Kopiere gewünschte Objekte
            for obj_type in object_types:
                for obj in template_idf.idfobjects[obj_type]:
                    idf.copyidfobject(obj)
        finally:
            # Cleanup
            Path(tmp_path).unlink(missing_ok=True)

    def _add_shared_thermostat(
        self,
        idf: IDF,
        heating_setpoint: float = 20.0,
        cooling_setpoint: float = 26.0
    ) -> None:
        """
        Add shared thermostat for all zones (loaded once globally).

        Uses HVACTEMPLATE:THERMOSTAT which ExpandObjects will convert
        to proper thermostat objects.

        Args:
            idf: IDF object
            heating_setpoint: Heating setpoint temperature in °C
            cooling_setpoint: Cooling setpoint temperature in °C
        """
        # Check if thermostat already exists - remove old ones
        existing = [
            obj for obj in idf.idfobjects.get('HVACTEMPLATE:THERMOSTAT', [])
        ]

        if existing:
            # Remove ALL old thermostats (might be per-zone ones from old version)
            print(f"   🔄 Removing {len(existing)} old thermostat(s) and replacing with shared one...")
            for obj in existing:
                idf.removeidfobject(obj)

        # Load thermostat template
        template_path = self.templates_dir / "thermostat_shared.idf"

        if template_path.exists():
            import tempfile
            content = template_path.read_text(encoding='utf-8')

            # Merge into IDF
            with tempfile.NamedTemporaryFile(mode='w', suffix='.idf', delete=False, encoding='utf-8') as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                template_idf = IDF(tmp_path)
                for obj in template_idf.idfobjects['HVACTEMPLATE:THERMOSTAT']:
                    idf.copyidfobject(obj)
                print("   ✅ Added shared thermostat for all zones")
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        else:
            # Fallback: Create directly with user-defined setpoints
            idf.newidfobject(
                "HVACTEMPLATE:THERMOSTAT",
                Name="All Zones",
                Heating_Setpoint_Schedule_Name="",
                Constant_Heating_Setpoint=heating_setpoint,
                Cooling_Setpoint_Schedule_Name="",
                Constant_Cooling_Setpoint=cooling_setpoint,
            )
            print(f"   ✅ Created shared thermostat directly (Heating: {heating_setpoint}°C, Cooling: {cooling_setpoint}°C)")

    def _add_ideal_loads_to_zone(self, idf: IDF, zone_name: str) -> None:
        """
        Add ideal loads air system to a specific zone using HVACTEMPLATE.

        ✅ FIXED: Now uses HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM instead of direct ZONEHVAC
        This avoids eppy field order bugs that caused simulation crashes.

        See: SIMULATION_CRASH_ANALYSIS.md

        Args:
            idf: IDF object
            zone_name: Name of the zone
        """
        # Check if HVAC already exists for this zone - REMOVE old ones first
        existing_hvac_template = [
            obj for obj in idf.idfobjects.get('HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM', [])
            if obj.Zone_Name == zone_name
        ]

        if existing_hvac_template:
            print(f"   🔄 Zone '{zone_name}' has old HVAC - removing and replacing...")
            for obj in existing_hvac_template:
                idf.removeidfobject(obj)

        # Also remove any direct ZONEHVAC objects (shouldn't exist with templates, but clean up)
        existing_hvac_direct = [
            obj for obj in idf.idfobjects.get('ZONEHVAC:IDEALLOADSAIRSYSTEM', [])
            if zone_name in obj.Name
        ]
        if existing_hvac_direct:
            print(f"   🔄 Removing {len(existing_hvac_direct)} old ZONEHVAC objects...")
            for obj in existing_hvac_direct:
                idf.removeidfobject(obj)

        # Load and apply template
        template_path = self.templates_dir / "ideal_loads.idf"

        if not template_path.exists():
            # Fallback: Create HVACTEMPLATE objects directly
            print(f"   ⚠️  Template not found, creating HVACTEMPLATE objects directly")
            self._add_hvactemplate_direct(idf, zone_name)
            return

        # Load template with zone name
        template_content = self._load_template_with_zone(template_path, zone_name)

        # Merge HVACTEMPLATE objects (only ZONE, not THERMOSTAT - that's loaded globally)
        self._merge_template_objects(
            idf,
            template_content,
            ["HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM"]
        )

        print(f"   ✅ Added ideal loads HVAC to zone '{zone_name}' (via HVACTEMPLATE)")

    def _add_hvactemplate_direct(self, idf: IDF, zone_name: str) -> None:
        """
        Fallback: Create HVACTEMPLATE objects directly if template file not found.

        Args:
            idf: IDF object
            zone_name: Name of the zone
        """
        # HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM (reference shared thermostat)
        idf.newidfobject(
            "HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM",
            Zone_Name=zone_name,
            Template_Thermostat_Name="All Zones",  # Reference shared thermostat
            System_Availability_Schedule_Name="",
            Maximum_Heating_Supply_Air_Temperature=50.0,
            Minimum_Cooling_Supply_Air_Temperature=13.0,
            Maximum_Heating_Supply_Air_Humidity_Ratio=0.015,
            Minimum_Cooling_Supply_Air_Humidity_Ratio=0.009,
            Heating_Limit="NoLimit",
            Maximum_Heating_Air_Flow_Rate="",
            Maximum_Sensible_Heating_Capacity="",
            Cooling_Limit="NoLimit",
            Maximum_Cooling_Air_Flow_Rate="",
            Maximum_Total_Cooling_Capacity="",
            Heating_Availability_Schedule_Name="",
            Cooling_Availability_Schedule_Name="",
            Dehumidification_Control_Type="ConstantSupplyHumidityRatio",
            Cooling_Sensible_Heat_Ratio="",
            Humidification_Control_Type="ConstantSupplyHumidityRatio",
        )

        print(f"   ✅ Added HVACTEMPLATE objects directly for zone '{zone_name}'")

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
    hvac_template: str = "ideal_loads",
    heating_setpoint: float = 20.0,
    cooling_setpoint: float = 26.0
) -> IDF:
    """Convenience function to add HVAC to a geometry IDF.

    Args:
        geometry_idf: IDF with building geometry (from SimpleBoxGenerator)
        hvac_template: Name of HVAC template to apply
        heating_setpoint: Heating setpoint temperature in °C (default: 20.0)
        cooling_setpoint: Cooling setpoint temperature in °C (default: 26.0)

    Returns:
        IDF with HVAC system added
    """
    manager = HVACTemplateManager()
    return manager.apply_template_simple(
        geometry_idf,
        hvac_template,
        heating_setpoint=heating_setpoint,
        cooling_setpoint=cooling_setpoint
    )
