"""Fast offline Flinn-Engdahl geographical and seismic region lookup."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup, ScalarCoordinate
from .types import GeographicRegion, Region, SeismicRegion

__version__ = "0.3.0a4"


def lookup_geographic_number(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
    """Return one FE geographical-region number.

    Args:
        longitude: Longitude in ``[-180, 180]`` geographic degrees.
        latitude: Latitude in ``[-90, 90]`` geographic degrees.

    Returns:
        The active FE geographical-region identifier containing the coordinate.

    Raises:
        CoordinateTypeError: If either coordinate is not a supported real scalar.
        CoordinateValueError: If either coordinate is not finite.
        CoordinateRangeError: If either coordinate is outside the supported range.
    """

    return get_default_lookup().lookup_geographic_number(longitude, latitude)


def lookup_geographic_region(
    longitude: ScalarCoordinate, latitude: ScalarCoordinate
) -> GeographicRegion:
    """Return one FE geographical-region identifier and packaged name.

    Args:
        longitude: Longitude in ``[-180, 180]`` geographic degrees.
        latitude: Latitude in ``[-90, 90]`` geographic degrees.

    Returns:
        An immutable :class:`GeographicRegion` for the coordinate.

    Raises:
        CoordinateTypeError: If either coordinate is not a supported real scalar.
        CoordinateValueError: If either coordinate is not finite.
        CoordinateRangeError: If either coordinate is outside the supported range.
    """

    return get_default_lookup().lookup_geographic_region(longitude, latitude)


def lookup_geographic_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    """Return FE geographical-region numbers for a coordinate batch.

    Args:
        coordinates: Numeric array-like input with shape ``(n, 2)`` in
            ``[longitude, latitude]`` column order.

    Returns:
        A one-dimensional ``uint16`` array with shape ``(n,)``.

    Raises:
        CoordinateShapeError: If the input does not have shape ``(n, 2)``.
        CoordinateTypeError: If the input dtype is not a supported real numeric type.
        CoordinateValueError: If a coordinate is not finite.
        CoordinateRangeError: If a coordinate is outside the supported range.
    """

    return get_default_lookup().lookup_geographic_numbers(coordinates)


def geographic_number_to_name(number: int) -> str:
    """Return the packaged name of one active FE geographical region.

    Args:
        number: Active geographical-region identifier.

    Returns:
        The packaged geographical-region name as a Python string.

    Raises:
        RegionNumberError: If ``number`` is not an active geographical identifier.
    """

    return get_default_lookup().geographic_number_to_name(number)


def geographic_numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert FE geographical-region identifiers to packaged names.

    Args:
        numbers: Integer array-like active geographical identifiers. A scalar
            array-like value is accepted and has shape ``()``.

    Returns:
        A Unicode NumPy array with the same shape as ``numbers``. Scalar input
        returns a zero-dimensional array, not a NumPy scalar.

    Raises:
        RegionNumberError: If the input is not integer-valued or contains an
            inactive or unknown geographical identifier.
    """

    return get_default_lookup().geographic_numbers_to_names(numbers)


def geographic_to_seismic_number(number: int) -> int:
    """Return the seismic parent of one active FE geographical region.

    Args:
        number: Active geographical-region identifier.

    Returns:
        The parent seismic-region identifier in the range 1 through 50.

    Raises:
        RegionNumberError: If ``number`` is not an active geographical identifier.
    """

    return get_default_lookup().geographic_to_seismic_number(number)


def geographic_numbers_to_seismic_numbers(
    numbers: npt.ArrayLike,
) -> npt.NDArray[np.uint8]:
    """Convert geographical identifiers to same-shape seismic identifiers.

    Args:
        numbers: Integer array-like active geographical identifiers. A scalar
            array-like value is accepted and has shape ``()``.

    Returns:
        A ``uint8`` NumPy array with the same shape as ``numbers``. Scalar input
        returns a zero-dimensional array.

    Raises:
        RegionNumberError: If the input is not integer-valued or contains an
            inactive, unknown, or unmapped geographical identifier.
    """

    return get_default_lookup().geographic_numbers_to_seismic_numbers(numbers)


def lookup_seismic_number(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
    """Return one FE seismic-region number.

    Args:
        longitude: Longitude in ``[-180, 180]`` geographic degrees.
        latitude: Latitude in ``[-90, 90]`` geographic degrees.

    Returns:
        The seismic-region identifier containing the coordinate.

    Raises:
        CoordinateTypeError: If either coordinate is not a supported real scalar.
        CoordinateValueError: If either coordinate is not finite.
        CoordinateRangeError: If either coordinate is outside the supported range.
    """

    return get_default_lookup().lookup_seismic_number(longitude, latitude)


def lookup_seismic_region(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> SeismicRegion:
    """Return one FE seismic-region identifier and packaged name.

    Args:
        longitude: Longitude in ``[-180, 180]`` geographic degrees.
        latitude: Latitude in ``[-90, 90]`` geographic degrees.

    Returns:
        An immutable :class:`SeismicRegion` for the coordinate.

    Raises:
        CoordinateTypeError: If either coordinate is not a supported real scalar.
        CoordinateValueError: If either coordinate is not finite.
        CoordinateRangeError: If either coordinate is outside the supported range.
    """

    return get_default_lookup().lookup_seismic_region(longitude, latitude)


def lookup_seismic_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint8]:
    """Return FE seismic-region numbers for a coordinate batch.

    Args:
        coordinates: Numeric array-like input with shape ``(n, 2)`` in
            ``[longitude, latitude]`` column order.

    Returns:
        A one-dimensional ``uint8`` array with shape ``(n,)``.

    Raises:
        CoordinateShapeError: If the input does not have shape ``(n, 2)``.
        CoordinateTypeError: If the input dtype is not a supported real numeric type.
        CoordinateValueError: If a coordinate is not finite.
        CoordinateRangeError: If a coordinate is outside the supported range.
    """

    return get_default_lookup().lookup_seismic_numbers(coordinates)


def seismic_number_to_name(number: int) -> str:
    """Return the packaged name of one FE seismic region.

    Args:
        number: Seismic-region identifier.

    Returns:
        The packaged seismic-region name as a Python string.

    Raises:
        RegionNumberError: If ``number`` is not a known seismic identifier.
    """

    return get_default_lookup().seismic_number_to_name(number)


def seismic_numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert FE seismic-region identifiers to packaged names.

    Args:
        numbers: Integer array-like seismic identifiers. A scalar array-like
            value is accepted and has shape ``()``.

    Returns:
        A Unicode NumPy array with the same shape as ``numbers``. Scalar input
        returns a zero-dimensional array, not a NumPy scalar.

    Raises:
        RegionNumberError: If the input is not integer-valued or contains an
            unknown seismic identifier.
    """

    return get_default_lookup().seismic_numbers_to_names(numbers)


# Compatibility surface from the 0.1 contract. These names continue to mean
# geographical regions. No deprecation is planned for this compatibility surface.
def lookup_number(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
    """Compatibility alias for :func:`lookup_geographic_number`."""

    return lookup_geographic_number(longitude, latitude)


def lookup_region(longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> Region:
    """Compatibility alias for :func:`lookup_geographic_region`."""

    return lookup_geographic_region(longitude, latitude)


def lookup_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    """Compatibility alias for :func:`lookup_geographic_numbers`."""

    return lookup_geographic_numbers(coordinates)


def number_to_name(number: int) -> str:
    """Compatibility alias for :func:`geographic_number_to_name`."""

    return geographic_number_to_name(number)


def numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Compatibility alias for :func:`geographic_numbers_to_names`."""

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
