"""pytest-benchmark coverage for in-process feregion lookup interfaces.

Run with:
    pytest benchmarks --benchmark-only --benchmark-json=benchmark.json

CLI and GeoJSON operations are intentionally excluded from this lookup suite.
ObsPy is a development-only scalar baseline when installed.
"""

from __future__ import annotations

import numpy as np
import pytest

import feregion
from tools.obspy_fe_source import DEFAULT_SOURCE_DIR, verify_source_dir


@pytest.fixture(scope="module")
def scalar_coordinates() -> np.ndarray:
    """Return one deterministic workload shared by scalar candidate baselines."""

    rng = np.random.default_rng(20260823)
    return np.column_stack((rng.uniform(-180, 180, 10_000), rng.uniform(-90, 90, 10_000)))


@pytest.fixture(
    scope="module",
    params=[1, 100, 1_000, 10_000, 100_000, 1_000_000],
    ids=lambda n: f"n={n}",
)
def coordinates(request) -> np.ndarray:
    """Return deterministic global coordinate arrays for vectorized benchmarks."""

    rng = np.random.default_rng(20260813 + request.param)
    return np.column_stack(
        (rng.uniform(-180, 180, request.param), rng.uniform(-90, 90, request.param))
    )


def test_scalar_number_lookup(benchmark, scalar_coordinates: np.ndarray) -> None:
    """Measure package-level scalar region-number lookup over 10,000 points."""

    expected = feregion.lookup_numbers(scalar_coordinates)

    def run() -> np.ndarray:
        return np.fromiter(
            (feregion.lookup_number(lon, lat) for lon, lat in scalar_coordinates),
            dtype=np.uint16,
            count=scalar_coordinates.shape[0],
        )

    result = benchmark(run)
    np.testing.assert_array_equal(result, expected)


def test_scalar_region_lookup(benchmark, scalar_coordinates: np.ndarray) -> None:
    """Measure scalar Region construction over the same 10,000-point workload."""

    expected = feregion.lookup_numbers(scalar_coordinates)

    def run() -> np.ndarray:
        return np.fromiter(
            (feregion.lookup_region(lon, lat).number for lon, lat in scalar_coordinates),
            dtype=np.uint16,
            count=scalar_coordinates.shape[0],
        )

    result = benchmark(run)
    np.testing.assert_array_equal(result, expected)


def test_scalar_number_to_name(benchmark, scalar_coordinates: np.ndarray) -> None:
    """Measure scalar region-number-to-name conversion on 10,000 values."""

    numbers = feregion.lookup_numbers(scalar_coordinates)
    expected = feregion.numbers_to_names(numbers)

    def run() -> np.ndarray:
        return np.asarray(
            [feregion.number_to_name(int(number)) for number in numbers],
            dtype=expected.dtype,
        )

    result = benchmark(run)
    np.testing.assert_array_equal(result, expected)


def test_vectorized_number_lookup(benchmark, coordinates: np.ndarray) -> None:
    """Measure vectorized region-number lookup at representative batch sizes."""

    expected = feregion.lookup_numbers(coordinates)
    result = benchmark(feregion.lookup_numbers, coordinates)
    np.testing.assert_array_equal(result, expected)


def test_vectorized_name_conversion(benchmark, coordinates: np.ndarray) -> None:
    """Measure vectorized number-to-name conversion at the same batch sizes."""

    numbers = feregion.lookup_numbers(coordinates)
    expected = feregion.numbers_to_names(numbers)
    result = benchmark(feregion.numbers_to_names, numbers)
    np.testing.assert_array_equal(result, expected)


@pytest.mark.parametrize("include_names", [False, True], ids=["numbers", "numbers-and-names"])
def test_pandas_lookup_copy(benchmark, scalar_coordinates: np.ndarray, include_names: bool) -> None:
    """Measure copy-return pandas lookup with and without name materialization."""

    pd = pytest.importorskip("pandas", reason="pandas is an optional benchmark dependency")
    from feregion.pandas import lookup_dataframe

    frame = pd.DataFrame(
        {"longitude": scalar_coordinates[:, 0], "latitude": scalar_coordinates[:, 1]}
    )
    expected = feregion.lookup_numbers(scalar_coordinates)
    result = benchmark(lookup_dataframe, frame, include_names=include_names, inplace=False)
    np.testing.assert_array_equal(result["fe_number"].to_numpy(), expected)


def test_obspy_scalar_loop_baseline(benchmark, scalar_coordinates: np.ndarray) -> None:
    """Measure ObsPy scalar FE lookup on the common 10,000-point workload."""

    pytest.importorskip("obspy", reason="ObsPy is a development-only benchmark baseline")
    from obspy.geodetics import FlinnEngdahl

    reference = FlinnEngdahl()
    expected = feregion.lookup_numbers(scalar_coordinates)

    def run() -> np.ndarray:
        return np.fromiter(
            (reference.get_number(lon, lat) for lon, lat in scalar_coordinates),
            dtype=np.uint16,
            count=scalar_coordinates.shape[0],
        )

    result = benchmark(run)
    np.testing.assert_array_equal(result, expected)


