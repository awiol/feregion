"""Narrow deterministic fixtures for core lookup tests."""

from __future__ import annotations

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup


def synthetic_region_number(quadrant: int, latitude: int, longitude: int) -> int:
    """Return a deterministic nonzero uint16-safe value for a synthetic table cell.

    The value is convenient for focused tests but is not globally unique over
    all 65,884 dense-table positions because uint16 has fewer nonzero values.
    Exhaustive index-selection tests use independent axis probe tables instead.
    """

    return 1 + quadrant * 16354 + latitude * 181 + longitude


@pytest.fixture
def synthetic_table() -> np.ndarray:
    """Create a table whose cell value makes quadrant and both indices observable."""

    q = np.arange(4, dtype=np.uint32)[:, None, None]
    lat = np.arange(91, dtype=np.uint32)[None, :, None]
    lon = np.arange(181, dtype=np.uint32)[None, None, :]
    return (1 + q * 16354 + lat * 181 + lon).astype(np.uint16)


@pytest.fixture
def synthetic_names(synthetic_table: np.ndarray) -> np.ndarray:
    """Create direct names for every synthetic region number used by the table."""

    maximum = int(synthetic_table.max())
    names = np.empty(maximum + 1, dtype="<U16")
    names[0] = ""
    for number in range(1, maximum + 1):
        names[number] = f"REGION_{number}"
    return names


@pytest.fixture
def lookup(synthetic_table: np.ndarray, synthetic_names: np.ndarray) -> FlinnEngdahlLookup:
    """Return an isolated lookup engine without package-resource I/O."""

    return FlinnEngdahlLookup(table=synthetic_table, names=synthetic_names)
