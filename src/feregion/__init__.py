"""Fast offline Flinn-Engdahl geographical and seismic region lookup."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup, ScalarCoordinate
from .types import GeographicRegion, Region, SeismicRegion

__version__ = "0.3.0a2"


def lookup_geographic_number(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
    """Return the FE geographical-region number for one coordinate pair."""

    return get_default_lookup().lookup_geographic_number(longitude, latitude)


def lookup_geographic_region(
    longitude: ScalarCoordinate, latitude: ScalarCoordinate
) -> GeographicRegion:
    """Return the FE geographical-region number and packaged name."""

    return get_default_lookup().lookup_geographic_region(longitude, latitude)


def lookup_geographic_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    """Return FE geographical-region numbers for ``(longitude, latitude)`` rows."""

    return get_default_lookup().lookup_geographic_numbers(coordinates)


def geographic_number_to_name(number: int) -> str:
    """Return the packaged name for one active FE geographical region."""

    return get_default_lookup().geographic_number_to_name(number)


def geographic_numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert FE geographical-region numbers to same-shape packaged names."""

    return get_default_lookup().geographic_numbers_to_names(numbers)


def geographic_to_seismic_number(number: int) -> int:
    """Return the FE seismic parent of one active geographical region."""

    return get_default_lookup().geographic_to_seismic_number(number)


def geographic_numbers_to_seismic_numbers(
    numbers: npt.ArrayLike,
) -> npt.NDArray[np.uint8]:
    """Convert FE geographical-region numbers to same-shape seismic numbers."""

    return get_default_lookup().geographic_numbers_to_seismic_numbers(numbers)


def lookup_seismic_number(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
    """Return the FE seismic-region number for one coordinate pair."""

    return get_default_lookup().lookup_seismic_number(longitude, latitude)


def lookup_seismic_region(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> SeismicRegion:
    """Return the FE seismic-region number and packaged name."""

    return get_default_lookup().lookup_seismic_region(longitude, latitude)


def lookup_seismic_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint8]:
    """Return FE seismic-region numbers for ``(longitude, latitude)`` rows."""

    return get_default_lookup().lookup_seismic_numbers(coordinates)


def seismic_number_to_name(number: int) -> str:
    """Return the packaged name for one FE seismic region."""

    return get_default_lookup().seismic_number_to_name(number)


def seismic_numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert FE seismic-region numbers to same-shape packaged names."""

    return get_default_lookup().seismic_numbers_to_names(numbers)


# Compatibility surface from the 0.1 contract. These names continue to mean
# geographical regions. No deprecation is planned for this compatibility surface.
def lookup_number(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
    """Return the FE geographical-region number for one coordinate pair."""

    return lookup_geographic_number(longitude, latitude)


def lookup_region(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> Region:
    """Return the FE geographical-region number and packaged name."""

    return lookup_geographic_region(longitude, latitude)


def lookup_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    """Return FE geographical-region numbers for a batch of coordinates."""

    return lookup_geographic_numbers(coordinates)


def number_to_name(number: int) -> str:
    """Return the packaged FE geographical-region name."""

    return geographic_number_to_name(number)


def numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert FE geographical-region numbers to packaged names."""

    return geographic_numbers_to_names(numbers)


__all__ = [
    "FlinnEngdahlLookup",
    "GeographicRegion",
    "Region",
    "ScalarCoordinate",
    "SeismicRegion",
    "geographic_number_to_name",
    "geographic_numbers_to_names",
    "geographic_numbers_to_seismic_numbers",
    "geographic_to_seismic_number",
    "get_default_lookup",
    "lookup_geographic_number",
    "lookup_geographic_numbers",
    "lookup_geographic_region",
    "lookup_number",
    "lookup_numbers",
    "lookup_region",
    "lookup_seismic_number",
    "lookup_seismic_numbers",
    "lookup_seismic_region",
    "number_to_name",
    "numbers_to_names",
    "seismic_number_to_name",
    "seismic_numbers_to_names",
]
