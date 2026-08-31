"""Small public value types for Flinn-Engdahl region levels."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeographicRegion:
    """Immutable geographical-region value returned by scalar lookup.

    Attributes:
        number: Active Flinn-Engdahl geographical-region identifier.
        name: Packaged name associated with ``number``.
    """

    number: int
    name: str


@dataclass(frozen=True, slots=True)
class SeismicRegion:
    """Immutable seismic-region value returned by scalar lookup.

    Attributes:
        number: Flinn-Engdahl seismic-region identifier.
        name: Packaged seismic-region name associated with ``number``.
    """

    number: int
    name: str


# Backward-compatible public name. Before 0.2, ``Region`` always meant the FE
# geographical region returned by coordinate lookup.
Region = GeographicRegion

__all__ = ["GeographicRegion", "Region", "SeismicRegion"]
