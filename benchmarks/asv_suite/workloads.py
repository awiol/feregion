"""Deterministic benchmark workloads and independent lightweight invariants."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .contracts import WORKLOAD_SEED


def coordinates(size: int, *, seed: int = WORKLOAD_SEED) -> npt.NDArray[np.float64]:
    """Return a deterministic global coordinate workload with shape ``(size, 2)``."""

    rng = np.random.default_rng(seed + size)
    longitude = rng.uniform(-180.0, 180.0, size=size)
    latitude = rng.uniform(-90.0, 90.0, size=size)
    return np.column_stack((longitude, latitude))


def assert_region_numbers(values: object, *, size: int, maximum: int = 757) -> None:
    """Check shape and numeric range without reproducing the lookup implementation."""

    array = np.asarray(values)
    if array.shape != (size,):
        raise AssertionError(f"expected shape {(size,)}, got {array.shape}")
    if size and (np.any(array < 1) or np.any(array > maximum)):
        raise AssertionError("benchmark result contains an out-of-range region number")
