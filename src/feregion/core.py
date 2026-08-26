"""Core scalar and NumPy Flinn-Engdahl lookup implementation."""

from __future__ import annotations

import math
import operator
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .exceptions import (
    CoordinateRangeError,
    CoordinateShapeError,
    CoordinateTypeError,
    CoordinateValueError,
    DataFileError,
    RegionNumberError,
)
from .types import Region

RegionNumberArray = npt.NDArray[np.uint16]

_TABLE_SHAPE = (4, 91, 181)
_NUMERIC_KINDS = frozenset("iuf")


@dataclass(frozen=True, slots=True, eq=False)
class FlinnEngdahlLookup:
    """Map WGS84 longitude/latitude coordinates to Flinn-Engdahl regions.

    ``table`` is an engine-owned immutable lookup array with shape ``(4, 91, 181)`` and
    ``uint16`` values. The dimensions are quadrant, absolute integer latitude,
    and absolute integer longitude. Quadrants use this order: northeast,
    northwest, southeast, southwest.

    ``names`` is a one-dimensional Unicode array indexed by region number.
    Index 0 is intentionally empty because Flinn-Engdahl region numbers start
    at 1.

    Explicit construction is primarily useful for tests and alternate data
    sets. Normal callers should use the package-level functions, which reuse a
    process-wide default instance.
    """

    table: npt.NDArray[np.uint16]
    names: npt.NDArray[np.str_]

    def __post_init__(self) -> None:
        """Validate data invariants and take ownership of immutable copies.

        Explicit construction accepts caller-owned arrays, but engine behavior
        must not change if the caller later mutates those arrays. Construction
        therefore copies the lookup table and region-name array once, then
        marks the owned copies read-only.
        """

        table = np.asarray(self.table)
        names = np.asarray(self.names)

        if table.shape != _TABLE_SHAPE:
            raise DataFileError(f"lookup table must have shape {_TABLE_SHAPE}, got {table.shape}")
        if table.dtype != np.dtype(np.uint16):
            raise DataFileError(f"lookup table must use uint16, got {table.dtype}")
        if names.ndim != 1:
            raise DataFileError(f"region names must be one-dimensional, got {names.shape}")
        if names.dtype.kind != "U":
            raise DataFileError(f"region names must use a Unicode dtype, got {names.dtype}")
        if names.size < 2 or names[0] != "":
            raise DataFileError("region names must reserve empty index 0")

        maximum = int(table.max())
        if maximum >= names.size:
            raise DataFileError(
                f"region names stop at index {names.size - 1}, but table uses {maximum}"
            )

        used = np.unique(table)
        if np.any(used == 0) or np.any(names[used] == ""):
            raise DataFileError("lookup table contains an unmapped region number")

        owned_table = np.array(table, copy=True, order="C")
        owned_table.setflags(write=False)
        owned_names = np.array(names, copy=True, order="C")
        owned_names.setflags(write=False)
        object.__setattr__(self, "table", owned_table)
        object.__setattr__(self, "names", owned_names)

    def lookup_number(self, longitude: float, latitude: float) -> int:
        """Return the region number for one coordinate pair.

        Longitude must be in ``[-180, 180]`` and latitude must be in
        ``[-90, 90]``. Both values must be finite real numbers. Longitude
        ``-180`` has the same lookup semantics as ``+180``, matching the ObsPy
        reference implementation.

        Raises:
            CoordinateTypeError: If a value is not a supported real number.
            CoordinateValueError: If a value is NaN or infinite.
            CoordinateRangeError: If a value is outside its valid range.
        """

        _validate_scalar_coordinate_types(longitude, latitude)
        _validate_scalar_coordinate_values(longitude, latitude)

        normalized_longitude = 180 if longitude == -180 else longitude
        absolute_longitude = int(abs(normalized_longitude))
        absolute_latitude = int(abs(latitude))
        quadrant = int(normalized_longitude < 0) + 2 * int(latitude < 0)
        return int(self.table[quadrant, absolute_latitude, absolute_longitude])

    def lookup_region(self, longitude: float, latitude: float) -> Region:
        """Return the region number and name for one coordinate pair."""

        number = self.lookup_number(longitude, latitude)
        return Region(number=number, name=self.number_to_name(number))

    def lookup_numbers(self, coordinates: npt.ArrayLike) -> RegionNumberArray:
        """Return region numbers for a two-column coordinate array.

        The input must have shape ``(n, 2)``. Column 0 contains longitude and
        column 1 contains latitude. Integer and floating NumPy dtypes are
        accepted. String, object, Boolean, and complex dtypes are rejected
        rather than coerced.

        The result has shape ``(n,)`` and dtype ``uint16``. The function does
        not modify the input array.

        Raises:
            CoordinateShapeError: If the input does not have shape ``(n, 2)``.
            CoordinateTypeError: If coordinates use an unsupported dtype.
            CoordinateValueError: If any coordinate is NaN or infinite.
            CoordinateRangeError: If any coordinate is outside its valid range.
        """

        array = _coordinate_array(coordinates)
        if array.shape[0] == 0:
            return np.empty(0, dtype=np.uint16)

        source_longitude = array[:, 0]
        source_latitude = array[:, 1]
        _validate_coordinate_values(source_longitude, source_latitude)

        numeric = array.astype(np.float64, copy=False)
        return self._lookup_validated(numeric[:, 0], numeric[:, 1])

    def number_to_name(self, number: int) -> str:
        """Return the packaged region name for one integer region number.

        Raises:
            RegionNumberError: If ``number`` is not an integer region number
                represented by the packaged data.
        """

        if isinstance(number, (bool, np.bool_)):
            raise RegionNumberError("region number must be an integer, not Boolean")
        try:
            index = operator.index(number)
        except TypeError as exc:
            raise RegionNumberError("region number must be an integer") from exc

        if index < 1 or index >= self.names.size or self.names[index] == "":
            raise RegionNumberError(f"unknown Flinn-Engdahl region number: {index}")
        return str(self.names[index])

    def numbers_to_names(self, numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
        """Convert integer region numbers to packaged region names.

        The returned Unicode array has the same shape as the input. Use
        :meth:`number_to_name` for a scalar when a Python ``str`` is preferred.

        Raises:
            RegionNumberError: If the input is not an integer array or contains
                an unknown region number.
        """

        try:
            array = np.asarray(numbers)
        except ValueError as exc:
            raise RegionNumberError("region numbers must form a rectangular array") from exc

        if array.dtype.kind not in "iu" or array.dtype.kind == "b":
            raise RegionNumberError("region numbers must use an integer dtype")
        if array.size == 0:
            return np.empty(array.shape, dtype=self.names.dtype)
        if np.any(array < 1) or np.any(array >= self.names.size):
            raise RegionNumberError("one or more Flinn-Engdahl region numbers are unknown")

        result = self.names[array]
        if np.any(result == ""):
            raise RegionNumberError("one or more Flinn-Engdahl region numbers are unknown")
        return result

    def _lookup_validated(
        self,
        longitude: npt.NDArray[np.float64],
        latitude: npt.NDArray[np.float64],
    ) -> RegionNumberArray:
        """Lookup already validated arrays without Python-level point loops."""

        normalized_longitude = np.where(longitude == -180.0, 180.0, longitude)
        absolute_longitude = np.abs(normalized_longitude).astype(np.uint8)
        absolute_latitude = np.abs(latitude).astype(np.uint8)

        quadrant = (normalized_longitude < 0.0).astype(np.uint8) + 2 * (latitude < 0.0).astype(
            np.uint8
        )
        return self.table[quadrant, absolute_latitude, absolute_longitude]


def _validate_scalar_coordinate_types(longitude: float, latitude: float) -> None:
    """Reject scalar types that the public coordinate contract does not accept."""

    for value in (longitude, latitude):
        if isinstance(value, (bool, np.bool_)):
            raise CoordinateTypeError("coordinates must be real numbers, not Boolean values")
        if not isinstance(value, (int, float, np.integer, np.floating)):
            raise CoordinateTypeError("coordinates must be real numbers")


def _validate_scalar_coordinate_values(longitude: float, latitude: float) -> None:
    """Validate scalar finiteness and ranges without creating NumPy arrays."""

    if not _scalar_is_finite(longitude):
        raise CoordinateValueError("longitude is NaN or infinite")
    if not _scalar_is_finite(latitude):
        raise CoordinateValueError("latitude is NaN or infinite")
    if longitude < -180 or longitude > 180:
        raise CoordinateRangeError("longitude must be within [-180, 180]")
    if latitude < -90 or latitude > 90:
        raise CoordinateRangeError("latitude must be within [-90, 90]")


def _scalar_is_finite(value: float) -> bool:
    """Check scalar finiteness without narrowing extended NumPy floats."""

    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, np.floating):
        if value.dtype.itemsize <= np.dtype(np.float64).itemsize:
            return math.isfinite(float(value))
        return bool(np.isfinite(value))
    return True


