"""Compare selected feregion benchmark metrics across Python versions.

The standalone benchmark harness writes one JSON report per interpreter. This
module reduces those detailed reports to a compact cross-version table covering
only the most decision-relevant public lookup paths. It also records dependency
versions so differences caused by environment markers remain visible rather
than being attributed silently to the interpreter.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Metric:
    """Describe one benchmark value selected for cross-version comparison."""

    label: str
    workload: str
    section: str
    key: str
    points: int | None = None


METRICS = (
    Metric("Scalar number lookup", "10k points", "scalar", "lookup_number"),
    Metric("Scalar Region lookup", "10k points", "scalar", "lookup_region"),
    Metric("Scalar number→name", "10k values", "scalar", "number_to_name"),
    Metric("Batch number lookup", "10k points", "batch", "", 10_000),
    Metric("Batch number lookup", "1m points", "batch", "", 1_000_000),
    Metric("Batch numbers→names", "1m values", "names", "", 1_000_000),
    Metric("pandas copy numbers", "100k rows", "pandas", "copy_numbers"),
    Metric("pandas copy with names", "100k rows", "pandas", "copy_with_names"),
)


class BenchmarkComparisonError(RuntimeError):
    """Raised when benchmark inputs cannot form a trustworthy comparison."""


def _python_key(version: str) -> tuple[int, ...]:
    """Return a numeric sort key for a dotted Python version string."""

    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError as exc:
        raise BenchmarkComparisonError(f"invalid Python version in benchmark: {version}") from exc


def load_reports(input_dir: Path) -> dict[str, dict[str, Any]]:
    """Load benchmark JSON files from ``input_dir`` keyed by Python major/minor.

    Args:
        input_dir: Directory containing ``python-*.json`` standalone reports.

    Returns:
        Mapping from Python ``major.minor`` to parsed report.

    Raises:
        BenchmarkComparisonError: If no reports are found or duplicate Python
            major/minor environments are present.
    """

    reports: dict[str, dict[str, Any]] = {}
    for path in sorted(input_dir.glob("python-*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        full_version = str(report["environment"]["python"])
        parts = full_version.split(".")
        if len(parts) < 2:
            raise BenchmarkComparisonError(f"invalid Python version in {path}: {full_version}")
        version = ".".join(parts[:2])
        if version in reports:
            raise BenchmarkComparisonError(f"duplicate benchmark for Python {version}")
        reports[version] = report
    if not reports:
        raise BenchmarkComparisonError(f"no python-*.json benchmark reports in {input_dir}")
    return reports


def _rows_by_points(report: dict[str, Any], section: str) -> dict[int, dict[str, Any]]:
    """Index one point-parametrized benchmark section by workload size."""

    return {int(row["points"]): row for row in report[section]}


def metric_throughput(report: dict[str, Any], metric: Metric) -> float:
    """Return operations/second for one selected metric in ``report``."""

    if metric.section in {"batch", "names"}:
        if metric.points is None:
            raise BenchmarkComparisonError(f"metric {metric.label} has no point selector")
        row = _rows_by_points(report, metric.section).get(metric.points)
        if row is None:
            raise BenchmarkComparisonError(
                f"metric {metric.label} missing workload {metric.points}"
            )
        return float(row["median_operations_per_second"])

    section = report.get(metric.section)
    if section is None:
        raise BenchmarkComparisonError(f"missing benchmark section: {metric.section}")
    if metric.section == "pandas" and section is None:
        raise BenchmarkComparisonError("pandas benchmark is unavailable")
    return float(section[metric.key]["median_operations_per_second"])


def _environment_row(version: str, report: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Return compact environment metadata for one interpreter result."""

    environment = report["environment"]
    pandas = report.get("pandas")
    pandas_version = "not installed" if pandas is None else str(pandas["pandas_version"])
    return (
        version,
        str(environment["python"]),
        str(environment["numpy"]),
        pandas_version,
        str(environment["feregion"]),
    )


def render_report(reports: dict[str, dict[str, Any]]) -> str:
    """Render a compact Markdown comparison for loaded Python-version reports."""

    versions = sorted(reports, key=_python_key)
    baseline = "3.11" if "3.11" in reports else versions[0]
    baseline_values = {metric: metric_throughput(reports[baseline], metric) for metric in METRICS}

    platforms = {str(report["environment"]["platform"]) for report in reports.values()}
    lines = [
        "# feregion Python-version benchmark comparison",
        "",
        f"Baseline for relative throughput: Python {baseline}.",
        "",
    ]
    if len(platforms) == 1:
        lines.append(f"Platform: `{next(iter(platforms))}`.")
    else:
        lines.append(
            "**Comparability warning:** input reports were produced on different platforms; "
            "cross-version throughput ratios are not controlled interpreter-only comparisons."
        )
    lines.extend(
        [
            "",
            "## Environment",
            "",
            "| Python target | Interpreter | NumPy | pandas | feregion |",
            "|---|---|---|---|---|",
        ]
    )
    for version in versions:
        target, interpreter, numpy_version, pandas_version, package_version = _environment_row(
            version, reports[version]
        )
        lines.append(
            f"| {target} | {interpreter} | {numpy_version} | {pandas_version} | {package_version} |"
        )

    header = "| Metric | Workload | " + " | ".join(versions) + " | Fastest |"
    separator = "|---|---|" + "---:|" * len(versions) + "---|"
    lines.extend(
        [
            "",
            "## Selected throughput metrics",
            "",
            "Each cell is median million operations/second followed by throughput relative "
            f"to Python {baseline}.",
            "",
            header,
            separator,
        ]
    )

    ratios_by_version: dict[str, list[float]] = {version: [] for version in versions}
    for metric in METRICS:
        values = {version: metric_throughput(reports[version], metric) for version in versions}
        fastest = max(values, key=values.__getitem__)
        cells: list[str] = []
        for version in versions:
            value = values[version]
            ratio = value / baseline_values[metric]
            ratios_by_version[version].append(ratio)
            cells.append(f"{value / 1_000_000:.3f} ({ratio:.2f}x)")
        lines.append(
            f"| {metric.label} | {metric.workload} | " + " | ".join(cells) + f" | {fastest} |"
        )

    lines.extend(
        [
            "",
            "## Aggregate view",
            "",
            "The geometric mean is an equal-weight summary of the eight selected "
            "relative-throughput ratios in log-ratio space. It is a review aid, not a "
            "product workload model or performance SLA.",
            "",
            "| Python | Geometric mean vs baseline |",
            "|---|---:|",
        ]
    )
    for version in versions:
        ratios = ratios_by_version[version]
        geometric_mean = math.exp(sum(math.log(value) for value in ratios) / len(ratios))
        lines.append(f"| {version} | {geometric_mean:.3f}x |")

    lines.extend(
        [
            "",
            "The benchmark matrix should use one repository lock and one machine when the goal "
            "is to compare interpreter versions. Exact NumPy and pandas versions are shown above "
            "because environment markers may still require different compatible artifacts.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Load benchmark JSON files, validate required versions, and emit Markdown."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-python", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        reports = load_reports(args.input_dir)
        missing = sorted(set(args.require_python) - set(reports), key=_python_key)
        if missing:
            raise BenchmarkComparisonError(
                "missing required Python benchmark(s): " + ", ".join(missing)
            )
        text = render_report(reports)
    except (BenchmarkComparisonError, KeyError, TypeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
