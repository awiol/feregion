"""Scalar interface behavior and exact scalar failure classes."""

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import CoordinateRangeError, CoordinateTypeError, CoordinateValueError
from feregion.types import Region
from tests.conftest import synthetic_region_number
from tests.helpers import raises_exact


def test_lookup_number_returns_python_int(lookup: FlinnEngdahlLookup) -> None:
    """Scalar lookup returns a Python integer rather than a NumPy scalar."""

    result = lookup.lookup_number(12.0, 48.0)
    assert type(result) is int
    assert result == synthetic_region_number(0, 48, 12)


def test_lookup_region_returns_slotted_region_value(lookup: FlinnEngdahlLookup) -> None:
    """Scalar region lookup combines the number with its direct name mapping."""

    number = synthetic_region_number(0, 48, 12)
    result = lookup.lookup_region(12.0, 48.0)
    assert result == Region(number=number, name=f"REGION_{number}")


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [
        pytest.param("12", 48.0, id="string-longitude"),
        pytest.param(12.0, "48", id="string-latitude"),
        pytest.param(True, 48.0, id="boolean-longitude"),
        pytest.param(12.0, False, id="boolean-latitude"),
        pytest.param(None, 48.0, id="none-longitude"),
    ],
)
def test_lookup_number_rejects_non_real_scalar_type(
    lookup: FlinnEngdahlLookup, longitude: object, latitude: object
) -> None:
    """Scalar input rejects textual, Boolean, and absent values without coercion."""

    with raises_exact(CoordinateTypeError):
        lookup.lookup_number(longitude, latitude)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [
        pytest.param(float("nan"), 0.0, id="nan"),
        pytest.param(float("inf"), 0.0, id="positive-infinity"),
        pytest.param(0.0, float("-inf"), id="negative-infinity"),
    ],
)
def test_lookup_number_rejects_non_finite_scalar(
    lookup: FlinnEngdahlLookup, longitude: float, latitude: float
) -> None:
    """A non-finite scalar raises exactly CoordinateValueError."""

    with raises_exact(CoordinateValueError):
        lookup.lookup_number(longitude, latitude)


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [
        pytest.param(-181.0, 0.0, id="longitude-low"),
        pytest.param(181.0, 0.0, id="longitude-high"),
        pytest.param(0.0, -91.0, id="latitude-low"),
        pytest.param(0.0, 91.0, id="latitude-high"),
    ],
)
def test_lookup_number_rejects_out_of_range_scalar(
    lookup: FlinnEngdahlLookup, longitude: float, latitude: float
) -> None:
    """A finite scalar outside the Earth coordinate range raises CoordinateRangeError."""

    with raises_exact(CoordinateRangeError):
        lookup.lookup_number(longitude, latitude)


def test_lookup_number_accepts_numpy_real_scalars(lookup: FlinnEngdahlLookup) -> None:
    """NumPy integer and floating scalar values are supported scalar inputs."""

    result = lookup.lookup_number(np.int16(12), np.float32(48.5))
    assert result == synthetic_region_number(0, 48, 12)


def test_lookup_number_classifies_wide_finite_longdouble_as_out_of_range(
    lookup: FlinnEngdahlLookup,
) -> None:
    """Finite longdouble overflow on float64 narrowing does not become non-finite input."""

    if np.finfo(np.longdouble).max <= np.finfo(np.float64).max:
        pytest.skip("platform longdouble has no wider finite range than float64")
    longitude = np.longdouble(np.finfo(np.float64).max) * np.longdouble(2)
    assert np.isfinite(longitude)

    with raises_exact(CoordinateRangeError):
        lookup.lookup_number(longitude, np.longdouble(0.0))
