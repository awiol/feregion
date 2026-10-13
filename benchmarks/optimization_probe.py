from __future__ import annotations

import argparse
import gc
import json
import os
import platform

try:
    import resource as _resource
except ImportError:  # pragma: no cover - platform boundary
    _resource = None
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

# Import target package from PYTHONPATH.
import feregion
from feregion._default import get_default_lookup
from feregion.core import _integer_region_array

try:
    import pandas as pd

    from feregion.pandas import _coordinate_values
except ImportError:
    pd = None
    _coordinate_values = None

SEED = 20260917


def coordinates(size: int) -> np.ndarray:
    rng = np.random.default_rng(SEED + size)
    lon = rng.uniform(-180.0, 180.0, size=size)
    lat = rng.uniform(-90.0, 90.0, size=size)
    return np.column_stack((lon, lat))


def rss_bytes() -> int | None:
    if _resource is None:
        return None
    value = _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB, macOS reports bytes.
    if sys.platform.startswith("linux"):
        return int(value) * 1024
    return int(value)


def median_ns(fn: Callable[[], Any], *, repeats: int, warmups: int = 1) -> tuple[float, list[int]]:
    for _ in range(warmups):
        fn()
    gc.collect()
    samples: list[int] = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        result = fn()
        elapsed = time.perf_counter_ns() - start
        samples.append(elapsed)
        # Keep the result alive through timing completion.
        if result is None:
            pass
    return float(statistics.median(samples)), samples


def _result_bytes(value: Any) -> int | None:
    if isinstance(value, np.ndarray):
        return int(value.nbytes)
    if pd is not None and isinstance(value, pd.DataFrame):
        return int(value.memory_usage(index=True, deep=True).sum())
    if isinstance(value, tuple):
        parts = [_result_bytes(item) for item in value]
        if all(item is not None for item in parts):
            return sum(int(item) for item in parts if item is not None)
    return None


def record(case: str, size: int, fn: Callable[[], Any], repeats: int) -> dict[str, Any]:
    representative = fn()
    result_bytes = _result_bytes(representative)
    before = rss_bytes()
    med, samples = median_ns(fn, repeats=repeats)
    after = rss_bytes()
    rss_delta = None if before is None or after is None else max(0, after - before)
    return {
        "case": case,
        "size": size,
        "median_ns": med,
        "samples_ns": samples,
        "ns_per_element": med / size,
        "operations_per_second": size / (med / 1e9),
        "result_bytes": result_bytes,
        "peak_rss_before_bytes": before,
        "peak_rss_after_bytes": after,
        "peak_rss_delta_bytes": rss_delta,
    }


