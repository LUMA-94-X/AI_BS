"""Standard construction and material definitions for EnergyPlus models."""

from eppy.modeleditor import IDF


def add_basic_materials(idf: IDF) -> None:
    """Add basic material definitions to IDF.

    These are simplified materials for initial testing.
    For production use, replace with detailed material properties.
    """
    # Concrete
    idf.newidfobject(
        "MATERIAL",
        Name="Concrete",
        Roughness="MediumRough",
        Thickness=0.20,
        Conductivity=1.95,
        Density=2400,
        Specific_Heat=900,
        Thermal_Absorptance=0.9,
        Solar_Absorptance=0.7,
        Visible_Absorptance=0.7,
    )

    # Insulation
    idf.newidfobject(
        "MATERIAL",
        Name="Insulation",
        Roughness="MediumRough",
        Thickness=0.10,
        Conductivity=0.04,
        Density=30,
        Specific_Heat=1300,
        Thermal_Absorptance=0.9,
        Solar_Absorptance=0.7,
        Visible_Absorptance=0.7,
    )

    # Gypsum Board
    idf.newidfobject(
        "MATERIAL",
        Name="GypsumBoard",
        Roughness="Smooth",
        Thickness=0.0127,
        Conductivity=0.16,
        Density=800,
        Specific_Heat=1090,
        Thermal_Absorptance=0.9,
        Solar_Absorptance=0.7,
        Visible_Absorptance=0.5,
    )

    # Brick
    idf.newidfobject(
        "MATERIAL",
        Name="Brick",
        Roughness="MediumRough",
        Thickness=0.10,
        Conductivity=0.89,
        Density=1920,
        Specific_Heat=790,
        Thermal_Absorptance=0.9,
        Solar_Absorptance=0.7,
        Visible_Absorptance=0.7,
    )

    # Plywood
    idf.newidfobject(
        "MATERIAL",
        Name="Plywood",
        Roughness="MediumSmooth",
        Thickness=0.019,
        Conductivity=0.12,
        Density=540,
        Specific_Heat=1210,
        Thermal_Absorptance=0.9,
        Solar_Absorptance=0.7,
        Visible_Absorptance=0.7,
    )


def add_basic_glazing(idf: IDF) -> None:
    """Add basic window glazing definitions."""
    # Simple double glazing
    idf.newidfobject(
        "WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM",
        Name="SimpleDoubleGlazing",
        UFactor=2.7,  # W/m²K
        Solar_Heat_Gain_Coefficient=0.7,
        Visible_Transmittance=0.8,
    )


def add_basic_constructions(idf: IDF) -> None:
    """Add basic construction definitions to IDF."""
    # Add materials first
    add_basic_materials(idf)
    add_basic_glazing(idf)

    # Wall Construction (outside to inside)
    idf.newidfobject(
        "CONSTRUCTION",
        Name="WallConstruction",
        Outside_Layer="Brick",
        Layer_2="Insulation",
        Layer_3="Concrete",
        Layer_4="GypsumBoard",
    )

    # Roof Construction
    idf.newidfobject(
        "CONSTRUCTION",
        Name="RoofConstruction",
        Outside_Layer="Plywood",
        Layer_2="Insulation",
        Layer_3="Concrete",
        Layer_4="GypsumBoard",
    )

    # Floor Construction
    idf.newidfobject(
        "CONSTRUCTION",
        Name="FloorConstruction",
        Outside_Layer="Concrete",
        Layer_2="Insulation",
        Layer_3="Concrete",
    )

    # Ceiling Construction (internal)
    idf.newidfobject(
        "CONSTRUCTION",
        Name="CeilingConstruction",
        Outside_Layer="GypsumBoard",
        Layer_2="Insulation",
        Layer_3="GypsumBoard",
    )

    # Window Construction
    idf.newidfobject(
        "CONSTRUCTION",
        Name="WindowConstruction",
        Outside_Layer="SimpleDoubleGlazing",
    )


def add_enhanced_materials(idf: IDF, standard: str = "ISO_13790") -> None:
    """Add enhanced material definitions based on building standards.

    Args:
        idf: IDF object
        standard: Building standard (e.g., 'ISO_13790', 'TABULA_DE')
    """
    # This is a placeholder for future implementation
    # Will load materials from standard databases
    add_basic_materials(idf)
    add_basic_glazing(idf)


def get_construction_u_value(construction_name: str) -> float:
    """Get approximate U-value for a construction.

    Args:
        construction_name: Name of construction

    Returns:
        U-value in W/m²K
    """
    # Approximate U-values for basic constructions
    u_values = {
        "WallConstruction": 0.35,  # Well-insulated wall
        "RoofConstruction": 0.25,  # Well-insulated roof
        "FloorConstruction": 0.40,  # Insulated floor
        "WindowConstruction": 2.7,  # Double glazing
    }

    return u_values.get(construction_name, 1.0)
