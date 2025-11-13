"""Shared Types für Geometrie-Feature.

Diese Types werden intern von Generatoren verwendet und als Output/State
zurückgegeben. Sie sind wiederverwendbar über verschiedene Generator-Typen.

Im Gegensatz zu models/ (User-Input) sind dies interne Datenstrukturen.
"""

from .generator_types import (
    # Zone Types
    ZoneInfo,
    create_zone_info_from_idf_object,

    # Surface Types
    SurfaceInfo,
    WindowInfo,

    # Configuration Types
    MetadataConfig,
    OutputConfig,
    OutputVariable,
    LocationData,

    # Result Types
    GenerationResult,
)

__all__ = [
    # Zone Types
    'ZoneInfo',
    'create_zone_info_from_idf_object',

    # Surface Types
    'SurfaceInfo',
    'WindowInfo',

    # Configuration Types
    'MetadataConfig',
    'OutputConfig',
    'OutputVariable',
    'LocationData',

    # Result Types
    'GenerationResult',
]
