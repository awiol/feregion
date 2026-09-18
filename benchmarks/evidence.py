"""Normalize ASV result records for project-owned performance decisions."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ResultState = Literal[
    "measured",
    "not_applicable",
    "build_unavailable",
    "correctness_failed",
    "execution_failed",
    "missing",
]


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Stable project evidence independent of incidental ASV JSON layout."""

    case_id: str
    case_version: int
    revision: str
    load_size: int | None
    result_state: ResultState
    samples: tuple[float, ...]
    statistic_seconds: float | None
    machine: str | None
    environment: str | None
    campaign_id: str
    asv_version: str | None = None
    asv_runner_version: str | None = None
    reason: str | None = None

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        data = asdict(self)
        data["samples"] = list(self.samples)
        return data


def write_evidence(path: Path, records: Iterable[EvidenceRecord]) -> None:
    """Write normalized evidence as a stable JSON document."""

    payload = {"schema_version": 1, "records": [record.to_json() for record in records]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_asv_result(
    *,
    case_id: str,
    case_version: int,
    revision: str,
    campaign_id: str,
    result: dict[str, Any],
    parameter_index: int = 0,
    load_size: int | None = None,
    machine: str | None = None,
    environment: str | None = None,
    asv_version: str | None = None,
    asv_runner_version: str | None = None,
) -> EvidenceRecord:
    """Normalize one supported ASV benchmark-result object.

    ASV storage parsing is intentionally isolated here. The supported 0.6.x
    fixture shape uses ``result`` for summary values and ``samples`` for raw
    measurements, each optionally parameterized as a list-of-values per
    benchmark parameter combination.
    """

    raw_result = result.get("result")
    raw_samples = result.get("samples")
    if raw_result is None:
        return EvidenceRecord(
            case_id,
            case_version,
            revision,
            load_size,
            "missing",
            (),
            None,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            "ASV result is missing",
        )

    if isinstance(raw_result, list):
        if parameter_index >= len(raw_result):
            raise ValueError("parameter_index is outside ASV result list")
        summary = raw_result[parameter_index]
    else:
        summary = raw_result

    if summary is None:
        return EvidenceRecord(
            case_id,
            case_version,
            revision,
            load_size,
            "not_applicable",
            (),
            None,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            "ASV benchmark result is not applicable or skipped",
        )

    samples: tuple[float, ...] = ()
    if raw_samples is not None:
        selected = raw_samples
        if isinstance(raw_samples, list) and raw_samples and isinstance(raw_samples[0], list):
            if parameter_index >= len(raw_samples):
                raise ValueError("parameter_index is outside ASV samples list")
            selected = raw_samples[parameter_index]
        if isinstance(selected, list):
            samples = tuple(float(value) for value in selected if value is not None)

    return EvidenceRecord(
        case_id=case_id,
        case_version=case_version,
        revision=revision,
        load_size=load_size,
        result_state="measured",
        samples=samples,
        statistic_seconds=float(summary),
        machine=machine,
        environment=environment,
        campaign_id=campaign_id,
        asv_version=asv_version,
        asv_runner_version=asv_runner_version,
    )
