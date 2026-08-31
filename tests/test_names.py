"""Scalar and array region-number-to-name contracts."""

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import RegionNumberError
from tests.helpers import raises_exact


def test_number_to_name_returns_python_string(lookup: FlinnEngdahlLookup) -> None:
    """A valid Python integer maps to one Python string."""

    result = lookup.number_to_name(543)
    assert type(result) is str
    assert result == "REGION_543"


def test_number_to_name_accepts_numpy_integer(lookup: FlinnEngdahlLookup) -> None:
    """NumPy integer scalar region numbers satisfy the scalar integer contract."""

    assert lookup.number_to_name(np.uint16(543)) == "REGION_543"


@pytest.mark.parametrize(
    "number",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(65534, id="above-synthetic-maximum"),
        pytest.param(543.0, id="float"),
        pytest.param("543", id="string"),
        pytest.param(True, id="boolean"),
    ],
)
def test_number_to_name_rejects_invalid_number(lookup: FlinnEngdahlLookup, number: object) -> None:
    """Invalid scalar region identifiers raise exactly RegionNumberError."""

    with raises_exact(RegionNumberError):
        lookup.number_to_name(number)  # type: ignore[arg-type]


def test_numbers_to_names_scalar_array_like_returns_zero_dimensional_array(
    lookup: FlinnEngdahlLookup,
) -> None:
    """A scalar ArrayLike still satisfies the documented ndarray return contract."""

    result = lookup.numbers_to_names(543)
    assert type(result) is np.ndarray
    assert result.shape == ()
    assert result.dtype.kind == "U"
    assert result.item() == "REGION_543"


def test_numbers_to_names_preserves_multidimensional_shape(lookup: FlinnEngdahlLookup) -> None:
    """Vector name conversion preserves the caller's region-number array shape."""

    numbers = np.array([[1, 2], [543, 544]], dtype=np.uint16)
    result = lookup.numbers_to_names(numbers)
    assert result.shape == (2, 2)
    assert result.tolist() == [["REGION_1", "REGION_2"], ["REGION_543", "REGION_544"]]


def test_numbers_to_names_empty_array_preserves_shape_and_unicode_dtype(
    lookup: FlinnEngdahlLookup,
) -> None:
    """An empty integer array returns an empty Unicode array with the same shape."""

    result = lookup.numbers_to_names(np.empty((2, 0), dtype=np.uint16))
    assert result.shape == (2, 0)
    assert result.dtype.kind == "U"


@pytest.mark.parametrize(
    "numbers",
    [
        pytest.param(np.array([0], dtype=np.uint16), id="zero"),
        pytest.param(np.array([-1], dtype=np.int64), id="negative"),
        pytest.param(np.array([65534], dtype=np.int64), id="above-maximum"),
        pytest.param(np.array([543.0]), id="float-dtype"),
        pytest.param(np.array(["543"]), id="string-dtype"),
        pytest.param(np.array([True]), id="boolean-dtype"),
    ],
)
def test_numbers_to_names_rejects_invalid_array(
    lookup: FlinnEngdahlLookup, numbers: np.ndarray
) -> None:
    """Invalid vector region identifiers raise exactly RegionNumberError."""

    with raises_exact(RegionNumberError):
        lookup.numbers_to_names(numbers)


def test_numbers_to_names_rejects_ragged_sequence(lookup: FlinnEngdahlLookup) -> None:
    """A ragged region sequence cannot produce a shape-preserving result."""

    with raises_exact(RegionNumberError):
        lookup.numbers_to_names([[1, 2], [3]])


def test_numbers_to_names_rejects_empty_mapping_not_used_by_lookup_table() -> None:
    """Name conversion rejects an empty direct mapping even if lookup never emits it."""

    table = np.ones((4, 91, 181), dtype=np.uint16)
    names = np.array(["", "ONE", ""], dtype="<U8")
    engine = FlinnEngdahlLookup(table, names)
    with raises_exact(RegionNumberError):
        engine.numbers_to_names(np.array([2], dtype=np.uint16))