def _coordinate_array(coordinates: npt.ArrayLike) -> np.ndarray:
    """Validate array shape and dtype before numeric conversion."""

    try:
        array = np.asarray(coordinates)
    except ValueError as exc:
        raise CoordinateShapeError("coordinates must form a rectangular (n, 2) array") from exc

    if array.ndim != 2 or array.shape[1:] != (2,):
        raise CoordinateShapeError(f"coordinates must have shape (n, 2), got {array.shape}")
    if array.dtype.kind not in _NUMERIC_KINDS:
        raise CoordinateTypeError(
            f"coordinates must use an integer or floating dtype, got {array.dtype}"
        )
    return array


def _validate_coordinate_values(
    longitude: np.ndarray,
    latitude: np.ndarray,
) -> None:
    """Validate values in their source dtype before narrowing to float64."""

    if not np.all(np.isfinite(longitude)):
        raise CoordinateValueError("longitude contains a NaN or infinite value")
    if not np.all(np.isfinite(latitude)):
        raise CoordinateValueError("latitude contains a NaN or infinite value")
    if np.any((longitude < -180.0) | (longitude > 180.0)):
        raise CoordinateRangeError("longitude must be within [-180, 180]")
    if np.any((latitude < -90.0) | (latitude > 90.0)):
        raise CoordinateRangeError("latitude must be within [-90, 90]")
