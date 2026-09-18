"""Project-owned release regression decision over normalized benchmark evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise

from .asv_suite.contracts import STANDARD_LOAD_SIZES
from .evidence import EvidenceRecord


@dataclass(frozen=True, slots=True)
class LoadComparison:
    """One comparable load-size throughput-slowdown observation."""

    load_size: int
    slowdown_fraction: float
    baseline_operations_per_second: float
    candidate_operations_per_second: float


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
    required_loads: Iterable[int] | None = None,
) -> RegressionDecision:
    """Apply the accepted adjacent-load throughput-slowdown rule.

    Only records with measured timing, mapped semantic case versions, and passed
    correctness setup are eligible. Throughput is derived from the declared
    operation count and elapsed statistic. A 25% throughput slowdown therefore
    corresponds to a duration increase greater than one third, not 25%.
    """

    baseline_records = [record for record in baseline if record.case_id == case_id]
    candidate_records = [record for record in candidate if record.case_id == case_id]
    baseline_contexts = {(record.machine, record.environment) for record in baseline_records}
    candidate_contexts = {(record.machine, record.environment) for record in candidate_records}
    common_contexts = baseline_contexts & candidate_contexts
    if len(common_contexts) != 1:
        reason = (
            "no comparable machine/environment context"
            if not common_contexts
            else "multiple comparable machine/environment contexts; select one machine"
        )
        return RegressionDecision(False, False, (), reason)
    context = next(iter(common_contexts))

    baseline_map = {
        _key(record): record
        for record in baseline_records
        if (record.machine, record.environment) == context
    }
    candidate_map = {
        _key(record): record
        for record in candidate_records
        if (record.machine, record.environment) == context
    }
    comparisons: list[LoadComparison] = []
    measured_loads: set[int] = set()
    for key, before in baseline_map.items():
        after = candidate_map.get(key)
        if after is None:
            continue
        if before.result_state != "measured" or after.result_state != "measured":
            continue
        if before.correctness_state != "passed" or after.correctness_state != "passed":
            continue
        if before.case_version is None or after.case_version is None:
            continue
        if before.load_size is None or before.load_size < minimum_load:
            continue
        before_rate = before.operations_per_second
        after_rate = after.operations_per_second
        if before_rate is None or after_rate is None or before_rate <= 0:
            continue
        slowdown = 1.0 - after_rate / before_rate
        comparisons.append(
            LoadComparison(
                before.load_size,
                slowdown,
                before_rate,
                after_rate,
            )
        )
        measured_loads.add(before.load_size)

    comparisons.sort(key=lambda item: item.load_size)
    if required_loads is not None:
        required = {load for load in required_loads if load >= minimum_load}
        missing = sorted(required - measured_loads)
        if missing:
            return RegressionDecision(
                False,
                False,
                tuple(comparisons),
                f"missing comparable correctness-passed measured loads: {missing}",
            )

    if len(comparisons) < 2:
        return RegressionDecision(False, False, tuple(comparisons), "insufficient comparable loads")

    order = {load: index for index, load in enumerate(STANDARD_LOAD_SIZES)}
    triggered = any(
        left.slowdown_fraction > threshold
        and right.slowdown_fraction > threshold
        and order.get(right.load_size) == order.get(left.load_size, -2) + 1
        for left, right in pairwise(comparisons)
    )
    return RegressionDecision(True, triggered, tuple(comparisons))
