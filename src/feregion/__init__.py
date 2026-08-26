"""Fast Flinn-Engdahl region lookup for scalar and tabular coordinates."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup
from .types import Region

__version__ = "0.1.2a2"


def lookup_number(longitude: float, latitude: float) -> int:
    """Return the Flinn-Engdahl region number for one coordinate pair.

    Args:
        longitude: Finite WGS84 longitude in degrees, in ``[-180, 180]``.
        latitude: Finite WGS84 latitude in degrees, in ``[-90, 90]``.

    Returns:
        The positive integer region number from the packaged FE mapping.

    Raises:
        CoordinateTypeError: If a coordinate is not a supported real number.
        CoordinateValueError: If a coordinate is NaN or infinite.
        CoordinateRangeError: If a coordinate is outside its valid range.

    Notes:
        The function reuses the process-wide default engine. Longitude ``-180``
        has the same mapping semantics as ``+180``.
    """

    return get_default_lookup().lookup_number(longitude, latitude)


def lookup_region(longitude: float, latitude: float) -> Region:
    """Return the region number and packaged name for one coordinate pair.

    Args:
        longitude: Finite WGS84 longitude in degrees, in ``[-180, 180]``.
        latitude: Finite WGS84 latitude in degrees, in ``[-90, 90]``.

    Returns:
        An immutable :class:`Region` with the numeric ID and packaged name.

    Raises:
        CoordinateTypeError: If a coordinate is not a supported real number.
        CoordinateValueError: If a coordinate is NaN or infinite.
        CoordinateRangeError: If a coordinate is outside its valid range.
    """

    return get_default_lookup().lookup_region(longitude, latitude)


def lookup_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    """Return FE region numbers for a batch of coordinate pairs.

    Args:
        coordinates: Numeric two-dimensional input with shape ``(n, 2)``.
            Column 0 is longitude and column 1 is latitude.

    Returns:
        A one-dimensional ``uint16`` array with shape ``(n,)``.

    Raises:
        CoordinateShapeError: If the input does not have shape ``(n, 2)``.
        CoordinateTypeError: If the input dtype is unsupported.
        CoordinateValueError: If any coordinate is NaN or infinite.
        CoordinateRangeError: If any coordinate is outside its valid range.

    Notes:
        This is the performance-oriented public lookup interface. The input is
        not modified and region-name conversion is intentionally separate.
    """

    return get_default_lookup().lookup_numbers(coordinates)


def number_to_name(number: int) -> str:
    """Return the packaged region name for one FE region number.

    Args:
        number: Integer region number represented by the packaged name table.

    Returns:
        The name derived from ObsPy 1.4.2 ``names.asc``.

    Raises:
        RegionNumberError: If ``number`` is not a represented integer region
            number.
    """

    return get_default_lookup().number_to_name(number)


def numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert a region-number array to a same-shape packaged-name array.

    Args:
        numbers: Integer NumPy-compatible array of represented FE region
            numbers.

    Returns:
        A Unicode array with the same shape as ``numbers``.

    Raises:
        RegionNumberError: If the input is not an integer array or contains an
            unrepresented region number.
    """

    return get_default_lookup().numbers_to_names(numbers)


__all__ = [
    "FlinnEngdahlLookup",
    "Region",
    "get_default_lookup",
    "lookup_number",
    "lookup_numbers",
    "lookup_region",
    "number_to_name",
    "numbers_to_names",
]
