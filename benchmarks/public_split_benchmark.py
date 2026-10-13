"""Reproduce the direct public matrix-versus-split benchmark for the 0.6 API.

This harness is intentionally independent from the source-table scanner and ASV
campaign machinery. It exists to retain the exact executable procedure for the
large-batch public-interface comparison required by ``REQ-PERF-033``. The
benchmark measures already-constructed matrix input separately from caller-side
``column_stack`` cost and alternates operation order between repetitions.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

import feregion

SEED = 20260813
DEFAULT_SIZES = (100_000, 1_000_000, 5_000_000)
DEFAULT_REPETITIONS = 9
_OPERATION_ORDER = (
    "matrix_geographic",
    "split_geographic_public",
    "stack_plus_geographic",
    "matrix_seismic",
    "split_seismic_public",
)


def _coordinates(size: int) -> tuple[np.ndarray, np.ndarray]:
    """Return deterministic separate longitude/latitude vectors for ``size`` points."""

    rng = np.random.default_rng(SEED + 21 + size)
    longitude = rng.uniform(-180.0, 180.0, size)
    latitude = rng.uniform(-90.0, 90.0, size)
    return longitude, latitude


def _time_once(callable_: Callable[[], object]) -> float:
    """Return one wall-clock duration in seconds."""

    started = time.perf_counter()
    callable_()
    return time.perf_counter() - started


def _run_size(size: int, repetitions: int) -> dict[str, Any]:
    """Measure all public matrix/split operations for one deterministic load."""

    engine = feregion.get_default_lookup()
    longitude, latitude = _coordinates(size)
    matrix = np.column_stack((longitude, latitude))

    expected_geographic = engine.lookup_geographic_numbers(matrix)
    expected_seismic = engine.lookup_seismic_numbers(matrix)

    def matrix_geographic() -> np.ndarray:
        return engine.lookup_geographic_numbers(matrix)

    def split_geographic_public() -> np.ndarray:
        return engine.lookup_geographic_numbers_from_vectors(longitude, latitude)

    def stack_plus_geographic() -> np.ndarray:
        return engine.lookup_geographic_numbers(np.column_stack((longitude, latitude)))

    def matrix_seismic() -> np.ndarray:
        return engine.lookup_seismic_numbers(matrix)

    def split_seismic_public() -> np.ndarray:
        return engine.lookup_seismic_numbers_from_vectors(longitude, latitude)

    operations: dict[str, Callable[[], np.ndarray]] = {
        "matrix_geographic": matrix_geographic,
        "split_geographic_public": split_geographic_public,
        "stack_plus_geographic": stack_plus_geographic,
        "matrix_seismic": matrix_seismic,
        "split_seismic_public": split_seismic_public,
    }

    for name in ("matrix_geographic", "split_geographic_public", "stack_plus_geographic"):
        np.testing.assert_array_equal(operations[name](), expected_geographic)
    for name in ("matrix_seismic", "split_seismic_public"):
        np.testing.assert_array_equal(operations[name](), expected_seismic)

    # Warm every operation once before recorded timing. Matrix construction remains
    # outside the matrix operation; stack construction intentionally remains inside
    # the stack-plus-geographic operation.
    for name in _OPERATION_ORDER:
        operations[name]()

    samples: dict[str, list[float]] = {name: [] for name in _OPERATION_ORDER}
    for repetition in range(repetitions):
        order = _OPERATION_ORDER if repetition % 2 == 0 else tuple(reversed(_OPERATION_ORDER))
        for name in order:
            samples[name].append(_time_once(operations[name]))

    medians = {name: statistics.median(values) for name, values in samples.items()}
    return {
        "points": size,
        "median_seconds": medians,
        "ratios": {
            "geographic_matrix_over_split": (
                medians["matrix_geographic"] / medians["split_geographic_public"]
            ),
            "geographic_stack_over_split": (
                medians["stack_plus_geographic"] / medians["split_geographic_public"]
            ),
            "seismic_matrix_over_split": (
                medians["matrix_seismic"] / medians["split_seismic_public"]
            ),
        },
        "samples_seconds": samples,
    }


def run_benchmark(
    *, sizes: Sequence[int] = DEFAULT_SIZES, repetitions: int = DEFAULT_REPETITIONS
) -> dict[str, Any]:
    """Return reproducible direct public split benchmark evidence.

    Args:
        sizes: Positive coordinate counts to measure, in the requested order.
        repetitions: Recorded timing repetitions for each operation and size.

    Returns:
        JSON-serializable benchmark evidence including protocol and raw samples.

    Raises:
        ValueError: If a size is non-positive or fewer than three repetitions are requested.
    """

    normalized_sizes = tuple(int(size) for size in sizes)
    if not normalized_sizes or any(size <= 0 for size in normalized_sizes):
        raise ValueError("sizes must contain positive integers")
    if repetitions < 3:
        raise ValueError("repetitions must be at least 3")

    rows = [_run_size(size, repetitions) for size in normalized_sizes]
    return {
        "schema": "feregion-public-split-direct-v2",
        "environment": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "feregion": feregion.__version__,
        },
        "protocol": {
            "seed": SEED,
            "seed_formula": "seed + 21 + points",
            "coordinate_distribution": "uniform longitude [-180, 180], latitude [-90, 90]",
            "sizes": list(normalized_sizes),
            "repetitions": repetitions,
            "warmup_calls_per_operation": 1,
            "operation_order": list(_OPERATION_ORDER),
            "alternation": "forward on even repetitions; reverse on odd repetitions",
            "matrix_construction": "outside matrix timings",
            "caller_column_stack": "inside stack_plus_geographic timing only",
            "clock": "time.perf_counter",
            "correctness": (
                "all geographic paths equal public matrix geographic result and all seismic "
                "paths equal public matrix seismic result before recorded timing"
            ),
        },
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the retained 0.6 public split benchmark and emit JSON evidence."""

    parser = argparse.ArgumentParser(
        description="Benchmark public matrix and split-vector lookup on deterministic loads."
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=list(DEFAULT_SIZES),
        help="positive point counts (default: 100000 1000000 5000000)",
    )
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = run_benchmark(sizes=args.sizes, repetitions=args.repetitions)
    except ValueError as exc:
        parser.error(str(exc))

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
