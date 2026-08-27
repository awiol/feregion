"""Tests for the compact cross-Python benchmark comparison report.

The tests use synthetic standalone benchmark reports so report selection,
ordering, normalization, and missing-version handling remain deterministic and
do not depend on the performance characteristics of the machine running pytest.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.compare_python_versions import (
    METRICS,
    BenchmarkComparisonError,
    load_reports,
    render_report,
)


def _summary(rate: float) -> dict[str, float | int]:
    """Return the minimum standalone-summary shape needed by the report."""

    return {
        "operations": 10_000,
        "repeats": 7,
        "median_seconds": 10_000 / rate,
        "min_seconds": 10_000 / rate,
        "max_seconds": 10_000 / rate,
        "median_operations_per_second": rate,
    }


def _report(version: str, scale: float) -> dict:
    """Return a synthetic complete report with throughput scaled by ``scale``."""

    base = 1_000_000 * scale
    return {
        "schema_version": 4,
        "environment": {
            "platform": "test-platform",
            "python": version,
            "numpy": "2.0.0",
            "feregion": "0.1.2a6",
        },
        "scalar": {
            "lookup_number": _summary(base * 1),
            "lookup_region": _summary(base * 2),
            "number_to_name": _summary(base * 3),
        },
        "batch": [
            {"points": 10_000, **_summary(base * 4)},
            {"points": 1_000_000, **_summary(base * 5)},
        ],
        "names": [{"points": 1_000_000, **_summary(base * 6)}],
        "pandas": {
            "pandas_version": "2.2.0",
            "copy_numbers": _summary(base * 7),
            "copy_with_names": _summary(base * 8),
        },
    }


def test_report_compares_eight_selected_metrics_and_orders_versions() -> None:
    """The report stays compact and normalizes each version to the 3.11 baseline."""

    text = render_report({"3.14": _report("3.14.1", 2.0), "3.11": _report("3.11.9", 1.0)})

    assert len(METRICS) == 8
    assert text.index("| 3.11 | 3.11.9") < text.index("| 3.14 | 3.14.1")
    assert "2.000 (2.00x)" in text
    assert "| 3.14 | 2.000x |" in text


def test_load_reports_rejects_duplicate_python_minor_versions(tmp_path: Path) -> None:
    """Two reports for one Python major/minor cannot be compared ambiguously."""

    (tmp_path / "python-a.json").write_text(json.dumps(_report("3.11.8", 1.0)))
    (tmp_path / "python-b.json").write_text(json.dumps(_report("3.11.9", 1.1)))

    with pytest.raises(BenchmarkComparisonError, match="duplicate benchmark"):
        load_reports(tmp_path)
