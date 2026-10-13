"""Public split-vector lookup contracts for the 0.6 additive NumPy API.

These tests establish the user-facing behavior for callers that already hold
longitude and latitude as separate one-dimensional vectors. The split interface
must preserve the same FE ownership, validation, custom-engine, dtype, and
hierarchy semantics as the existing ``(n, 2)`` matrix batch interface while
avoiding a caller-side coordinate-matrix materialization.
"""

from __future__ import annotations

import numpy as np
import pytest

import feregion
from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import (
    CoordinateRangeError,
    CoordinateShapeError,
    CoordinateTypeError,
    CoordinateValueError,
    SeismicDataUnavailableError,
)
from tests.helpers import raises_exact


@pytest.mark.parametrize("dtype", [np.int32, np.float32, np.float64, np.longdouble])
def test_engine_split_geographic_matches_matrix(dtype: type[np.generic]) -> None:
    """Engine split lookup returns exactly the matrix geographical result."""

    longitude = np.asarray([-180, -12.75, -0.0, 0.0, 12.75, 180], dtype=dtype)
    latitude = np.asarray([10, 48.5, -0.0, 0.0, -48.5, -10], dtype=dtype)
    coordinates = np.column_stack((longitude, latitude))
    engine = feregion.get_default_lookup()

    expected = engine.lookup_geographic_numbers(coordinates)
    observed = engine.lookup_geographic_numbers_from_vectors(longitude, latitude)
    assert observed.dtype == np.dtype(np.uint16)
    assert observed.shape == longitude.shape
    np.testing.assert_array_equal(observed, expected)


@pytest.mark.parametrize("dtype", [np.int32, np.float32, np.float64, np.longdouble])
def test_engine_split_seismic_matches_matrix(dtype: type[np.generic]) -> None:
    """Engine split lookup returns exactly the matrix seismic result."""

    longitude = np.asarray([-180, -12.75, -0.0, 0.0, 12.75, 180], dtype=dtype)
    latitude = np.asarray([10, 48.5, -0.0, 0.0, -48.5, -10], dtype=dtype)
    coordinates = np.column_stack((longitude, latitude))
    engine = feregion.get_default_lookup()

    expected = engine.lookup_seismic_numbers(coordinates)
    observed = engine.lookup_seismic_numbers_from_vectors(longitude, latitude)
    assert observed.dtype == np.dtype(np.uint8)
    assert observed.shape == longitude.shape
    np.testing.assert_array_equal(observed, expected)


def test_module_split_wrappers_use_default_engine() -> None:
    """Top-level split functions expose the default engine at both FE levels."""

    longitude = np.asarray([12.0, -60.0])
    latitude = np.asarray([48.0, -30.0])
    np.testing.assert_array_equal(
        feregion.lookup_geographic_numbers_from_vectors(longitude, latitude),
        np.asarray([543, 133], dtype=np.uint16),
    )
    np.testing.assert_array_equal(
        feregion.lookup_seismic_numbers_from_vectors(longitude, latitude),
        feregion.lookup_seismic_numbers(np.column_stack((longitude, latitude))),
    )


def test_split_vectors_accept_empty_and_non_contiguous_arrays() -> None:
    """Supported one-dimensional views do not require contiguous storage or nonempty input."""

    engine = feregion.get_default_lookup()
    empty = np.asarray([], dtype=np.float64)
    geographic_empty = engine.lookup_geographic_numbers_from_vectors(empty, empty)
    seismic_empty = engine.lookup_seismic_numbers_from_vectors(empty, empty)
    assert geographic_empty.shape == (0,)
    assert geographic_empty.dtype == np.dtype(np.uint16)
    assert seismic_empty.shape == (0,)
    assert seismic_empty.dtype == np.dtype(np.uint8)

    longitude_storage = np.asarray([12.0, 999.0, -60.0, 999.0])
    latitude_storage = np.asarray([48.0, 999.0, -30.0, 999.0])
    longitude = longitude_storage[::2]
    latitude = latitude_storage[::2]
    assert not longitude.flags.c_contiguous
    assert not latitude.flags.c_contiguous
    np.testing.assert_array_equal(
        engine.lookup_geographic_numbers_from_vectors(longitude, latitude),
        engine.lookup_geographic_numbers(np.column_stack((longitude, latitude))),
    )