@pytest.fixture(
    scope="module",
    params=[100, 1_000, 10_000, 100_000],
    ids=lambda n: f"n={n}",
)
def comparison_coordinates(request) -> np.ndarray:
    """Return deterministic workloads shared by batch candidate/reference benchmarks."""

    rng = np.random.default_rng(20260838 + request.param)
    return np.column_stack(
        (rng.uniform(-180, 180, request.param), rng.uniform(-90, 90, request.param))
    )


def test_batch_retained_source_baseline(benchmark, comparison_coordinates: np.ndarray) -> None:
    """Measure source-table scanning on batch-comparison coordinates."""

    from tests.reference import SourceReference

    try:
        verify_source_dir(DEFAULT_SOURCE_DIR)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    reference = SourceReference(DEFAULT_SOURCE_DIR)
    expected = feregion.lookup_numbers(comparison_coordinates)

    def run() -> np.ndarray:
        return np.fromiter(
            (reference.number(lon, lat) for lon, lat in comparison_coordinates),
            dtype=np.uint16,
            count=comparison_coordinates.shape[0],
        )

    result = benchmark(run)
    np.testing.assert_array_equal(result, expected)


def test_batch_candidate_comparison(benchmark, comparison_coordinates: np.ndarray) -> None:
    """Measure batch candidate lookup on the exact baseline-comparison coordinates."""

    expected = feregion.lookup_numbers(comparison_coordinates)
    result = benchmark(feregion.lookup_numbers, comparison_coordinates)
    np.testing.assert_array_equal(result, expected)


def test_vectorized_seismic_number_lookup(benchmark, coordinates: np.ndarray) -> None:
    """Measure vectorized coordinate-to-seismic lookup at representative batch sizes."""

    geographic = feregion.lookup_geographic_numbers(coordinates)
    expected = feregion.geographic_numbers_to_seismic_numbers(geographic)
    result = benchmark(feregion.lookup_seismic_numbers, coordinates)
    np.testing.assert_array_equal(result, expected)


def test_vectorized_geographic_to_seismic_conversion(benchmark, coordinates: np.ndarray) -> None:
    """Measure the compact hierarchy crosswalk independently of coordinate lookup."""

    geographic = feregion.lookup_geographic_numbers(coordinates)
    expected = feregion.lookup_seismic_numbers(coordinates)
    result = benchmark(feregion.geographic_numbers_to_seismic_numbers, geographic)
    np.testing.assert_array_equal(result, expected)


def test_vectorized_seismic_name_conversion(benchmark, coordinates: np.ndarray) -> None:
    """Measure vectorized seismic-number-to-name conversion."""

    numbers = feregion.lookup_seismic_numbers(coordinates)
    expected = feregion.seismic_numbers_to_names(numbers)
    result = benchmark(feregion.seismic_numbers_to_names, numbers)
    np.testing.assert_array_equal(result, expected)


def test_internal_split_geographic_lookup(benchmark, coordinates: np.ndarray) -> None:
    """Measure the package-internal split-vector geographical path."""

    engine = feregion.get_default_lookup()
    longitude = coordinates[:, 0].copy()
    latitude = coordinates[:, 1].copy()
    expected = engine.lookup_geographic_numbers(coordinates)
    result = benchmark(
        engine._lookup_geographic_numbers_from_vectors,
        longitude,
        latitude,
    )
    np.testing.assert_array_equal(result, expected)


def test_internal_split_seismic_lookup(benchmark, coordinates: np.ndarray) -> None:
    """Measure split-vector lookup plus trusted seismic hierarchy composition."""

    engine = feregion.get_default_lookup()
    longitude = coordinates[:, 0].copy()
    latitude = coordinates[:, 1].copy()
    geographic = engine.lookup_geographic_numbers(coordinates)
    expected = engine.geographic_numbers_to_seismic_numbers(geographic)
    result = benchmark(
        engine._lookup_seismic_numbers_from_vectors,
        longitude,
        latitude,
    )
    np.testing.assert_array_equal(result, expected)


@pytest.mark.parametrize("level", ["geographic", "seismic"])
def test_pandas_lookup_inplace_by_level(
    benchmark,
    scalar_coordinates: np.ndarray,
    level: str,
) -> None:
    """Measure adapter lookup without including DataFrame preparation time."""

    pd = pytest.importorskip("pandas", reason="pandas is an optional benchmark dependency")
    from feregion.pandas import lookup_dataframe

    template = pd.DataFrame(
        {"longitude": scalar_coordinates[:, 0], "latitude": scalar_coordinates[:, 1]}
    )
    engine = feregion.get_default_lookup()
    expected = (
        engine.lookup_geographic_numbers(scalar_coordinates)
        if level == "geographic"
        else engine.lookup_seismic_numbers(scalar_coordinates)
    )
    number_column = "fe_number" if level == "geographic" else "fe_seismic_number"

    def run() -> np.ndarray:
        frame = template.copy()
        result = lookup_dataframe(frame, level=level, inplace=True, lookup=engine)
        return result[number_column].to_numpy()

    observed = benchmark(run)
    np.testing.assert_array_equal(observed, expected)
