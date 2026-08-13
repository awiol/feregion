"""Dtype rejection for a correctly shaped coordinate array."""

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import CoordinateTypeError
from tests.helpers import raises_exact


@pytest.mark.parametrize(
    "coordinates",
    [
        pytest.param(np.array([["12", "48"]]), id="numeric-strings"),
        pytest.param(np.array([[object(), object()]], dtype=object), id="objects"),
        pytest.param(np.array([[True, False]], dtype=bool), id="booleans"),
        pytest.param(np.array([[12 + 0j, 48 + 0j]], dtype=complex), id="complex"),
    ],
)
def test_lookup_numbers_rejects_unsupported_dtype(
    lookup: FlinnEngdahlLookup, coordinates: np.ndarray
) -> None:
    """The array API rejects non-real numeric or coercible textual dtypes."""

    with raises_exact(CoordinateTypeError):
        lookup.lookup_numbers(coordinates)