def test_split_vectors_do_not_modify_caller_arrays() -> None:
    """Public split lookup is read-only with respect to caller-owned coordinate vectors."""

    longitude = np.asarray([-180.0, 12.75])
    latitude = np.asarray([-10.25, 48.5])
    before_longitude = longitude.copy()
    before_latitude = latitude.copy()

    feregion.lookup_geographic_numbers_from_vectors(longitude, latitude)

    np.testing.assert_array_equal(longitude, before_longitude)
    np.testing.assert_array_equal(latitude, before_latitude)


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [
        ([1.0, 2.0], [3.0]),
        ([[1.0], [2.0]], [3.0, 4.0]),
        ([1.0, 2.0], [[3.0], [4.0]]),
        (1.0, [2.0]),
    ],
)
def test_split_vectors_reject_shape_mismatch_without_broadcasting(
    longitude: object, latitude: object
) -> None:
    """The additive split API requires equal one-dimensional shapes and never broadcasts."""

    with raises_exact(CoordinateShapeError):
        feregion.lookup_geographic_numbers_from_vectors(longitude, latitude)


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [
        (["1"], [2.0]),
        ([1.0], ["2"]),
        ([True], [2.0]),
        ([1.0], [False]),
        ([1.0 + 0j], [2.0]),
    ],
)
def test_split_vectors_reject_non_real_numeric_dtypes(longitude: object, latitude: object) -> None:
    """String, Boolean, object-like, and complex coordinate vectors remain invalid."""

    with raises_exact(CoordinateTypeError):
        feregion.lookup_geographic_numbers_from_vectors(longitude, latitude)


@pytest.mark.parametrize(
    ("function_name", "longitude", "latitude", "error_type"),
    [
        ("lookup_geographic_numbers_from_vectors", [np.nan], [0.0], CoordinateValueError),
        ("lookup_geographic_numbers_from_vectors", [0.0], [np.inf], CoordinateValueError),
        ("lookup_geographic_numbers_from_vectors", [180.0001], [0.0], CoordinateRangeError),
        ("lookup_geographic_numbers_from_vectors", [0.0], [-90.0001], CoordinateRangeError),
        ("lookup_seismic_numbers_from_vectors", [np.nan], [0.0], CoordinateValueError),
        ("lookup_seismic_numbers_from_vectors", [-180.0001], [0.0], CoordinateRangeError),
    ],
)
def test_split_vectors_preserve_coordinate_value_and_range_errors(
    function_name: str,
    longitude: object,
    latitude: object,
    error_type: type[Exception],
) -> None:
    """Split lookup uses the established finite-value and Earth-range exception classes."""

    function = getattr(feregion, function_name)
    with raises_exact(error_type):
        function(longitude, latitude)


def test_split_geographic_supports_explicit_geographical_only_engine() -> None:
    """The geographical split method remains usable on an explicit two-array engine."""

    packaged = feregion.get_default_lookup()
    engine = FlinnEngdahlLookup(packaged.table, packaged.names)
    np.testing.assert_array_equal(
        engine.lookup_geographic_numbers_from_vectors([12.0], [48.0]),
        np.asarray([543], dtype=np.uint16),
    )


def test_split_seismic_requires_hierarchy_on_explicit_engine() -> None:
    """The seismic split method does not borrow packaged hierarchy for a custom engine."""

    packaged = feregion.get_default_lookup()
    engine = FlinnEngdahlLookup(packaged.table, packaged.names)
    with raises_exact(SeismicDataUnavailableError):
        engine.lookup_seismic_numbers_from_vectors([12.0], [48.0])
