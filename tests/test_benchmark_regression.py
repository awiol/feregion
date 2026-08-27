"""Release-to-release performance-regression decision contracts."""

from __future__ import annotations

import copy

import pytest

from benchmarks.compare_releases import ReleaseBenchmarkError, compare_reports


def _report(version: str, rates: tuple[float, float, float]) -> dict[str, object]:
    """Return the smallest benchmark report that supports the release gate."""

    return {
        "schema_version": 6,
        "environment": {
            "platform": "test-platform",
            "python": "3.13.5",
            "python_implementation": "CPython",
            "python_compiler": "test-compiler",
            "machine": "x86_64",
            "cpu_model": "test cpu",
            "logical_cpu_count": 8,
            "numpy": "2.3.5",
            "feregion": version,
        },
        "workload": {
            "seed": 20260813,
            "coordinate_distribution": "uniform global valid longitude/latitude",
            "timing": "steady-state wall clock after one warmup",
        },
        "batch": [
            {"points": points, "median_operations_per_second": rate}
            for points, rate in zip((10_000, 100_000, 1_000_000), rates, strict=True)
        ],
    }


def test_release_gate_triggers_for_two_adjacent_slowdowns_above_threshold() -> None:
    """Two adjacent >25% slowdowns cross the documented review trigger."""

    comparison = compare_reports(
        _report("0.2.0a1", (100.0, 100.0, 100.0)),
        _report("0.2.0a2", (74.0, 70.0, 100.0)),
    )
    assert comparison["review_triggered"] is True
    assert comparison["triggering_adjacent_size_pairs"] == [[10_000, 100_000]]


def test_release_gate_does_not_trigger_for_one_isolated_slow_size() -> None:
    """One slow workload remains a review signal but does not satisfy the gate rule."""

    comparison = compare_reports(
        _report("0.2.0a1", (100.0, 100.0, 100.0)),
        _report("0.2.0a2", (74.0, 100.0, 74.0)),
    )
    assert comparison["review_triggered"] is False


def test_release_gate_rejects_environment_drift() -> None:
    """A version comparison cannot silently attribute hardware drift to package code."""

    baseline = _report("0.2.0a1", (100.0, 100.0, 100.0))
    candidate = copy.deepcopy(_report("0.2.0a2", (100.0, 100.0, 100.0)))
    candidate["environment"]["cpu_model"] = "different cpu"
    with pytest.raises(ReleaseBenchmarkError, match="cpu_model"):
        compare_reports(baseline, candidate)
