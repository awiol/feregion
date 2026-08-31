"""Internal batch optimization contracts and trusted hierarchy composition.

These tests protect the package-internal split-vector path used by adapters and
its trusted coordinate-to-seismic composition. The public matrix API remains the
supported external batch contract.
"""

from __future__ import annotations

import numpy as np
import pytest

import feregion
from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import (
    CoordinateShapeError,
    CoordinateTypeError,
    SeismicDataUnavailableError,
)
from tests.helpers import raises_exact


@pytest.mark.parametrize("dtype", [np.int32, np.float32, np.float64, np.longdouble])
def test_internal_split_geographic_matches_public_matrix(dtype: type[np.generic]) -> None:
    """Separate coordinate vectors preserve public matrix lookup semantics."""

    longitude = np.asarray([-180, -12.75, -0.0, 0.0, 12.75, 180], dtype=dtype)
    latitude = np.asarray([10, 48.5, -0.0, 0.0, -48.5, -10], dtype=dtype)
    coordinates = np.column_stack((longitude, latitude))
    engine = feregion.get_default_lookup()

    expected = engine.lookup_geographic_numbers(coordinates)
    observed = engine._lookup_geographic_numbers_from_vectors(longitude, latitude)
    np.testing.assert_array_equal(observed, expected)


def test_internal_split_rejects_mismatched_lengths() -> None:
    """The internal split path does not broadcast coordinate vectors."""

    engine = feregion.get_default_lookup()
    with raises_exact(CoordinateShapeError):
        engine._lookup_geographic_numbers_from_vectors([1.0, 2.0], [3.0])


def test_internal_split_rejects_non_vector_shape() -> None:
    """Each split coordinate input must be one-dimensional."""

    engine = feregion.get_default_lookup()
    with raises_exact(CoordinateShapeError):
        engine._lookup_geographic_numbers_from_vectors([[1.0], [2.0]], [3.0, 4.0])


def test_internal_split_rejects_non_numeric_vector() -> None:
    """Split input retains the core numeric-dtype contract."""

    engine = feregion.get_default_lookup()
    with raises_exact(CoordinateTypeError):
        engine._lookup_geographic_numbers_from_vectors(["1"], [2.0])


def test_internal_split_does_not_modify_input_vectors() -> None:
    """Vector lookup does not mutate caller-owned coordinate arrays."""

    longitude = np.asarray([-180.0, 12.75])
    latitude = np.asarray([-10.25, 48.5])
    before_longitude = longitude.copy()
    before_latitude = latitude.copy()

    feregion.get_default_lookup()._lookup_geographic_numbers_from_vectors(longitude, latitude)

    np.testing.assert_array_equal(longitude, before_longitude)
    np.testing.assert_array_equal(latitude, before_latitude)


def test_trusted_seismic_lookup_matches_public_crosswalk_on_all_cell_centers() -> None:
    """Trusted composition is identical to public validated hierarchy conversion."""

    engine = feregion.get_default_lookup()
    longitude = np.arange(-180.0, 180.0) + 0.5
    latitude = np.arange(-90.0, 90.0) + 0.5
    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    longitude_vector = lon_grid.ravel()
    latitude_vector = lat_grid.ravel()
    coordinates = np.column_stack((longitude_vector, latitude_vector))

    geographic = engine.lookup_geographic_numbers(coordinates)
    expected = engine.geographic_numbers_to_seismic_numbers(geographic)
    np.testing.assert_array_equal(engine.lookup_seismic_numbers(coordinates), expected)
    np.testing.assert_array_equal(
        engine._lookup_seismic_numbers_from_vectors(longitude_vector, latitude_vector),
        expected,
    )


def test_internal_split_seismic_requires_explicit_hierarchy() -> None:
    """The optimized path does not attach packaged hierarchy to a custom engine."""

    packaged = feregion.get_default_lookup()
    engine = FlinnEngdahlLookup(packaged.table, packaged.names)
    with raises_exact(SeismicDataUnavailableError):
        engine._lookup_seismic_numbers_from_vectors([12.0], [48.0])
