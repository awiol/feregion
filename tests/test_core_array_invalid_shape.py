"""Shape rejection for the vectorized public contract."""

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import CoordinateShapeError
from tests.helpers import raises_exact


@pytest.mark.parametrize(
    "coordinates",
    [
        pytest.param(12.0, id="scalar"),
        pytest.param([12.0, 48.0], id="one-dimensional-pair"),
        pytest.param(np.empty((2, 1)), id="one-column"),
        pytest.param(np.empty((2, 3)), id="three-columns"),
        pytest.param(np.empty((1, 2, 1)), id="three-dimensional"),
    ],
)
def test_lookup_numbers_rejects_non_two_column_shape(
    lookup: FlinnEngdahlLookup, coordinates: object
) -> None:
    """Inputs outside the exact (n, 2) contract raise CoordinateShapeError."""

    with raises_exact(CoordinateShapeError):
        lookup.lookup_numbers(coordinates)


def test_lookup_numbers_rejects_ragged_sequence_as_shape_error(
    lookup: FlinnEngdahlLookup,
) -> None:
    """A ragged sequence cannot form the required rectangular coordinate array."""

    with raises_exact(CoordinateShapeError):
        lookup.lookup_numbers([[1.0, 2.0], [3.0]])
