"""Construction-time invariants for alternate lookup engines."""

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup
from feregion.exceptions import DataFileError
from tests.helpers import raises_exact


def test_engine_uses_read_only_views_without_freezing_caller_arrays(
    synthetic_table: np.ndarray, synthetic_names: np.ndarray
) -> None:
    """Engine immutability does not impose write protection on caller-owned arrays."""

    engine = FlinnEngdahlLookup(synthetic_table, synthetic_names)
    assert synthetic_table.flags.writeable
    assert synthetic_names.flags.writeable
    assert not engine.table.flags.writeable
    assert not engine.names.flags.writeable


@pytest.mark.parametrize(
    "shape",
    [pytest.param((4, 90, 181), id="latitude"), pytest.param((4, 91, 180), id="longitude")],
)
def test_engine_rejects_wrong_table_shape(
    synthetic_names: np.ndarray, shape: tuple[int, int, int]
) -> None:
    """A table outside the fixed FE dense-table dimensions raises DataFileError."""

    table = np.ones(shape, dtype=np.uint16)
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(table, synthetic_names)


def test_engine_rejects_non_uint16_table(synthetic_names: np.ndarray) -> None:
    """Region table storage is contractually uint16."""

    table = np.ones((4, 91, 181), dtype=np.uint32)
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(table, synthetic_names)


def test_engine_rejects_name_array_without_reserved_zero(synthetic_table: np.ndarray) -> None:
    """Direct name lookup requires empty index zero for one-based FE numbers."""

    names = np.full(int(synthetic_table.max()) + 1, "NAME", dtype="<U8")
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(synthetic_table, names)


def test_engine_rejects_multidimensional_name_array(synthetic_table: np.ndarray) -> None:
    """Direct name storage must be one-dimensional for number indexing."""

    names = np.full((100, 100), "NAME", dtype="<U8")
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(synthetic_table, names)


def test_engine_rejects_non_unicode_name_array(synthetic_table: np.ndarray) -> None:
    """Byte-string name storage is rejected to keep public names as Unicode."""

    names = np.full(int(synthetic_table.max()) + 1, b"NAME", dtype="S8")
    names[0] = b""
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(synthetic_table, names)


def test_engine_rejects_name_array_shorter_than_used_region_numbers() -> None:
    """A direct name table must cover the largest region identifier in the grid."""

    table = np.full((4, 91, 181), 2, dtype=np.uint16)
    names = np.array(["", "ONE"], dtype="<U8")
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(table, names)


def test_engine_rejects_region_zero_in_lookup_table() -> None:
    """FE region zero is invalid even when the names array reserves index zero."""

    table = np.ones((4, 91, 181), dtype=np.uint16)
    table[0, 0, 0] = 0
    names = np.array(["", "ONE"], dtype="<U8")
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(table, names)
