"""Small public value types for Flinn-Engdahl region levels."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeographicRegion:
    """A Flinn-Engdahl geographical-region number and packaged name."""

    number: int
    name: str


@dataclass(frozen=True, slots=True)
class SeismicRegion:
    """A Flinn-Engdahl seismic-region number and packaged name."""

    number: int
    name: str


# Backward-compatible public name. Before 0.2, ``Region`` always meant the FE
# geographical region returned by coordinate lookup.
Region = GeographicRegion

__all__ = ["GeographicRegion", "Region", "SeismicRegion"]
