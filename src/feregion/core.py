"""Core scalar and NumPy Flinn-Engdahl lookup implementation."""

from __future__ import annotations

import math
import operator
from dataclasses import dataclass, field
from typing import Any, SupportsInt, TypeAlias, cast

import numpy as np
import numpy.typing as npt

from .exceptions import (
    CoordinateRangeError,
    CoordinateShapeError,
    CoordinateTypeError,
    CoordinateValueError,
    DataFileError,
    RegionNumberError,
    SeismicDataUnavailableError,
)
from .types import GeographicRegion, Region, SeismicRegion

GeographicNumberArray = npt.NDArray[np.uint16]
SeismicNumberArray = npt.NDArray[np.uint8]
RegionNumberArray = GeographicNumberArray
ScalarCoordinate: TypeAlias = int | float | np.integer[Any] | np.floating[Any]

_TABLE_SHAPE = (4, 91, 181)
_NUMERIC_KINDS = frozenset("iuf")


@dataclass(frozen=True, slots=True, eq=False)
class FlinnEngdahlLookup:
    """Map longitude/latitude degrees to FE geographical and seismic regions.

    Args:
        table: Immutable geographical lookup source after construction. The
            array must have shape ``(4, 91, 181)`` and dtype ``uint16``.
        names: One-based Unicode geographical-region names. Index 0 must be
            empty.
        seismic_by_geographic: Optional one-based ``uint8`` crosswalk from
            geographical-region number to seismic-region number. Index 0 is
            the sentinel value 0. If omitted, seismic operations are disabled.
        seismic_names: Optional one-based Unicode seismic-region names. This
            argument must be supplied together with ``seismic_by_geographic``.

    Notes:
        Explicit two-array construction remains supported for alternate
        geographical datasets. The packaged default engine supplies the two
        seismic arrays as well. The engine takes ownership of copies of every
        supplied array and marks the copies read-only.
    """

    table: npt.NDArray[np.uint16]
    names: npt.NDArray[np.str_]
    seismic_by_geographic: npt.NDArray[np.uint8] | None = None
    seismic_names: npt.NDArray[np.str_] | None = None
    _active_geographic: npt.NDArray[np.bool_] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate data invariants and take ownership of immutable copies."""

        table = np.asarray(self.table)
        names = np.asarray(self.names)

        if table.shape != _TABLE_SHAPE:
            raise DataFileError(f"lookup table must have shape {_TABLE_SHAPE}, got {table.shape}")
        if table.dtype != np.dtype(np.uint16):
            raise DataFileError(f"lookup table must use uint16, got {table.dtype}")
        _validate_name_array(names, "geographical-region names")

        maximum = int(table.max())
        if maximum >= names.size:
            raise DataFileError(
                f"geographical-region names stop at index {names.size - 1}, "
                f"but table uses {maximum}"
            )
        used = np.unique(table)
        if np.any(used == 0) or np.any(names[used] == ""):
            raise DataFileError("lookup table contains an unmapped geographical-region number")
        active_geographic = np.zeros(names.shape, dtype=np.bool_)
        active_geographic[used] = True
        active_geographic.setflags(write=False)

        crosswalk = self.seismic_by_geographic
        seismic_names = self.seismic_names
        if (crosswalk is None) != (seismic_names is None):
            raise DataFileError("seismic_by_geographic and seismic_names must be supplied together")

        owned_crosswalk: npt.NDArray[np.uint8] | None = None
        owned_seismic_names: npt.NDArray[np.str_] | None = None
        if crosswalk is not None and seismic_names is not None:
            crosswalk_array = np.asarray(crosswalk)
            seismic_name_array = np.asarray(seismic_names)
            if crosswalk_array.ndim != 1 or crosswalk_array.shape != names.shape:
                raise DataFileError(
                    "seismic crosswalk must be one-dimensional and match geographical names"
                )
            if crosswalk_array.dtype != np.dtype(np.uint8):
                raise DataFileError(
                    f"seismic crosswalk must use uint8, got {crosswalk_array.dtype}"
                )
            if crosswalk_array[0] != 0:
                raise DataFileError("seismic crosswalk must reserve sentinel value 0 at index 0")
            _validate_name_array(seismic_name_array, "seismic-region names")
            if int(crosswalk_array.max()) >= seismic_name_array.size:
                raise DataFileError("seismic crosswalk references an unknown seismic region")
            if np.any(crosswalk_array[used] == 0):
                raise DataFileError(
                    "seismic crosswalk omits a geographical region used by the table"
                )
            if np.any(seismic_name_array[np.unique(crosswalk_array[crosswalk_array > 0])] == ""):
                raise DataFileError("seismic crosswalk references an unnamed seismic region")
            owned_crosswalk = np.array(crosswalk_array, copy=True, order="C")
            owned_crosswalk.setflags(write=False)
            owned_seismic_names = np.array(seismic_name_array, copy=True, order="C")
            owned_seismic_names.setflags(write=False)

        owned_table = np.array(table, copy=True, order="C")
        owned_table.setflags(write=False)
        owned_names = np.array(names, copy=True, order="C")
        owned_names.setflags(write=False)
        object.__setattr__(self, "table", owned_table)
        object.__setattr__(self, "names", owned_names)
        object.__setattr__(self, "seismic_by_geographic", owned_crosswalk)
        object.__setattr__(self, "seismic_names", owned_seismic_names)
        object.__setattr__(self, "_active_geographic", active_geographic)

    @property
    def has_seismic_data(self) -> bool:
        """Return whether this engine can perform seismic-region operations."""

        return self.seismic_by_geographic is not None

    def lookup_geographic_number(
        self, longitude: ScalarCoordinate, latitude: ScalarCoordinate
    ) -> int:
        """Return the geographical-region number for one coordinate pair."""

        _validate_scalar_coordinate_types(longitude, latitude)
        _validate_scalar_coordinate_values(longitude, latitude)
        normalized_longitude = 180 if longitude == -180 else longitude
        absolute_longitude = _absolute_degree_index(normalized_longitude)
        absolute_latitude = _absolute_degree_index(latitude)
        quadrant = int(normalized_longitude < 0) + 2 * int(latitude < 0)
        return int(self.table[quadrant, absolute_latitude, absolute_longitude])

    def lookup_number(self, longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
        """Compatibility alias for :meth:`lookup_geographic_number`."""

        return self.lookup_geographic_number(longitude, latitude)

    def lookup_geographic_region(
        self, longitude: ScalarCoordinate, latitude: ScalarCoordinate
    ) -> GeographicRegion:
        """Return the geographical-region number and packaged name."""

        number = self.lookup_geographic_number(longitude, latitude)
        return GeographicRegion(number=number, name=self.geographic_number_to_name(number))

    def lookup_region(self, longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> Region:
        """Compatibility alias for :meth:`lookup_geographic_region`."""

        return self.lookup_geographic_region(longitude, latitude)

    def lookup_geographic_numbers(self, coordinates: npt.ArrayLike) -> GeographicNumberArray:
        """Return geographical-region numbers for a two-column coordinate array."""

        array = _coordinate_array(coordinates)
        if array.shape[0] == 0:
            return np.empty(0, dtype=np.uint16)
        longitude = array[:, 0]
        latitude = array[:, 1]
        _validate_coordinate_values(longitude, latitude)
        return self._lookup_validated(longitude, latitude)

    def _lookup_geographic_numbers_from_vectors(
        self, longitude: npt.ArrayLike, latitude: npt.ArrayLike
    ) -> GeographicNumberArray:
        """Lookup geographical numbers from separate package-internal vectors.

        This path is for package adapters that already own separate longitude
        and latitude arrays. It avoids materializing an ``(n, 2)`` coordinate
        matrix while preserving the same dtype, validation, and FE cell-ownership
        semantics as :meth:`lookup_geographic_numbers`. Inputs must be
        one-dimensional and have equal lengths. Broadcasting is not supported.
        """

        longitude_array, latitude_array = _coordinate_vectors(longitude, latitude)
        if longitude_array.size == 0:
            return np.empty(0, dtype=np.uint16)
        _validate_coordinate_values(longitude_array, latitude_array)
        return self._lookup_validated(longitude_array, latitude_array)

    def lookup_numbers(self, coordinates: npt.ArrayLike) -> GeographicNumberArray:
        """Compatibility alias for :meth:`lookup_geographic_numbers`."""

        return self.lookup_geographic_numbers(coordinates)

    def geographic_number_to_name(self, number: int) -> str:
        """Return the packaged geographical-region name for one active number."""

        index = _scalar_region_index(
            number,
            self.names,
            "geographical",
            active=self._active_geographic,
        )
        return str(self.names[index])

    def number_to_name(self, number: int) -> str:
        """Compatibility alias for :meth:`geographic_number_to_name`."""

        return self.geographic_number_to_name(number)

    def geographic_numbers_to_names(self, numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
        """Convert geographical-region numbers to same-shape packaged names."""

        return _numbers_to_names(
            numbers,
            self.names,
            "geographical",
            active=self._active_geographic,
        )

    def numbers_to_names(self, numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
        """Compatibility alias for :meth:`geographic_numbers_to_names`."""

        return self.geographic_numbers_to_names(numbers)

    def geographic_to_seismic_number(self, number: int) -> int:
        """Return the seismic parent of one active geographical-region number."""

        crosswalk, _ = self._require_seismic_data()
        index = _scalar_region_index(
            number,
            self.names,
            "geographical",
            active=self._active_geographic,
        )
        seismic = int(crosswalk[index])
        if seismic == 0:
            raise RegionNumberError(f"geographical region {index} has no active seismic mapping")
        return seismic

    def geographic_numbers_to_seismic_numbers(self, numbers: npt.ArrayLike) -> SeismicNumberArray:
        """Convert geographical-region numbers to same-shape seismic numbers."""

        crosswalk, _ = self._require_seismic_data()
        array = _integer_region_array(
            numbers,
            self.names,
            "geographical",
            active=self._active_geographic,
        )
        if array.size == 0:
            return np.empty(array.shape, dtype=np.uint8)
        result = crosswalk[array]
        if np.any(result == 0):
            raise RegionNumberError(
                "one or more geographical regions have no active seismic mapping"
            )
        return cast(SeismicNumberArray, result)

    def lookup_seismic_number(self, longitude: ScalarCoordinate, latitude: ScalarCoordinate) -> int:
        """Return the seismic-region number for one coordinate pair."""

        return self.geographic_to_seismic_number(self.lookup_geographic_number(longitude, latitude))

    def lookup_seismic_region(
        self, longitude: ScalarCoordinate, latitude: ScalarCoordinate
    ) -> SeismicRegion:
        """Return the seismic-region number and packaged name for one coordinate pair."""

        number = self.lookup_seismic_number(longitude, latitude)
        return SeismicRegion(number=number, name=self.seismic_number_to_name(number))

    def lookup_seismic_numbers(self, coordinates: npt.ArrayLike) -> SeismicNumberArray:
        """Return seismic-region numbers for a two-column coordinate array."""

        geographic = self.lookup_geographic_numbers(coordinates)
        return self._seismic_numbers_for_lookup_result(geographic)

    def _lookup_seismic_numbers_from_vectors(
        self, longitude: npt.ArrayLike, latitude: npt.ArrayLike
    ) -> SeismicNumberArray:
        """Lookup seismic numbers from separate package-internal vectors."""

        geographic = self._lookup_geographic_numbers_from_vectors(longitude, latitude)
        return self._seismic_numbers_for_lookup_result(geographic)

    def _active_geographic_numbers_for_seismic(self, seismic_number: int) -> GeographicNumberArray:
        """Return active geographical children of one seismic region.

        Membership is derived from this engine's active geographical mask and
        hierarchy crosswalk together. Populated crosswalk slots for identifiers
        that are not used by the geographical lookup table remain inactive and
        are therefore excluded. This helper is package-internal; callers that
        supply arbitrary region numbers must continue to use the validating
        public conversion APIs.
        """

        crosswalk, _ = self._require_seismic_data()
        active = np.flatnonzero(self._active_geographic).astype(np.uint16, copy=False)
        return cast(GeographicNumberArray, active[crosswalk[active] == seismic_number])

    def _seismic_numbers_for_lookup_result(
        self, geographic: GeographicNumberArray
    ) -> SeismicNumberArray:
        """Map a geographical result produced by this engine to seismic numbers.

        The input is trusted only when it comes directly from this engine's
        validated dense-table lookup. Constructor invariants guarantee a nonzero
        seismic mapping for every geographical number used by the table.
        Arbitrary caller data must continue to use
        :meth:`geographic_numbers_to_seismic_numbers`, which validates it.
        """

        crosswalk, _ = self._require_seismic_data()
        return cast(SeismicNumberArray, crosswalk[geographic])

    def seismic_number_to_name(self, number: int) -> str:
        """Return the packaged seismic-region name for one region number."""

        _, names = self._require_seismic_data()
        index = _scalar_region_index(number, names, "seismic")
        return str(names[index])

    def seismic_numbers_to_names(self, numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
        """Convert seismic-region numbers to same-shape packaged names."""

        _, names = self._require_seismic_data()
        return _numbers_to_names(numbers, names, "seismic")

    def _require_seismic_data(
        self,
    ) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.str_]]:
        """Return seismic assets or fail explicitly for geographical-only engines."""

        if self.seismic_by_geographic is None or self.seismic_names is None:
            raise SeismicDataUnavailableError(
                "this FlinnEngdahlLookup was constructed without seismic hierarchy data"
            )
        return self.seismic_by_geographic, self.seismic_names

    def _lookup_validated(
        self,
        longitude: np.ndarray,
        latitude: np.ndarray,
    ) -> GeographicNumberArray:
        """Lookup validated coordinate arrays without narrowing their source dtype.

        FE cell ownership is discontinuous at integer degrees. Preserving the
        validated dtype until absolute integer indices and quadrant ownership are
        established prevents extended-precision values immediately beside a
        boundary from being rounded into the adjacent cell. Exact ``-180`` keeps
        longitude index 180 but uses the east-side quadrant by package convention.
        """

        absolute_longitude = np.abs(longitude).astype(np.uint8)
        absolute_latitude = np.abs(latitude).astype(np.uint8)
        west = (longitude < 0) & (longitude != -180)
        quadrant = west.astype(np.uint8) + 2 * (latitude < 0).astype(np.uint8)
        return cast(
            GeographicNumberArray,
            self.table[quadrant, absolute_latitude, absolute_longitude],
        )


def _validate_name_array(names: np.ndarray, label: str) -> None:
    """Validate one one-based Unicode name array."""

    if names.ndim != 1:
        raise DataFileError(f"{label} must be one-dimensional, got {names.shape}")
    if names.dtype.kind != "U":
        raise DataFileError(f"{label} must use a Unicode dtype, got {names.dtype}")
    if names.size < 2 or names[0] != "":
        raise DataFileError(f"{label} must reserve empty index 0")


def _scalar_region_index(
    number: int,
    names: np.ndarray,
    level: str,
    *,
    active: npt.NDArray[np.bool_] | None = None,
) -> int:
    """Validate one active integer region number for a one-based name table."""

    if isinstance(number, (bool, np.bool_)):
        raise RegionNumberError(f"{level} region number must be an integer, not Boolean")
    try:
        index = operator.index(number)
    except TypeError as exc:
        raise RegionNumberError(f"{level} region number must be an integer") from exc
    if (
        index < 1
        or index >= names.size
        or names[index] == ""
        or (active is not None and not bool(active[index]))
    ):
        raise RegionNumberError(f"unknown Flinn-Engdahl {level} region number: {index}")
    return index


def _integer_region_array(
    numbers: npt.ArrayLike,
    names: np.ndarray,
    level: str,
    *,
    active: npt.NDArray[np.bool_] | None = None,
) -> np.ndarray:
    """Validate an integer region-number array without changing its shape."""

    try:
        array = np.asarray(numbers)
    except ValueError as exc:
        raise RegionNumberError(f"{level} region numbers must form a rectangular array") from exc
    if array.dtype.kind not in "iu" or array.dtype.kind == "b":
        raise RegionNumberError(f"{level} region numbers must use an integer dtype")
    if array.size == 0:
        return array
    if np.any(array < 1) or np.any(array >= names.size):
        raise RegionNumberError(f"one or more Flinn-Engdahl {level} region numbers are unknown")
    if np.any(names[array] == ""):
        raise RegionNumberError(f"one or more Flinn-Engdahl {level} region numbers are unknown")
    if active is not None and np.any(~active[array]):
        raise RegionNumberError(f"one or more Flinn-Engdahl {level} region numbers are inactive")
    return array


def _numbers_to_names(
    numbers: npt.ArrayLike,
    names: npt.NDArray[np.str_],
    level: str,
    *,
    active: npt.NDArray[np.bool_] | None = None,
) -> npt.NDArray[np.str_]:
    """Convert a validated region-number array through one name table."""

    array = _integer_region_array(numbers, names, level, active=active)
    if array.size == 0:
        return np.empty(array.shape, dtype=names.dtype)
    return cast(npt.NDArray[np.str_], names[array])


def _validate_scalar_coordinate_types(
    longitude: ScalarCoordinate, latitude: ScalarCoordinate
) -> None:
    """Reject scalar types that the public coordinate contract does not accept."""

    for value in (longitude, latitude):
        if isinstance(value, (bool, np.bool_)):
            raise CoordinateTypeError("coordinates must be real numbers, not Boolean values")
        if not isinstance(value, (int, float, np.integer, np.floating)):
            raise CoordinateTypeError("coordinates must be real numbers")


def _validate_scalar_coordinate_values(
    longitude: ScalarCoordinate, latitude: ScalarCoordinate
) -> None:
    """Validate scalar finiteness and ranges without creating NumPy arrays."""

    if not _scalar_is_finite(longitude):
        raise CoordinateValueError("longitude is NaN or infinite")
    if not _scalar_is_finite(latitude):
        raise CoordinateValueError("latitude is NaN or infinite")
    if longitude < -180 or longitude > 180:
        raise CoordinateRangeError("longitude must be within [-180, 180]")
    if latitude < -90 or latitude > 90:
        raise CoordinateRangeError("latitude must be within [-90, 90]")


def _absolute_degree_index(value: ScalarCoordinate) -> int:
    """Return the non-negative integer-degree index for a validated scalar.

    NumPy scalar stubs expose the result of ``abs()`` more broadly than the
    runtime scalar-coordinate contract.  The scalar type validator guarantees
    that accepted values support integer conversion.  This cast records that
    fact for static type checking without narrowing extended floating values.
    """

    return int(cast(SupportsInt, abs(value)))


def _scalar_is_finite(value: ScalarCoordinate) -> bool:
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


def _coordinate_vectors(
    longitude: npt.ArrayLike, latitude: npt.ArrayLike
) -> tuple[np.ndarray, np.ndarray]:
    """Validate separate coordinate-vector shape and dtype without copying.

    The package-internal split path accepts only one-dimensional vectors with
    identical shapes. It intentionally does not broadcast inputs. Value
    validation remains separate so finiteness and range checks run in each
    source dtype.
    """

    try:
        longitude_array = np.asarray(longitude)
        latitude_array = np.asarray(latitude)
    except ValueError as exc:
        raise CoordinateShapeError(
            "longitude and latitude must form one-dimensional arrays"
        ) from exc

    for name, array in (("longitude", longitude_array), ("latitude", latitude_array)):
        if array.ndim != 1:
            raise CoordinateShapeError(f"{name} must be one-dimensional, got shape {array.shape}")
        if array.dtype.kind not in _NUMERIC_KINDS:
            raise CoordinateTypeError(
                f"{name} must use an integer or floating dtype, got {array.dtype}"
            )

    if longitude_array.shape != latitude_array.shape:
        raise CoordinateShapeError(
            "longitude and latitude must have identical one-dimensional shapes, "
            f"got {longitude_array.shape} and {latitude_array.shape}"
        )
    return longitude_array, latitude_array


def _validate_coordinate_values(longitude: np.ndarray, latitude: np.ndarray) -> None:
    """Validate coordinate values in their source dtype."""

    if not np.all(np.isfinite(longitude)):
        raise CoordinateValueError("longitude contains a NaN or infinite value")
    if not np.all(np.isfinite(latitude)):
        raise CoordinateValueError("latitude contains a NaN or infinite value")
    if np.any((longitude < -180.0) | (longitude > 180.0)):
        raise CoordinateRangeError("longitude must be within [-180, 180]")
    if np.any((latitude < -90.0) | (latitude > 90.0)):
        raise CoordinateRangeError("latitude must be within [-90, 90]")