def run_size(size: int, repeats: int, *, include_pandas: bool) -> list[dict[str, Any]]:
    engine = get_default_lookup()
    coords = coordinates(size)
    longitude = coords[:, 0].copy()
    latitude = coords[:, 1].copy()
    geographic = engine.lookup_geographic_numbers(coords)
    public_seismic = engine.geographic_numbers_to_seismic_numbers(geographic)
    public_geo_names = engine.geographic_numbers_to_names(geographic)
    seismic = engine.lookup_seismic_numbers(coords)
    public_seismic_names = engine.seismic_numbers_to_names(seismic)

    crosswalk = engine.seismic_by_geographic
    seismic_names = engine.seismic_names
    if crosswalk is None or seismic_names is None:
        raise RuntimeError("default engine lacks seismic hierarchy")

    expected_seismic = crosswalk[geographic]
    np.testing.assert_array_equal(public_seismic, expected_seismic)
    np.testing.assert_array_equal(public_geo_names, engine.names[geographic])
    np.testing.assert_array_equal(public_seismic_names, seismic_names[seismic])

    cases: list[tuple[str, Callable[[], Any]]] = [
        ("geographic_lookup_matrix", lambda: engine.lookup_geographic_numbers(coords)),
        (
            "geographic_stack_plus_lookup",
            lambda: engine.lookup_geographic_numbers(np.column_stack((longitude, latitude))),
        ),
        (
            "geographic_split_lookup",
            lambda: engine._lookup_geographic_numbers_from_vectors(longitude, latitude),
        ),
        ("seismic_lookup_matrix", lambda: engine.lookup_seismic_numbers(coords)),
        (
            "seismic_split_lookup",
            lambda: engine._lookup_seismic_numbers_from_vectors(longitude, latitude),
        ),
        (
            "geo_to_seismic_public",
            lambda: engine.geographic_numbers_to_seismic_numbers(geographic),
        ),
        (
            "geo_validation_complete",
            lambda: _integer_region_array(
                geographic, engine.names, "geographical", active=engine._active_geographic
            ),
        ),
        (
            "geo_validation_bounds",
            lambda: (np.any(geographic < 1), np.any(geographic >= engine.names.size)),
        ),
        (
            "geo_validation_name_slot",
            lambda: np.any(engine.names[geographic] == ""),
        ),
        (
            "geo_validation_active_mask",
            lambda: np.any(~engine._active_geographic[geographic]),
        ),
        ("geo_to_seismic_gather", lambda: crosswalk[geographic]),
        ("geo_names_public", lambda: engine.geographic_numbers_to_names(geographic)),
        (
            "geo_names_gather",
            lambda: np.asarray(engine.names[geographic], dtype=engine.names.dtype),
        ),
        ("seismic_names_public", lambda: engine.seismic_numbers_to_names(seismic)),
        (
            "seismic_validation_complete",
            lambda: _integer_region_array(seismic, seismic_names, "seismic"),
        ),
        (
            "seismic_validation_bounds",
            lambda: (np.any(seismic < 1), np.any(seismic >= seismic_names.size)),
        ),
        ("seismic_validation_name_slot", lambda: np.any(seismic_names[seismic] == "")),
        (
            "seismic_validation_valid_mask",
            lambda: (
                np.any(~engine._valid_seismic[seismic])
                if engine._valid_seismic is not None
                else False
            ),
        ),
        (
            "seismic_names_gather",
            lambda: np.asarray(seismic_names[seismic], dtype=seismic_names.dtype),
        ),
    ]

    records = [record(name, size, fn, repeats) for name, fn in cases]

    if include_pandas and pd is not None and _coordinate_values is not None and size <= 1_000_000:
        frame = pd.DataFrame({"longitude": coords[:, 0], "latitude": coords[:, 1]})
        longitude = _coordinate_values(frame["longitude"])
        latitude = _coordinate_values(frame["latitude"])
        split_numbers = engine._lookup_geographic_numbers_from_vectors(longitude, latitude)
        names = engine.geographic_numbers_to_names(split_numbers)
        object_names = np.asarray(engine.names, dtype=object)[split_numbers]
        np.testing.assert_array_equal(split_numbers, geographic)
        np.testing.assert_array_equal(names, public_geo_names)
        np.testing.assert_array_equal(object_names, public_geo_names)

        records.extend(
            [
                record("pandas_frame_copy", size, lambda: frame.copy(), repeats),
                record(
                    "pandas_coordinate_extract",
                    size,
                    lambda: (
                        _coordinate_values(frame["longitude"]),
                        _coordinate_values(frame["latitude"]),
                    ),
                    repeats,
                ),
                record(
                    "pandas_split_geographic_core",
                    size,
                    lambda: engine._lookup_geographic_numbers_from_vectors(longitude, latitude),
                    repeats,
                ),
                record(
                    "pandas_name_materialization",
                    size,
                    lambda: engine.geographic_numbers_to_names(split_numbers),
                    repeats,
                ),
                record(
                    "pandas_object_name_gather",
                    size,
                    lambda: np.asarray(engine.names, dtype=object)[split_numbers],
                    repeats,
                ),
            ]
        )

        def assign_numbers() -> object:
            target = frame.copy()
            target["fe_number"] = split_numbers
            return target

        def assign_names() -> object:
            target = frame.copy()
            target["fe_region"] = names
            return target

        def assign_object_names() -> object:
            target = frame.copy()
            target["fe_region"] = object_names
            return target

        def assign_both() -> object:
            target = frame.copy()
            target["fe_number"] = split_numbers
            target["fe_region"] = names
            return target

        records.extend(
            [
                record("pandas_copy_plus_assign_numbers", size, assign_numbers, repeats),
                record("pandas_copy_plus_assign_names", size, assign_names, repeats),
                record(
                    "pandas_copy_plus_assign_object_names",
                    size,
                    assign_object_names,
                    repeats,
                ),
                record("pandas_copy_plus_assign_both", size, assign_both, repeats),
            ]
        )

    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[100_000, 1_000_000])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    for size in args.sizes:
        records.extend(run_size(size, args.repeats, include_pandas=True))

    payload = {
        "schema_version": 1,
        "purpose": "feregion 0.5 optimization mechanism investigation",
        "package_version": feregion.__version__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "numpy": np.__version__,
        "pandas": None if pd is None else pd.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "workload_seed": SEED,
        "sizes": args.sizes,
        "repeats": args.repeats,
        "records": records,
        "limitations": [
            "single-host mechanism-diagnostic evidence; not a release-performance gate",
            "ru_maxrss deltas are process-high-water observations, not exact allocation accounting",
            "pandas stage timings intentionally include DataFrame.copy in assignment cases",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
