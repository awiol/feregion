"""Compare accepted feregion benchmark records for release regression review."""

from __future__ import annotations

import argparse
import json
from itertools import pairwise
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLD = 0.25
_REQUIRED_ENVIRONMENT_FIELDS = (
    "platform",
    "python",
    "python_implementation",
    "python_compiler",
    "machine",
    "cpu_model",
    "logical_cpu_count",
    "numpy",
)
_REQUIRED_WORKLOAD_FIELDS = ("seed", "coordinate_distribution", "timing")


class ReleaseBenchmarkError(RuntimeError):
    """Raised when two reports cannot support a controlled release comparison."""


def load_report(path: Path) -> dict[str, Any]:
    """Load one standalone benchmark report from JSON."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseBenchmarkError(f"cannot read benchmark report {path}: {exc}") from exc


def _matching_context(baseline: dict[str, Any], candidate: dict[str, Any]) -> None:
    """Require environment and workload fields that make release ratios interpretable."""

    for field in _REQUIRED_ENVIRONMENT_FIELDS:
        left = baseline["environment"].get(field)
        right = candidate["environment"].get(field)
        if left != right:
            raise ReleaseBenchmarkError(
                f"benchmark environment differs for {field}: baseline={left!r}, candidate={right!r}"
            )
    for field in _REQUIRED_WORKLOAD_FIELDS:
        left = baseline["workload"].get(field)
        right = candidate["workload"].get(field)
        if left != right:
            raise ReleaseBenchmarkError(
                f"benchmark workload differs for {field}: baseline={left!r}, candidate={right!r}"
            )


def _batch_rows(report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Index geographical batch benchmark rows by point count."""

    return {int(row["points"]): row for row in report["batch"]}


def compare_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """Return the release-to-release batch regression decision record.

    The review trigger is crossed only when throughput slows by more than the
    threshold at two adjacent recorded batch sizes of at least 10,000 points.
    Reports must come from the same recorded environment and workload contract.
    """

    if not 0 < threshold < 1:
        raise ReleaseBenchmarkError("threshold must be between 0 and 1")
    _matching_context(baseline, candidate)

    baseline_rows = _batch_rows(baseline)
    candidate_rows = _batch_rows(candidate)
    sizes = sorted(set(baseline_rows) & set(candidate_rows))
    sizes = [size for size in sizes if size >= 10_000]
    if len(sizes) < 2:
        raise ReleaseBenchmarkError("comparison requires at least two batch sizes >= 10,000")

    rows: list[dict[str, Any]] = []
    slowed_sizes: list[int] = []
    for size in sizes:
        baseline_rate = float(baseline_rows[size]["median_operations_per_second"])
        candidate_rate = float(candidate_rows[size]["median_operations_per_second"])
        if baseline_rate <= 0 or candidate_rate <= 0:
            raise ReleaseBenchmarkError("throughput values must be positive")
        ratio = candidate_rate / baseline_rate
        slowdown = 1.0 - ratio
        crossed = slowdown > threshold
        if crossed:
            slowed_sizes.append(size)
        rows.append(
            {
                "points": size,
                "baseline_operations_per_second": baseline_rate,
                "candidate_operations_per_second": candidate_rate,
                "candidate_to_baseline_ratio": ratio,
                "slowdown_fraction": slowdown,
                "threshold_crossed": crossed,
            }
        )

    adjacent_pairs = [
        [left, right]
        for left, right in pairwise(sizes)
        if left in slowed_sizes and right in slowed_sizes
    ]
    return {
        "schema_version": 1,
        "baseline_version": baseline["environment"]["feregion"],
        "candidate_version": candidate["environment"]["feregion"],
        "threshold_fraction": threshold,
        "trigger_rule": "slowdown exceeds threshold at two adjacent batch sizes >=10000",
        "review_triggered": bool(adjacent_pairs),
        "triggering_adjacent_size_pairs": adjacent_pairs,
        "rows": rows,
        "environment": {
            field: baseline["environment"].get(field) for field in _REQUIRED_ENVIRONMENT_FIELDS
        },
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    """Render one human-reviewable release performance comparison."""

    lines = [
        "# feregion release benchmark comparison",
        "",
        f"Baseline: `{comparison['baseline_version']}`",
        f"Candidate: `{comparison['candidate_version']}`",
        f"Review trigger: **{'crossed' if comparison['review_triggered'] else 'not crossed'}**",
        "",
        "| Points | Baseline Mops/s | Candidate Mops/s | Ratio | Slowdown | Trigger at size |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for row in comparison["rows"]:
        lines.append(
            f"| {row['points']:,} | {row['baseline_operations_per_second'] / 1e6:.3f} | "
            f"{row['candidate_operations_per_second'] / 1e6:.3f} | "
            f"{row['candidate_to_baseline_ratio']:.3f}x | "
            f"{row['slowdown_fraction'] * 100:.1f}% | "
            f"{'yes' if row['threshold_crossed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "The decision is valid only for the recorded same-environment benchmark pair. "
            "CPU power/frequency policy must also be controlled externally.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Compare two benchmark JSON reports and emit JSON or Markdown."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--fail-on-trigger", action="store_true")
    args = parser.parse_args(argv)

    try:
        comparison = compare_reports(
            load_report(args.baseline), load_report(args.candidate), threshold=args.threshold
        )
    except (KeyError, TypeError, ValueError, ReleaseBenchmarkError) as exc:
        parser.exit(2, f"error: {exc}\n")

    if args.format == "json":
        text = json.dumps(comparison, indent=2, sort_keys=True) + "\n"
    else:
        text = render_markdown(comparison)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if args.fail_on_trigger and comparison["review_triggered"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
