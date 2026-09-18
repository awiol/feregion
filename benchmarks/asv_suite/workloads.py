"""Deterministic benchmark workloads and independent untimed correctness checks."""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from .contracts import WORKLOAD_SEED
from .source_oracle import (
    SourceReference,
    geographic_to_seismic,
    sample_indices,
    seismic_names,
    source_reference,
)


def coordinates(size: int, *, seed: int = WORKLOAD_SEED) -> npt.NDArray[np.float64]:
    """Return a deterministic global coordinate workload with shape ``(size, 2)``."""

    rng = np.random.default_rng(seed + size)
    longitude = rng.uniform(-180.0, 180.0, size=size)
    latitude = rng.uniform(-90.0, 90.0, size=size)
    return np.column_stack((longitude, latitude))


def assert_region_numbers(values: object, *, size: int, maximum: int = 757) -> None:
    """Check structural number invariants before applying semantic oracle checks."""

    array = np.asarray(values)
    if array.shape != (size,):
        raise AssertionError(f"expected shape {(size,)}, got {array.shape}")
    if size and (np.any(array < 1) or np.any(array > maximum)):
        raise AssertionError("benchmark result contains an out-of-range region number")


def expected_geographic_numbers(
    coordinate_values: npt.NDArray[np.float64],
    *,
    reference: SourceReference | None = None,
) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.uint16]]:
    """Return bounded sampled indices and direct source-oracle geographic numbers."""

    oracle = source_reference() if reference is None else reference
    indices = sample_indices(coordinate_values.shape[0])
    expected = np.fromiter(
        (
            oracle.number(float(coordinate_values[index, 0]), float(coordinate_values[index, 1]))
            for index in indices
        ),
        dtype=np.uint16,
        count=len(indices),
    )
    return indices, expected


def assert_geographic_numbers_match_source(
    values: object,
    coordinate_values: npt.NDArray[np.float64],
    *,
    reference: SourceReference | None = None,
) -> None:
    """Require sampled geographical identities to match the pinned source-table scanner."""

    array = np.asarray(values)
    assert_region_numbers(array, size=coordinate_values.shape[0])
    indices, expected = expected_geographic_numbers(coordinate_values, reference=reference)
    np.testing.assert_array_equal(array[indices], expected)


def assert_geographic_names_match_source(
    values: object,
    geographic_numbers: object,
    *,
    reference: SourceReference | None = None,
) -> None:
    """Require sampled geographic names to match pinned source names."""

    oracle = source_reference() if reference is None else reference
    numbers = np.asarray(geographic_numbers)
    names = np.asarray(values)
    if names.shape != numbers.shape:
        raise AssertionError("geographic name conversion changed result shape")
    indices = sample_indices(numbers.size)
    expected = np.asarray([oracle.name(int(numbers[index])) for index in indices])
    np.testing.assert_array_equal(names[indices], expected)


def expected_seismic_numbers(
    coordinate_values: npt.NDArray[np.float64],
    *,
    reference: SourceReference | None = None,
) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.uint8]]:
    """Return sampled seismic identities from source geographic lookup plus crosswalk."""

    indices, geographic = expected_geographic_numbers(coordinate_values, reference=reference)
    crosswalk = geographic_to_seismic()
    return indices, crosswalk[geographic]


def assert_seismic_numbers_match_source(
    values: object,
    coordinate_values: npt.NDArray[np.float64],
    *,
    reference: SourceReference | None = None,
) -> None:
    """Require sampled seismic identities to match source geographic lookup plus crosswalk."""

    array = np.asarray(values)
    assert_region_numbers(array, size=coordinate_values.shape[0], maximum=50)
    indices, expected = expected_seismic_numbers(coordinate_values, reference=reference)
    np.testing.assert_array_equal(array[indices], expected)


def assert_crosswalk_matches_source(
    values: object,
    geographic_numbers: object,
) -> None:
    """Require sampled hierarchy conversion to match the project oracle crosswalk."""

    geographic = np.asarray(geographic_numbers)
    seismic = np.asarray(values)
    if seismic.shape != geographic.shape:
        raise AssertionError("seismic crosswalk changed result shape")
    assert_region_numbers(seismic, size=geographic.size, maximum=50)
    indices = sample_indices(geographic.size)
    expected = geographic_to_seismic()[geographic[indices]]
    np.testing.assert_array_equal(seismic[indices], expected)


def assert_seismic_names_match_oracle(values: object, seismic_numbers_value: object) -> None:
    """Require sampled seismic names to match the project-owned name oracle."""

    numbers = np.asarray(seismic_numbers_value)
    names = np.asarray(values)
    if names.shape != numbers.shape:
        raise AssertionError("seismic name conversion changed result shape")
    indices = sample_indices(numbers.size)
    expected = seismic_names()[numbers[indices]]
    np.testing.assert_array_equal(names[indices], expected)


def assert_region_object(
    region: Any,
    *,
    expected_number: int,
    expected_name: str,
) -> None:
    """Require one returned Region-like object to carry the expected identity and name."""

    if int(region.number) != expected_number:
        raise AssertionError("region object contains the wrong region number")
    if str(region.name) != expected_name:
        raise AssertionError("region object contains the wrong region name")
