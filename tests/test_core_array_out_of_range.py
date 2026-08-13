"""Range rejection immediately outside valid Earth coordinate limits."""

import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import CoordinateRangeError
from tests.helpers import raises_exact


@pytest.mark.parametrize(
    "coordinates",
    [
        pytest.param([[-180.000001, 0.0]], id="longitude-below-minimum"),
        pytest.param([[180.000001, 0.0]], id="longitude-above-maximum"),
        pytest.param([[0.0, -90.000001]], id="latitude-below-minimum"),
        pytest.param([[0.0, 90.000001]], id="latitude-above-maximum"),
    ],
)
def test_lookup_numbers_rejects_value_immediately_outside_range(
    lookup: FlinnEngdahlLookup, coordinates: list[list[float]]
) -> None:
    """A finite value just outside a coordinate limit raises CoordinateRangeError."""

    with raises_exact(CoordinateRangeError):
        lookup.lookup_numbers(coordinates)


def test_lookup_numbers_classifies_wide_finite_longdouble_as_out_of_range(
    lookup: FlinnEngdahlLookup,
) -> None:
    """Batch validation checks longdouble range before safe float64 narrowing."""

    import numpy as np

    if np.finfo(np.longdouble).max <= np.finfo(np.float64).max:
        pytest.skip("platform longdouble has no wider finite range than float64")
    longitude = np.longdouble(np.finfo(np.float64).max) * np.longdouble(2)
    coordinates = np.array([[longitude, np.longdouble(0.0)]], dtype=np.longdouble)
    assert np.isfinite(coordinates).all()

    with raises_exact(CoordinateRangeError):
        lookup.lookup_numbers(coordinates)
