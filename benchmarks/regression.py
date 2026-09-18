"""Project-owned release regression decision over normalized benchmark evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise

from .evidence import EvidenceRecord


@dataclass(frozen=True, slots=True)
class LoadComparison:
    """One comparable load-size slowdown observation."""

    load_size: int
    slowdown_fraction: float


@dataclass(frozen=True, slots=True)
class RegressionDecision:
    """Outcome of the project release-performance comparison rule."""

    complete: bool
    triggered: bool
    comparisons: tuple[LoadComparison, ...]
    reason: str | None = None


def _key(record: EvidenceRecord) -> tuple[object, ...]:
    return (
        record.case_id,
        record.case_version,
        record.load_size,
        record.machine,
        record.environment,
    )


def compare_release_evidence(
    baseline: Iterable[EvidenceRecord],
    candidate: Iterable[EvidenceRecord],
    *,
    case_id: str = "lookup_geographic_numbers",
    threshold: float = 0.25,
    minimum_load: int = 10_000,
) -> RegressionDecision:
    """Apply the accepted adjacent-load slowdown rule to comparable evidence."""

    baseline_map = {_key(record): record for record in baseline if record.case_id == case_id}
    candidate_map = {_key(record): record for record in candidate if record.case_id == case_id}
    comparisons: list[LoadComparison] = []
    for key, before in baseline_map.items():
        after = candidate_map.get(key)
        if after is None:
            continue
        if before.result_state != "measured" or after.result_state != "measured":
            continue
        if before.load_size is None or before.load_size < minimum_load:
            continue
        if before.statistic_seconds is None or after.statistic_seconds is None:
            continue
        if before.statistic_seconds <= 0:
            continue
        slowdown = after.statistic_seconds / before.statistic_seconds - 1.0
        comparisons.append(LoadComparison(before.load_size, slowdown))

    comparisons.sort(key=lambda item: item.load_size)
    if len(comparisons) < 2:
        return RegressionDecision(False, False, tuple(comparisons), "insufficient comparable loads")

    triggered = any(
        left.slowdown_fraction > threshold and right.slowdown_fraction > threshold
        for left, right in pairwise(comparisons)
    )
    return RegressionDecision(True, triggered, tuple(comparisons))
