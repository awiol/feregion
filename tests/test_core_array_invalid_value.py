"""Non-finite numeric rejection for array lookup."""

import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import CoordinateValueError
from tests.helpers import raises_exact


@pytest.mark.parametrize(
    "coordinates",
    [
        pytest.param([[float("nan"), 0.0]], id="longitude-nan"),
        pytest.param([[float("inf"), 0.0]], id="longitude-positive-infinity"),
        pytest.param([[float("-inf"), 0.0]], id="longitude-negative-infinity"),
        pytest.param([[0.0, float("nan")]], id="latitude-nan"),
        pytest.param([[0.0, float("inf")]], id="latitude-positive-infinity"),
        pytest.param([[0.0, float("-inf")]], id="latitude-negative-infinity"),
    ],
)
def test_lookup_numbers_rejects_non_finite_coordinate(
    lookup: FlinnEngdahlLookup, coordinates: list[list[float]]
) -> None:
    """Every non-finite coordinate class raises exactly CoordinateValueError."""

    with raises_exact(CoordinateValueError):
        lookup.lookup_numbers(coordinates)
