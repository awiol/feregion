"""Normalize ASV result records for project-owned performance decisions."""

from __future__ import annotations

import ast
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal, Protocol

from .asv_suite.contracts import CASES, BenchmarkCase

ResultState = Literal[
    "measured",
    "not_applicable",
    "build_unavailable",
    "correctness_failed",
    "execution_failed",
    "incompatible",
    "missing",
]
CorrectnessState = Literal["passed", "failed", "not_applicable", "unknown"]


class ResolvedRevisionLike(Protocol):
    """Minimum resolved-revision interface needed by evidence collection."""

    requested: str
    commit: str


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Stable project evidence independent of incidental ASV JSON layout."""

    case_id: str
    case_version: int | None
    revision: str
    load_size: int | None
    result_state: ResultState
    correctness_state: CorrectnessState
    samples: tuple[float, ...]
    statistic_seconds: float | None
    operation_count_unit: str
    operations: int | None
    operations_per_second: float | None
    stored_benchmark_version: str | None
    machine: str | None
    environment: str | None
    campaign_id: str
    asv_version: str | None = None
    asv_runner_version: str | None = None
    reason: str | None = None
    source_result: str | None = None

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
    "seismic_numbers_to_names": "time_seismic_numbers_to_names",
    "pandas_lookup_numbers": "time_pandas_lookup_numbers",
    "pandas_lookup_numbers_and_names": "time_pandas_lookup_numbers_and_names",
    "pandas_lookup_inplace_numbers": "time_pandas_lookup_inplace_numbers",
    "pandas_lookup_inplace_numbers_and_names": "time_pandas_lookup_inplace_numbers_and_names",
    "pandas_lookup_inplace_seismic_numbers": "time_pandas_lookup_inplace_seismic_numbers",
    "internal_split_geographic_numbers": "time_internal_split_geographic_numbers",
    "internal_split_seismic_numbers": "time_internal_split_seismic_numbers",
    "stack_plus_geographic_numbers": "time_stack_plus_geographic_numbers",
    "obspy_geographic_number": "time_obspy_geographic_number",
    "source_reference_geographic_number": "time_source_reference_geographic_number",
    "source_reference_geographic_numbers": "time_source_reference_geographic_numbers",
}


def write_evidence(path: Path, records: Iterable[EvidenceRecord]) -> None:
    """Write normalized evidence as a stable JSON document."""

    payload = {"schema_version": 2, "records": [record.to_json() for record in records]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _flatten_numeric_samples(value: Any) -> tuple[float, ...]:
    """Flatten sample groups within one selected parameter without crossing parameters."""

    flattened: list[float] = []

    def visit(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, list):
            for child in item:
                visit(child)
            return
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(
                f"unsupported ASV sample leaf for one parameter: {type(item).__name__}"
            )
        flattened.append(float(item))

    visit(value)
    return tuple(flattened)


def _operations(case: BenchmarkCase, load_size: int | None) -> int | None:
    if case.operation_count in {"points", "rows"}:
        return load_size
    if case.operation_count == "calls":
        return 1
    return None


def normalize_asv_result(
    *,
    case_id: str,
    case_version: int | None,
    revision: str,
    campaign_id: str,
    result: dict[str, Any],
    parameter_index: int = 0,
    load_size: int | None = None,
    machine: str | None = None,
    environment: str | None = None,
    stored_benchmark_version: str | None = None,
    correctness_state: CorrectnessState = "unknown",
    state_override: ResultState | None = None,
    state_reason: str | None = None,
    asv_version: str | None = None,
    asv_runner_version: str | None = None,
    source_result: str | None = None,
) -> EvidenceRecord:
    """Normalize one supported ASV benchmark-result object.

    Parameter-specific sample groups may contain one or more nested ASV repeat/round
    lists. They are flattened only after selecting the requested parameter index, so
    samples from different load values can never be mixed.
    """

    case = CASES[case_id]
    operations = _operations(case, load_size)

    if "result" not in result:
        state = state_override or "missing"
        return EvidenceRecord(
            case_id,
            case_version,
            revision,
            load_size,
            state,
            correctness_state,
            (),
            None,
            case.operation_count,
            operations,
            None,
            stored_benchmark_version,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            state_reason or "ASV result is missing",
            source_result,
        )

    raw_result = result.get("result")
    raw_samples = result.get("samples")
    if isinstance(raw_result, list):
        if parameter_index >= len(raw_result):
            raise ValueError("parameter_index is outside ASV result list")
        summary = raw_result[parameter_index]
    else:
        summary = raw_result

    if state_override is not None and state_override != "measured":
        return EvidenceRecord(
            case_id,
            case_version,
            revision,
            load_size,
            state_override,
            correctness_state,
            (),
            None,
            case.operation_count,
            operations,
            None,
            stored_benchmark_version,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            state_reason,
            source_result,
        )

    if summary is None:
        return EvidenceRecord(
            case_id,
            case_version,
            revision,
            load_size,
            "execution_failed",
            correctness_state,
            (),
            None,
            case.operation_count,
            operations,
            None,
            stored_benchmark_version,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            state_reason or "ASV benchmark result is null",
            source_result,
        )
    if isinstance(summary, float) and math.isnan(summary):
        return EvidenceRecord(
            case_id,
            case_version,
            revision,
            load_size,
            "not_applicable",
            "not_applicable",
            (),
            None,
            case.operation_count,
            operations,
            None,
            stored_benchmark_version,
            machine,
            environment,
            campaign_id,
            asv_version,
            asv_runner_version,
            state_reason or "ASV benchmark was explicitly skipped/not applicable",
            source_result,
        )

    samples: tuple[float, ...] = ()
    if raw_samples is not None:
        selected = raw_samples
        if isinstance(raw_result, list) and isinstance(raw_samples, list):
            if parameter_index >= len(raw_samples):
                raise ValueError("parameter_index is outside ASV samples list")
            selected = raw_samples[parameter_index]
        samples = _flatten_numeric_samples(selected)

    statistic = float(summary)
    throughput = None
    if operations is not None and statistic > 0:
        throughput = operations / statistic
    return EvidenceRecord(
        case_id=case_id,
        case_version=case_version,
        revision=revision,
        load_size=load_size,
        result_state="measured",
        correctness_state=correctness_state,
        samples=samples,
        statistic_seconds=statistic,
        operation_count_unit=case.operation_count,
        operations=operations,
        operations_per_second=throughput,
        stored_benchmark_version=stored_benchmark_version,
        machine=machine,
        environment=environment,
        campaign_id=campaign_id,
        asv_version=asv_version,
        asv_runner_version=asv_runner_version,
        reason=state_reason,
        source_result=source_result,
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


def _stored_version(result: dict[str, Any]) -> str | None:
    value = result.get("version")
    return value if isinstance(value, str) and value else None


def _state_marker(
    results_dir: Path,
    *,
    commit: str,
    environment: str | None,
    case_id: str,
    load_size: int | None,
) -> dict[str, Any] | None:
    if environment is None:
        return None
    load = "scalar" if load_size is None else str(load_size)
    path = results_dir.parent / "feregion-state" / commit / environment / case_id / f"{load}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _marker_interpretation(
    marker: dict[str, Any] | None,
) -> tuple[ResultState | None, CorrectnessState, str | None]:
    if marker is None:
        return None, "unknown", None
    state = marker.get("state")
    reason = marker.get("reason") if isinstance(marker.get("reason"), str) else None
    if state == "correctness_passed":
        return None, "passed", reason
    if state == "correctness_failed":
        return "correctness_failed", "failed", reason
    if state == "build_unavailable":
        return "build_unavailable", "unknown", reason
    if state == "not_applicable":
        return "not_applicable", "not_applicable", reason
    if state == "execution_failed":
        return "execution_failed", "unknown", reason
    return None, "unknown", reason


def _version_mapping(
    case: BenchmarkCase,
    stored_version: str | None,
) -> tuple[int | None, ResultState | None, str | None]:
    if case.accepts_asv_version(stored_version):
        return case.case_version, None, None
    return (
        None,
        "incompatible",
        "stored ASV benchmark version is not mapped to the current project case version",
    )


def _run_record(
    results_dir: Path,
    *,
    campaign_id: str,
    commit: str,
) -> dict[str, Any] | None:
    """Return one retained campaign-run record when available."""

    path = results_dir.parent / "feregion-runs" / campaign_id / f"{commit}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _run_failure_record(
    results_dir: Path,
    *,
    campaign_id: str,
    commit: str,
) -> dict[str, Any] | None:
    """Return a retained nonzero run record when benchmark JSON was not written."""

    payload = _run_record(results_dir, campaign_id=campaign_id, commit=commit)
    if payload is not None and payload.get("returncode") not in (None, 0):
        return payload
    return None


def _tool_identity(run_record: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Extract exact ASV tool identities from one retained run record."""

    if run_record is None:
        return None, None
    asv = run_record.get("asv_version")
    runner = run_record.get("asv_runner_version")
    return (str(asv) if asv is not None else None, str(runner) if runner is not None else None)


