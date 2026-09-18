"""Normalize ASV result records for project-owned performance decisions."""

from __future__ import annotations

import ast
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from .asv_suite.contracts import CASES

ResultState = Literal[
    "measured",
    "not_applicable",
    "build_unavailable",
    "correctness_failed",
    "execution_failed",
    "missing",
]


class ResolvedRevisionLike(Protocol):
    """Minimum resolved-revision interface needed by evidence collection."""

    requested: str
    commit: str


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


_RESULT_METHOD_BY_CASE: dict[str, str] = {
    "lookup_geographic_number": "time_lookup_geographic_number",
    "lookup_geographic_region": "time_lookup_geographic_region",
    "geographic_number_to_name": "time_geographic_number_to_name",
    "lookup_geographic_numbers": "time_lookup_geographic_numbers",
    "lookup_seismic_number": "time_lookup_seismic_number",
    "lookup_seismic_region": "time_lookup_seismic_region",
    "lookup_seismic_numbers": "time_lookup_seismic_numbers",
    "geographic_numbers_to_seismic_numbers": "time_geographic_numbers_to_seismic_numbers",
    "geographic_numbers_to_names": "time_geographic_numbers_to_names",
    "pandas_lookup_numbers": "time_pandas_lookup_numbers",
    "pandas_lookup_numbers_and_names": "time_pandas_lookup_numbers_and_names",
}


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

    ASV 0.6.x stores ``null`` for failed/missing execution and ``NaN`` for an
    explicit benchmark skip. The latter maps to project state ``not_applicable``;
    a null result maps to ``execution_failed`` unless no result key exists at all.
    """

    if "result" not in result:
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

    raw_result = result.get("result")
    raw_samples = result.get("samples")
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
            "execution_failed",
            (),
            None,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            "ASV benchmark result is null (failed or unavailable execution)",
        )
    if isinstance(summary, float) and math.isnan(summary):
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
            "ASV benchmark was explicitly skipped/not applicable",
        )

    samples: tuple[float, ...] = ()
    if raw_samples is not None:
        selected = raw_samples
        # ASV v2 stores samples as a parameter-list aligned with ``result``.
        # Do not infer parameterization from the first sample entry: a failed
        # first parameter is represented by ``None`` while later entries can
        # still contain sample lists.
        if isinstance(raw_result, list) and isinstance(raw_samples, list):
            if parameter_index >= len(raw_samples):
                raise ValueError("parameter_index is outside ASV samples list")
            selected = raw_samples[parameter_index]
        if selected is None:
            samples = ()
        elif isinstance(selected, list):
            if any(isinstance(value, list) for value in selected):
                raise ValueError("unsupported nested ASV sample layout for one parameter value")
            samples = tuple(float(value) for value in selected if value is not None)
        else:
            raise ValueError(
                f"unsupported ASV samples value for one parameter: {type(selected).__name__}"
            )

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


def _result_object(payload: dict[str, Any], benchmark_name: str) -> dict[str, Any] | None:
    """Decode one ASV v2 result row using its declared column order."""

    values = payload.get("results", {}).get(benchmark_name)
    if values is None:
        return None
    columns = payload.get("result_columns")
    if not isinstance(columns, list) or not isinstance(values, list):
        raise ValueError("unsupported ASV result-file layout")
    return dict(zip(columns, values, strict=False))


def _case_for_benchmark_name(name: str) -> str | None:
    """Map an ASV fully qualified timing method back to a project case ID."""

    for case_id, method_name in _RESULT_METHOD_BY_CASE.items():
        if name == method_name or name.endswith(f".{method_name}"):
            return case_id
    return None


def _parameter_values(result: dict[str, Any]) -> tuple[int, ...]:
    """Decode the maintained one-dimensional ``size`` ASV parameter."""

    params = result.get("params")
    if not params:
        return ()
    if not isinstance(params, list) or len(params) != 1 or not isinstance(params[0], list):
        raise ValueError("unsupported ASV parameter layout for feregion benchmark")
    values: list[int] = []
    for raw in params[0]:
        value = ast.literal_eval(str(raw))
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"unexpected ASV load parameter value: {raw!r}")
        values.append(value)
    return tuple(values)


def collect_asv_evidence(
    results_dir: Path,
    *,
    campaign_id: str,
    revisions: Sequence[ResolvedRevisionLike],
    cases: Sequence[str],
    load_sizes: Sequence[int],
    machine: str | None = None,
) -> list[EvidenceRecord]:
    """Collect normalized evidence for selected commits from retained ASV results.

    The collector reads ASV's documented v2 JSON result files and ignores machine
    metadata and unrelated revisions. It does not rerun benchmarks. Multiple
    machine/environment contexts are preserved so the caller can reject ambiguous
    comparisons instead of silently mixing hosts or dependency sets.
    """

    selected_commits = {revision.commit for revision in revisions}
    selected_cases = set(cases)
    selected_loads = set(load_sizes)
    records: list[EvidenceRecord] = []
    if not results_dir.is_dir():
        return records

    for path in sorted(results_dir.glob("*/*.json")):
        if machine is not None and path.parent.name != machine:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        commit = payload.get("commit_hash")
        if commit not in selected_commits or not isinstance(payload.get("results"), dict):
            continue
        environment = payload.get("env_name")
        result_machine = path.parent.name
        for benchmark_name in payload["results"]:
            case_id = _case_for_benchmark_name(benchmark_name)
            if case_id is None or case_id not in selected_cases:
                continue
            decoded = _result_object(payload, benchmark_name)
            if decoded is None:
                continue
            case = CASES[case_id]
            if case.load_parameterized:
                parameter_values = _parameter_values(decoded)
                for index, load_size in enumerate(parameter_values):
                    if load_size not in selected_loads:
                        continue
                    records.append(
                        normalize_asv_result(
                            case_id=case_id,
                            case_version=case.case_version,
                            revision=commit,
                            campaign_id=campaign_id,
                            result=decoded,
                            parameter_index=index,
                            load_size=load_size,
                            machine=result_machine,
                            environment=str(environment) if environment is not None else None,
                        )
                    )
            else:
                records.append(
                    normalize_asv_result(
                        case_id=case_id,
                        case_version=case.case_version,
                        revision=commit,
                        campaign_id=campaign_id,
                        result=decoded,
                        machine=result_machine,
                        environment=str(environment) if environment is not None else None,
                    )
                )
    return records
