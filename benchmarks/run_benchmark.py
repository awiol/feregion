"""Run reproducible in-process feregion lookup benchmarks.

This standalone harness requires only feregion's base dependency for scalar,
NumPy, and name-conversion measurements. Install ``feregion[benchmark]`` to add
pandas and the optional ObsPy comparison baseline.

CLI and GeoJSON operations are intentionally excluded. Their dominant costs are
process/I/O and geometry operations rather than the in-process FE lookup paths
measured here.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np

import feregion
from tests.reference import SourceReference
from tools.obspy_fe_source import DEFAULT_SOURCE_DIR, verify_source_dir

SOURCE = DEFAULT_SOURCE_DIR
SEED = 20260813


def timed(callable_: Callable[[], object], repeats: int) -> list[float]:
    """Return wall-clock durations after one unrecorded warmup call."""

    callable_()
    durations: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        callable_()
        durations.append(time.perf_counter() - start)
    return durations


def summarize(
    durations: list[float],
    operations: int,
) -> dict[str, float | int]:
    """Summarize repeated durations and retain enough spread for review."""

    median = statistics.median(durations)
    return {
        "operations": operations,
        "repeats": len(durations),
        "median_seconds": median,
        "min_seconds": min(durations),
        "max_seconds": max(durations),
        "median_operations_per_second": operations / median,
    }


def coordinates(size: int, *, seed_offset: int = 0) -> np.ndarray:
    """Return deterministic uniformly distributed valid global coordinates."""

    rng = np.random.default_rng(SEED + seed_offset + size)
    return np.column_stack((rng.uniform(-180.0, 180.0, size), rng.uniform(-90.0, 90.0, size)))


def benchmark_scalar(
    reference: SourceReference,
    repeats: int,
    size: int = 10_000,
) -> dict[str, Any]:
    """Benchmark scalar number/Region interfaces and source-reference lookup."""

    points = coordinates(size, seed_offset=10)
    expected = np.fromiter(
        (reference.number(lon, lat) for lon, lat in points),
        dtype=np.uint16,
        count=size,
    )

    def number_loop() -> np.ndarray:
        return np.fromiter(
            (feregion.lookup_number(lon, lat) for lon, lat in points),
            dtype=np.uint16,
            count=size,
        )

    def region_loop() -> np.ndarray:
        return np.fromiter(
            (feregion.lookup_region(lon, lat).number for lon, lat in points),
            dtype=np.uint16,
            count=size,
        )

    expected_names = feregion.numbers_to_names(expected)

    def name_loop() -> np.ndarray:
        return np.asarray(
            [feregion.number_to_name(int(number)) for number in expected],
            dtype=expected_names.dtype,
        )

    def source_loop() -> np.ndarray:
        return np.fromiter(
            (reference.number(lon, lat) for lon, lat in points),
            dtype=np.uint16,
            count=size,
        )

    np.testing.assert_array_equal(number_loop(), expected)
    np.testing.assert_array_equal(region_loop(), expected)
    np.testing.assert_array_equal(name_loop(), expected_names)

    result: dict[str, Any] = {
        "lookup_number": summarize(timed(number_loop, repeats), size),
        "lookup_region": summarize(timed(region_loop, repeats), size),
        "number_to_name": summarize(timed(name_loop, repeats), size),
        "source_reference": summarize(timed(source_loop, repeats), size),
    }

    try:
        from obspy.geodetics import FlinnEngdahl
    except ImportError:
        result["obspy"] = None
    else:
        obspy_lookup = FlinnEngdahl()

        def obspy_loop() -> np.ndarray:
            return np.fromiter(
                (obspy_lookup.get_number(lon, lat) for lon, lat in points),
                dtype=np.uint16,
                count=size,
            )

        np.testing.assert_array_equal(obspy_loop(), expected)
        result["obspy"] = summarize(timed(obspy_loop, repeats), size)

    return result


def benchmark_batch(repeats: int) -> list[dict[str, float | int]]:
    """Benchmark batch number lookup at representative batch sizes."""

    rows: list[dict[str, float | int]] = []
    for size in (1, 100, 1_000, 10_000, 100_000, 1_000_000):
        points = coordinates(size, seed_offset=20)
        expected = feregion.lookup_numbers(points)

        run = partial(feregion.lookup_numbers, points)

        np.testing.assert_array_equal(run(), expected)
        summary = summarize(timed(run, repeats), size)
        summary["points"] = size
        rows.append(summary)
    return rows


def _reference_batch(reference: SourceReference, points: np.ndarray) -> np.ndarray:
    """Return region numbers from the direct source-table scanner."""

    return np.fromiter(
        (reference.number(lon, lat) for lon, lat in points),
        dtype=np.uint16,
        count=points.shape[0],
    )


def benchmark_batch_comparison(
    reference: SourceReference,
    repeats: int,
) -> list[dict[str, Any]]:
    """Compare batch candidate lookup with the source-table scanner baseline."""

    rows: list[dict[str, Any]] = []
    for size in (100, 1_000, 10_000, 100_000):
        points = coordinates(size, seed_offset=25)

        source_run = partial(_reference_batch, reference, points)
        expected = source_run()
        candidate_run = partial(feregion.lookup_numbers, points)

        np.testing.assert_array_equal(candidate_run(), expected)
        candidate = summarize(timed(candidate_run, repeats), size)
        baseline = summarize(timed(source_run, repeats), size)
        rows.append(
            {
                "points": size,
                "candidate": candidate,
                "baseline": baseline,
                "baseline_name": "source-table-scanner",
                "candidate_speedup": (baseline["median_seconds"] / candidate["median_seconds"]),
            }
        )
    return rows


def benchmark_names(repeats: int) -> list[dict[str, float | int]]:
    """Benchmark batch conversion from region numbers to names."""

    rows: list[dict[str, float | int]] = []
    for size in (1, 100, 10_000, 100_000, 1_000_000):
        numbers = feregion.lookup_numbers(coordinates(size, seed_offset=30))
        expected = feregion.numbers_to_names(numbers)

        run = partial(feregion.numbers_to_names, numbers)

        np.testing.assert_array_equal(run(), expected)
        summary = summarize(timed(run, repeats), size)
        summary["points"] = size
        rows.append(summary)
    return rows


def benchmark_pandas(repeats: int, size: int = 100_000) -> dict[str, Any] | None:
    """Benchmark pandas copy/in-place lookup with and without region names."""

    try:
        import pandas as pd
    except ImportError:
        return None

    from feregion.pandas import lookup_dataframe

    points = coordinates(size, seed_offset=40)
    base = pd.DataFrame({"longitude": points[:, 0], "latitude": points[:, 1]})
    expected = feregion.lookup_numbers(points)

    def copy_numbers() -> Any:
        return lookup_dataframe(base, include_names=False, inplace=False)

    def copy_names() -> Any:
        return lookup_dataframe(base, include_names=True, inplace=False)

    def timed_inplace(include_names: bool) -> list[float]:
        # Each in-place call owns a fresh frame. Preparation occurs outside the
        # timed interval so the measurement remains the adapter operation, not
        # DataFrame construction. Reusing an annotated frame would correctly
        # violate the additive-output schema.
        warmup_frame = base.copy()
        warmup = lookup_dataframe(warmup_frame, include_names=include_names, inplace=True)
        np.testing.assert_array_equal(warmup["fe_number"].to_numpy(), expected)

        durations: list[float] = []
        for _ in range(repeats):
            frame = base.copy()
            start = time.perf_counter()
            observed = lookup_dataframe(frame, include_names=include_names, inplace=True)
            durations.append(time.perf_counter() - start)
            np.testing.assert_array_equal(observed["fe_number"].to_numpy(), expected)
        return durations

    for run in (copy_numbers, copy_names):
        observed = run()
        np.testing.assert_array_equal(observed["fe_number"].to_numpy(), expected)

    return {
        "pandas_version": pd.__version__,
        "rows": size,
        "copy_numbers": summarize(timed(copy_numbers, repeats), size),
        "copy_with_names": summarize(timed(copy_names, repeats), size),
        "inplace_numbers": summarize(timed_inplace(False), size),
        "inplace_with_names": summarize(timed_inplace(True), size),
        "inplace_preparation": "fresh DataFrame prepared outside each timed interval",
    }


def main(argv: list[str] | None = None) -> int:
    """Run all routine in-process benchmarks and optionally write JSON."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")

    # Warm the package-level cached assets before steady-state measurements.
    feregion.lookup_number(0.0, 0.0)
    verify_source_dir(SOURCE)
    reference = SourceReference(SOURCE)

    report: dict[str, Any] = {
        "schema_version": 4,
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "python_compiler": platform.python_compiler(),
            "numpy": np.__version__,
            "feregion": feregion.__version__,
        },
        "workload": {
            "seed": SEED,
            "coordinate_distribution": "uniform global valid longitude/latitude",
            "timing": "steady-state wall clock after one warmup",
            "cli_included": False,
            "geojson_included": False,
        },
        "scalar": benchmark_scalar(reference, args.repeats),
        "batch": benchmark_batch(args.repeats),
        "batch_comparison": benchmark_batch_comparison(reference, args.repeats),
        "names": benchmark_names(args.repeats),
        "pandas": benchmark_pandas(args.repeats),
        "notes": [
            "All timed candidate paths are correctness-checked before reporting.",
            "The source-table scanner performs an independent direct breakpoint scan.",
            (
                "Batch comparison uses identical coordinates for candidate and "
                "source-table-scanner baseline."
            ),
            "ObsPy is measured only when installed; it is never a runtime dependency.",
            "Results are environment-specific microbenchmarks, not a performance SLA.",
        ],
    }

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