def _environment_runner_version(
    results_dir: Path,
    *,
    commit: str,
    environment: str | None,
) -> str | None:
    """Return the asv-runner version observed inside one retained ASV environment."""

    if environment is None:
        return None
    digest = sha256(environment.encode("utf-8")).hexdigest()[:16]
    path = results_dir.parent / "feregion-environments" / commit / f"{digest}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    value = payload.get("asv_runner_version") if isinstance(payload, dict) else None
    return str(value) if value is not None else None


def collect_asv_evidence(
    results_dir: Path,
    *,
    campaign_id: str,
    revisions: Sequence[ResolvedRevisionLike],
    cases: Sequence[str],
    load_sizes: Sequence[int],
    machine: str | None = None,
    environments: Sequence[str] | None = None,
) -> list[EvidenceRecord]:
    """Collect normalized evidence for selected commits from retained ASV results.

    Retained ASV benchmark-version identity is mapped explicitly to project case
    versions. Setup-state sidecars distinguish not-applicable, oracle/environment
    unavailability, correctness failure, execution failure, and valid timing.
    """

    selected_commits = {revision.commit for revision in revisions}
    selected_cases = set(cases)
    selected_loads = set(load_sizes)
    selected_environments = set(environments) if environments is not None else None
    records: list[EvidenceRecord] = []
    if not results_dir.is_dir():
        return records

    commits_with_results: set[str] = set()
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
        environment_value = payload.get("env_name")
        environment = str(environment_value) if environment_value is not None else None
        if selected_environments is not None and environment not in selected_environments:
            continue
        commits_with_results.add(commit)
        result_machine = path.parent.name
        run_record = _run_record(results_dir, campaign_id=campaign_id, commit=commit)
        asv_version, run_runner_version = _tool_identity(run_record)
        environment_runner_version = _environment_runner_version(
            results_dir, commit=commit, environment=environment
        )
        asv_runner_version = environment_runner_version or run_runner_version
        for benchmark_name in payload["results"]:
            case_id = _case_for_benchmark_name(benchmark_name)
            if case_id is None or case_id not in selected_cases:
                continue
            decoded = _result_object(payload, benchmark_name)
            if decoded is None:
                continue
            case = CASES[case_id]
            stored_version = _stored_version(decoded)
            mapped_version, version_state, version_reason = _version_mapping(case, stored_version)
            if case.load_parameterized:
                parameter_values = _parameter_values(decoded)
                for index, load_size in enumerate(parameter_values):
                    if load_size not in selected_loads:
                        continue
                    marker = _state_marker(
                        results_dir,
                        commit=commit,
                        environment=environment,
                        case_id=case_id,
                        load_size=load_size,
                    )
                    marker_state, correctness, marker_reason = _marker_interpretation(marker)
                    state_override = version_state or marker_state
                    reason = version_reason or marker_reason
                    records.append(
                        normalize_asv_result(
                            case_id=case_id,
                            case_version=mapped_version,
                            revision=commit,
                            campaign_id=campaign_id,
                            result=decoded,
                            parameter_index=index,
                            load_size=load_size,
                            machine=result_machine,
                            environment=environment,
                            stored_benchmark_version=stored_version,
                            correctness_state=correctness,
                            state_override=state_override,
                            state_reason=reason,
                            source_result=str(path),
                            asv_version=asv_version,
                            asv_runner_version=asv_runner_version,
                        )
                    )
            else:
                marker = _state_marker(
                    results_dir,
                    commit=commit,
                    environment=environment,
                    case_id=case_id,
                    load_size=None,
                )
                marker_state, correctness, marker_reason = _marker_interpretation(marker)
                state_override = version_state or marker_state
                reason = version_reason or marker_reason
                records.append(
                    normalize_asv_result(
                        case_id=case_id,
                        case_version=mapped_version,
                        revision=commit,
                        campaign_id=campaign_id,
                        result=decoded,
                        machine=result_machine,
                        environment=environment,
                        stored_benchmark_version=stored_version,
                        correctness_state=correctness,
                        state_override=state_override,
                        state_reason=reason,
                        source_result=str(path),
                        asv_version=asv_version,
                        asv_runner_version=asv_runner_version,
                    )
                )

    for revision in revisions:
        if revision.commit in commits_with_results:
            continue
        failed_run = _run_failure_record(
            results_dir,
            campaign_id=campaign_id,
            commit=revision.commit,
        )
        if failed_run is None:
            continue
        asv_version, asv_runner_version = _tool_identity(failed_run)
        reason = (
            "ASV revision run failed before retaining benchmark-level results; "
            "the retained run record does not identify a narrower build/setup phase"
        )
        for case_id in cases:
            case = CASES[case_id]
            loads: tuple[int | None, ...] = (
                tuple(load_sizes) if case.load_parameterized else (None,)
            )
            for load_size in loads:
                operations = _operations(case, load_size)
                records.append(
                    EvidenceRecord(
                        case_id=case_id,
                        case_version=case.case_version,
                        revision=revision.commit,
                        load_size=load_size,
                        result_state="execution_failed",
                        correctness_state="unknown",
                        samples=(),
                        statistic_seconds=None,
                        operation_count_unit=case.operation_count,
                        operations=operations,
                        operations_per_second=None,
                        stored_benchmark_version=None,
                        machine=machine,
                        environment=None,
                        campaign_id=campaign_id,
                        reason=reason,
                        asv_version=asv_version,
                        asv_runner_version=asv_runner_version,
                    )
                )
    return records
