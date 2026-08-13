"""Positive and boundary behavior for vectorized numeric lookup."""

from __future__ import annotations

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup
from tests.conftest import synthetic_region_number


@pytest.mark.parametrize(
    ("longitude", "latitude", "quadrant", "abs_lon", "abs_lat"),
    [
        pytest.param(12.0, 48.0, 0, 12, 48, id="northeast"),
        pytest.param(-12.0, 48.0, 1, 12, 48, id="northwest"),
        pytest.param(12.0, -48.0, 2, 12, 48, id="southeast"),
        pytest.param(-12.0, -48.0, 3, 12, 48, id="southwest"),
    ],
)
def test_lookup_numbers_selects_sign_quadrant(
    lookup: FlinnEngdahlLookup,
    longitude: float,
    latitude: float,
    quadrant: int,
    abs_lon: int,
    abs_lat: int,
) -> None:
    """Coordinate signs select the intended quadrant before table indexing."""

    result = lookup.lookup_numbers([[longitude, latitude]])
    assert result.tolist() == [synthetic_region_number(quadrant, abs_lat, abs_lon)]


@pytest.mark.parametrize(
    ("longitude", "latitude", "abs_lon", "abs_lat"),
    [
        pytest.param(0.0, 0.0, 0, 0, id="origin"),
        pytest.param(0.999999, 0.999999, 0, 0, id="below-first-degree"),
        pytest.param(12.999999, 48.999999, 12, 48, id="fractional-positive"),
        pytest.param(179.999999, 89.999999, 179, 89, id="below-upper-limits"),
    ],
)
def test_lookup_numbers_truncates_absolute_fractional_coordinates(
    lookup: FlinnEngdahlLookup,
    longitude: float,
    latitude: float,
    abs_lon: int,
    abs_lat: int,
) -> None:
    """Positive absolute coordinates use truncation toward the integer degree."""

    result = lookup.lookup_numbers([[longitude, latitude]])
    assert result.tolist() == [synthetic_region_number(0, abs_lat, abs_lon)]


def test_lookup_numbers_truncates_fractional_coordinates_after_absolute_value(
    lookup: FlinnEngdahlLookup,
) -> None:
    """Negative fractions are made absolute before they are converted to integers."""

    result = lookup.lookup_numbers([[-12.999999, -48.999999]])
    assert result.tolist() == [synthetic_region_number(3, 48, 12)]


def test_lookup_numbers_treats_negative_zero_as_zero(lookup: FlinnEngdahlLookup) -> None:
    """IEEE negative zero selects the non-negative longitude and latitude quadrant."""

    result = lookup.lookup_numbers([[-0.0, -0.0]])
    assert result.tolist() == [synthetic_region_number(0, 0, 0)]


def test_lookup_numbers_maps_minus_180_to_plus_180_before_quadrant_selection(
    lookup: FlinnEngdahlLookup,
) -> None:
    """Longitude -180 uses the east-side quadrant and longitude index 180."""

    result = lookup.lookup_numbers([[-180.0, 10.0]])
    assert result.tolist() == [synthetic_region_number(0, 10, 180)]


def test_lookup_numbers_maps_minus_180_at_south_to_southeast(
    lookup: FlinnEngdahlLookup,
) -> None:
    """The -180 normalization also precedes quadrant selection south of the equator."""

    result = lookup.lookup_numbers([[-180.0, -10.0]])
    assert result.tolist() == [synthetic_region_number(2, 10, 180)]


def test_lookup_numbers_accepts_exact_coordinate_limits(lookup: FlinnEngdahlLookup) -> None:
    """All four exact range limits are valid inputs."""

    result = lookup.lookup_numbers([[180.0, 90.0], [180.0, -90.0]])
    assert result.tolist() == [
        synthetic_region_number(0, 90, 180),
        synthetic_region_number(2, 90, 180),
    ]


def test_lookup_numbers_returns_uint16_vector_for_multiple_rows(
    lookup: FlinnEngdahlLookup,
) -> None:
    """One output region number is returned for each input row."""

    coordinates = np.array([[1.0, 2.0], [-3.0, 4.0], [5.0, -6.0]])
    result = lookup.lookup_numbers(coordinates)
    assert result.dtype == np.dtype(np.uint16)
    assert result.shape == (3,)


def test_lookup_numbers_accepts_integer_array(lookup: FlinnEngdahlLookup) -> None:
    """Signed integer coordinate arrays are valid numeric input."""

    result = lookup.lookup_numbers(np.array([[12, -48]], dtype=np.int32))
    assert result.tolist() == [synthetic_region_number(2, 48, 12)]


def test_lookup_numbers_accepts_rectangular_numeric_python_sequence(
    lookup: FlinnEngdahlLookup,
) -> None:
    """A rectangular numeric sequence follows the same two-column array contract."""

    result = lookup.lookup_numbers([[12, 48], [-12, -48]])
    assert result.tolist() == [
        synthetic_region_number(0, 48, 12),
        synthetic_region_number(3, 48, 12),
    ]


def test_lookup_numbers_empty_two_column_input_returns_empty_uint16(
    lookup: FlinnEngdahlLookup,
) -> None:
    """A valid zero-row input produces a zero-row result without special caller handling."""

    result = lookup.lookup_numbers(np.empty((0, 2), dtype=np.float64))
    assert result.shape == (0,)
    assert result.dtype == np.dtype(np.uint16)


def test_lookup_numbers_does_not_modify_input(lookup: FlinnEngdahlLookup) -> None:
    """Normalization of -180 and absolute values does not mutate caller-owned data."""

    coordinates = np.array([[-180.0, -10.25], [12.75, 48.5]])
    before = coordinates.copy()
    lookup.lookup_numbers(coordinates)
    np.testing.assert_array_equal(coordinates, before)
