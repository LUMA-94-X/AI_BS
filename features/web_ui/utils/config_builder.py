"""Build SimulationConfig from Streamlit session state for YAML export."""

from datetime import datetime
from typing import Dict, Any

from core.simulation_config import (
    SimulationConfig,
    BuildingParams,
    GeometryParams,
    EnvelopeParams,
    ZoneParams,
    HVACSystemConfig,
    IdealLoadsParams,
    SimulationParams,
    SimulationPeriod,
    OutputParams
)


def build_simulation_config_from_ui(session_state: Dict[str, Any]) -> SimulationConfig:
    """Build SimulationConfig from Streamlit session_state.

    Args:
        session_state: Streamlit session_state dictionary

    Returns:
        SimulationConfig object ready for YAML export

    Raises:
        ValueError: If required data is missing or invalid
        NotImplementedError: If trying to export Energieausweis model (not yet supported)
    """
    # Check if we have building_model
    building_model = session_state.get('building_model')
    geometry = session_state.get('geometry')

    if not building_model and not geometry:
        raise ValueError("No building model or geometry found in session_state")

    # Check source (building_model can be dict or object)
    source = None
    if building_model:
        if isinstance(building_model, dict):
            source = building_model.get('source')
        else:
            source = getattr(building_model, 'source', None)

    if source == "energieausweis":
        raise NotImplementedError(
            "Energieausweis YAML export not yet implemented. "
            "Please use SimpleBox workflow for now."
        )

    # Get parameters from session_state
    hvac_config = session_state.get('hvac_config', {})
    sim_settings = session_state.get('sim_settings', {})
    weather_file = session_state.get('weather_file', 'resources/energyplus/weather/austria/example.epw')

    # Build geometry from building_model or legacy geometry
    if building_model:
        # Handle dict or object
        if isinstance(building_model, dict):
            geom_summary = building_model.get('geometry_summary', {})
        else:
            geom_summary = getattr(building_model, 'geometry_summary', {})

        geometry_params = GeometryParams(
            length=geom_summary.get('length', 10.0),
            width=geom_summary.get('width', 10.0),
            height=geom_summary.get('height', 6.0),
            num_floors=geom_summary.get('num_floors', 2),
            window_wall_ratio=geom_summary.get('window_wall_ratio', 0.25),
            orientation=geom_summary.get('orientation', 0.0)
        )
    else:
        # Legacy geometry
        geometry_params = GeometryParams(
            length=geometry.length,
            width=geometry.width,
            height=geometry.height,
            num_floors=geometry.num_floors,
            window_wall_ratio=geometry.window_wall_ratio,
            orientation=geometry.orientation
        )

    # Build envelope params (defaults for now - U-values not yet used in SimpleBox)
    envelope_params = EnvelopeParams(
        wall_construction="medium_insulated",
        wall_u_value=0.35,
        roof_construction="insulated_roof",
        roof_u_value=0.25,
        floor_construction="slab_on_grade",
        floor_u_value=0.40,
        window_type="double_glazed",
        window_u_value=1.3,
        window_shgc=0.6
    )

    # Build zone params (defaults for now - not yet configurable in UI)
    zone_params = ZoneParams(
        zone_type="residential",
        people_density=0.02,
        lighting_power=5.0,
        equipment_power=3.0,
        occupancy_schedule="residential",
        lighting_schedule="residential",
        equipment_schedule="residential",
        infiltration_rate=0.5
    )

    # Build building params
    building_params = BuildingParams(
        name=f"SimpleBox_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        building_type="residential",
        geometry=geometry_params,
        envelope=envelope_params,
        default_zone=zone_params
    )

    # Build HVAC params
    hvac_params = HVACSystemConfig(
        system_type="ideal_loads",
        ideal_loads=IdealLoadsParams(
            heating_setpoint=hvac_config.get('heating_setpoint', 20.0),
            cooling_setpoint=hvac_config.get('cooling_setpoint', 26.0),
            heating_limit=None,
            cooling_limit=None,
            outdoor_air_flow_rate=0.0  # TODO: Calculate from air_change_rate
        )
    )

    # Build simulation params
    simulation_params = SimulationParams(
        weather_file=weather_file,
        timestep=sim_settings.get('timestep', 4),
        period=SimulationPeriod(
            start_month=sim_settings.get('start_month', 1),
            start_day=sim_settings.get('start_day', 1),
            end_month=sim_settings.get('end_month', 12),
            end_day=sim_settings.get('end_day', 31)
        ),
        output=OutputParams(
            output_dir=f"output/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            save_idf=True,
            save_sql=True,
            output_variables=sim_settings.get('output_variables', [
                "Zone Mean Air Temperature",
                "Zone Air System Sensible Heating Energy",
                "Zone Air System Sensible Cooling Energy"
            ]),
            reporting_frequency=sim_settings.get('reporting_frequency', 'Hourly')
        )
    )

    # Build complete config
    config = SimulationConfig(
        name=f"UI_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description="Exported from Web UI",
        version="1.0",
        building=building_params,
        hvac=hvac_params,
        simulation=simulation_params
    )

    return config
