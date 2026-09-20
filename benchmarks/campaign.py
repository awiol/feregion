"""Thin campaign planner and ASV command adapter for feregion benchmarks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from itertools import product
from pathlib import Path
from typing import Any

from .asv_suite.contracts import CASES, STANDARD_LOAD_SIZES
from .evidence import collect_asv_evidence, write_evidence
from .regression import RegressionDecision, compare_release_evidence

PROFILE_CONFIG: dict[str, dict[str, Any]] = {
    "release-history": {
        "pythons": ["3.12"],
        "matrix": {"req": {"numpy": ["1.26.4"], "pandas": ["2.1.4"]}},
    },
    "python-supported": {
        "pythons": ["3.11", "3.12", "3.13", "3.14"],
        "matrix": {"req": {"numpy": ["2.3.5"], "pandas": ["2.3.3"]}},
    },
    "numpy-sensitivity": {
        "pythons": ["3.12"],
        "matrix": {
            "req": {
                "numpy": ["1.26.4", "2.0.2", "2.2.6", "2.5.2"],
                "pandas": ["2.1.4"],
            }
        },
    },
    "pandas-sensitivity": {
        "pythons": ["3.12"],
        "matrix": {
            "req": {
                "numpy": ["1.26.4"],
                "pandas": ["2.1.4", "2.2.3", "2.3.3", "3.0.5"],
            }
        },
    },
    "dependency-matrix": {
        "pythons": ["3.12"],
        "matrix": {"req": {"numpy": ["1.26.4"], "pandas": ["2.1.4"]}},
        "include": [
            {"python": "3.12", "req": {"numpy": "2.0.2", "pandas": "2.1.4"}},
            {"python": "3.12", "req": {"numpy": "2.2.6", "pandas": "2.1.4"}},
            {"python": "3.12", "req": {"numpy": "2.5.2", "pandas": "2.1.4"}},
            {"python": "3.12", "req": {"numpy": "1.26.4", "pandas": "2.2.3"}},
            {"python": "3.12", "req": {"numpy": "1.26.4", "pandas": "2.3.3"}},
            {"python": "3.12", "req": {"numpy": "1.26.4", "pandas": "3.0.5"}},
        ],
    },
    "reference-comparison": {
        "pythons": ["3.12"],
        "matrix": {
            "req": {
                # The campaign wrapper applies the matching pip constraints
                # file to every ASV environment-install subprocess. This is
                # required because ASV 0.6.6 installs declarations one at a
                # time with ``pip --upgrade``. Environment preflight then
                # verifies the final installed state before timing is accepted.
                "numpy": ["1.26.4"],
                "pandas": ["2.1.4"],
                "obspy": ["1.4.2"],
                "setuptools": ["81.0.0"],
            }
        },
    },
}

ASV_BUILD_COMMAND = [
    "python -m pip wheel --no-deps -w {build_cache_dir} {build_dir}",
]
ASV_INSTALL_COMMAND = [
    "in-dir={env_dir} python -m pip install --no-deps --force-reinstall {wheel_file}",
]
REFERENCE_CONSTRAINTS = Path("benchmarks/constraints/reference-comparison.txt")
DEFAULT_MACHINE_POLICY = "same-machine-environment-case-version"
SUPPORTED_REPORT_STEPS = frozenset({"asv-site"})
EXPLICIT_BASELINE_MARKER = "__BASELINE__"


def benchmark_tool_versions() -> dict[str, str | None]:
    """Return benchmark-tool identities installed in the operator environment.

    ASV itself executes from this environment. ``asv-runner`` is also captured here as
    pre-run provenance, but the environment preflight records the runner version that
    actually executes inside each ASV benchmark environment. Missing distributions remain
    explicit ``None`` values.
    """

    def installed(distribution: str) -> str | None:
        try:
            return distribution_version(distribution)
        except PackageNotFoundError:
            return None

    return {"asv_version": installed("asv"), "asv_runner_version": installed("asv-runner")}


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_environment_names(profile_name: str) -> tuple[str, ...]:
    """Return the ASV environment names allowed by one maintained profile.

    The project release gate uses this explicit profile identity when reading retained
    ASV results. This prevents a benchmark result from another campaign profile from
    being relabeled as release-comparison evidence merely because commit, case, and
    load size happen to match.
    """

    profile = PROFILE_CONFIG[profile_name]
    environments: set[str] = set()

    def add_environment(python: str, requirements: dict[str, str]) -> None:
        parts = ["uv", f"py{python}"]
        parts.extend(f"{name}{requirements[name]}" for name in sorted(requirements))
        environments.add("-".join(parts))

    matrix = profile.get("matrix", {}).get("req", {})
    names = list(matrix)
    values = [value if isinstance(value, list) else [value] for value in matrix.values()]
    for python in profile["pythons"]:
        combinations = product(*values) if values else [()]
        for combination in combinations:
            add_environment(python, dict(zip(names, combination, strict=True)))

    for include in profile.get("include", []):
        add_environment(str(include["python"]), dict(include.get("req", {})))

    return tuple(sorted(environments))


_REVISION_META_CHARS = re.compile(r"(?:\.\.|@\{|[\s~^:?*\[\\])")
_HEX_COMMIT = re.compile(r"^[0-9A-Fa-f]{7,40}$")


@dataclass(frozen=True, slots=True)
class ResolvedRevision:
    """One operator revision identity resolved to one immutable Git commit."""

    requested: str
    commit: str

    @property
    def asv_run_selector(self) -> str:
        """Return Git syntax that selects exactly this commit for ``asv run``."""

        return f"{self.commit}^!"


def _validate_revision_identity(revision: str) -> None:
    """Reject Git range/expression syntax from campaign revision identities."""

    if not revision:
        raise ValueError("campaign revision identity must not be empty")
    if revision.startswith("-") or _REVISION_META_CHARS.search(revision):
        raise ValueError(
            f"campaign revision must be one ref/commit identity, not Git range syntax: {revision!r}"
        )
    if revision == "HEAD" or _HEX_COMMIT.fullmatch(revision):
        return
    # Git ref names cannot contain these expression characters. Remaining names
    # are allowed here and are authoritatively resolved by ``git rev-parse``.


def resolve_revision(revision: str, *, repository: Path) -> ResolvedRevision:
    """Resolve one campaign revision to an immutable commit or fail preflight."""

    _validate_revision_identity(revision)
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=repository.resolve(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "revision did not resolve to a commit"
        raise ValueError(f"cannot resolve campaign revision {revision!r}: {detail}")
    commit = completed.stdout.strip()
    if not re.fullmatch(r"[0-9A-Fa-f]{40}", commit):
        raise ValueError(f"Git returned an unexpected commit identity for {revision!r}: {commit!r}")
    return ResolvedRevision(revision, commit.lower())


def resolve_revisions(campaign: Campaign, *, repository: Path) -> tuple[ResolvedRevision, ...]:
    """Resolve all selected campaign revisions before invoking ASV."""

    return tuple(
        resolve_revision(revision, repository=repository) for revision in campaign.revisions
    )


@dataclass(frozen=True, slots=True)
class Campaign:
    """Resolved operator intent for one benchmark campaign."""

    campaign_id: str
    purpose: str
    revisions: tuple[str, ...]
    cases: tuple[str, ...]
    load_sizes: tuple[int, ...]
    repetitions: int
    rounds: int
    environment_profile: str
    record_samples: bool
    machine_policy: str = DEFAULT_MACHINE_POLICY
    report_steps: tuple[str, ...] = ()

    @classmethod
    def from_toml(cls, path: Path) -> Campaign:
        """Load and validate a campaign TOML file."""

        with path.open("rb") as handle:
            data = tomllib.load(handle)
        config = data.get("campaign", data)
        campaign = cls(
            campaign_id=str(config["id"]),
            purpose=str(config.get("purpose", "benchmark campaign")),
            revisions=tuple(str(value) for value in config["revisions"]),
            cases=tuple(str(value) for value in config.get("cases", CASES)),
            load_sizes=tuple(int(value) for value in config.get("load_sizes", STANDARD_LOAD_SIZES)),
            repetitions=int(config.get("repetitions", 5)),
            rounds=int(config.get("rounds", 3)),
            environment_profile=str(config.get("environment_profile", "release-history")),
            record_samples=bool(config.get("record_samples", True)),
            machine_policy=str(config.get("machine_policy", DEFAULT_MACHINE_POLICY)),
            report_steps=tuple(str(value) for value in config.get("report_steps", ())),
        )
        campaign.validate()
        return campaign

    def with_explicit_baseline(self, baseline: str | None) -> Campaign:
        """Bind a required release baseline supplied by the operator.

        Campaign source may contain ``__BASELINE__`` only as a stable placeholder.
        The placeholder never resolves implicitly: the operator must supply one Git
        revision/commit identity, which is then retained in the effective plan before
        timing starts. Campaigns without the placeholder reject an unrelated baseline
        argument so release intent cannot silently leak into another campaign.
        """

        requires_baseline = EXPLICIT_BASELINE_MARKER in self.revisions
        if requires_baseline and baseline is None:
            raise ValueError(
                f"campaign {self.campaign_id!r} requires an explicit --baseline revision"
            )
        if not requires_baseline and baseline is not None:
            raise ValueError(f"campaign {self.campaign_id!r} does not accept --baseline")
        if baseline is None:
            return self
        _validate_revision_identity(baseline)
        revisions = tuple(
            baseline if item == EXPLICIT_BASELINE_MARKER else item for item in self.revisions
        )
        return replace(self, revisions=revisions)

    def validate(self) -> None:
        """Reject campaign values that cannot map to the maintained contract."""

        if not self.revisions:
            raise ValueError("campaign must select at least one revision")
        if not self.cases:
            raise ValueError("campaign must select at least one benchmark case")
        if not self.load_sizes:
            raise ValueError("campaign must select at least one load size")
        unknown = sorted(set(self.cases) - CASES.keys())
        if unknown:
            raise ValueError(f"unknown benchmark cases: {', '.join(unknown)}")
        invalid_sizes = sorted(set(self.load_sizes) - set(STANDARD_LOAD_SIZES))
        if invalid_sizes:
            raise ValueError(f"unsupported load sizes: {invalid_sizes}")
        if self.repetitions < 1 or self.rounds < 1:
            raise ValueError("repetitions and rounds must be positive integers")
        if self.environment_profile not in PROFILE_CONFIG:
            raise ValueError(f"unknown environment profile: {self.environment_profile}")
        if self.machine_policy != DEFAULT_MACHINE_POLICY:
            raise ValueError(f"unsupported machine/comparability policy: {self.machine_policy}")
        unknown_report_steps = sorted(set(self.report_steps) - SUPPORTED_REPORT_STEPS)
        if unknown_report_steps:
            raise ValueError(f"unsupported report steps: {', '.join(unknown_report_steps)}")

    def plan(
        self,
        *,
        repository: Path,
        resolved_revisions: Sequence[ResolvedRevision] | None = None,
        append_samples: bool = False,
        source_config: Path | None = None,
        tool_versions: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        """Return the effective, inspectable campaign contract.

        The returned plan contains the immutable revision identities, effective timing
        controls, comparability policy, requested report steps, run-time sample append
        mode, source-config identity when supplied, and operator benchmark-tool versions
        when installed. This is the content later retained as a content-addressed plan.
        """

        resolved = (
            tuple(resolved_revisions)
            if resolved_revisions is not None
            else resolve_revisions(self, repository=repository)
        )
        result = asdict(self)
        result["profile"] = PROFILE_CONFIG[self.environment_profile]
        result["case_versions"] = {case: CASES[case].case_version for case in self.cases}
        result["resolved_revisions"] = [asdict(item) for item in resolved]
        result["append_samples"] = append_samples
        result["tool_versions"] = tool_versions or benchmark_tool_versions()
        if source_config is not None:
            source = source_config.resolve()
            try:
                source_name = source.relative_to(repository.resolve()).as_posix()
            except ValueError:
                source_name = str(source)
            result["source_config"] = {"path": source_name, "sha256": _sha256(source)}
        return result


def build_asv_config(
    campaign: Campaign,
    *,
    repository: Path,
    resolved_revisions: Sequence[ResolvedRevision] | None = None,
) -> dict[str, Any]:
    """Build the bounded ASV configuration for one campaign."""

    profile = PROFILE_CONFIG[campaign.environment_profile]
    branches = (
        [item.commit for item in resolved_revisions]
        if resolved_revisions is not None
        else list(campaign.revisions)
    )
    config = {
        "version": 1,
        "project": "feregion",
        "repo": str(repository.resolve()),
        "branches": branches,
        "environment_type": "uv",
        "pythons": profile["pythons"],
        "matrix": profile["matrix"],
        "benchmark_dir": "benchmarks/asv_suite",
        "env_dir": ".asv/env",
        "results_dir": ".asv/results",
        "html_dir": ".asv/html",
        "build_command": list(ASV_BUILD_COMMAND),
        "install_command": list(ASV_INSTALL_COMMAND),
        "plugins": [".benchmarks.asv_plugin"],
    }
    if "include" in profile:
        config["include"] = profile["include"]
    return config


def benchmark_regex(campaign: Campaign) -> str:
    """Return an ASV regex selecting the requested semantic cases and load parameters."""

    escaped_cases = [re.escape(case) for case in campaign.cases]
    if set(campaign.load_sizes) == set(STANDARD_LOAD_SIZES):
        return "|".join(escaped_cases)

    scalar_cases = [
        re.escape(case) for case in campaign.cases if not CASES[case].load_parameterized
    ]
    load_cases = [re.escape(case) for case in campaign.cases if CASES[case].load_parameterized]
    expressions: list[str] = []
    if scalar_cases:
        expressions.append(rf"(?:{'|'.join(scalar_cases)})$")
    if load_cases:
        size_expr = "|".join(re.escape(str(size)) for size in campaign.load_sizes)
        expressions.append(rf"(?:{'|'.join(load_cases)})\((?:{size_expr})\)$")
    return "|".join(expressions)


def _run_asv(
    campaign: Campaign,
    command: Sequence[str],
    *,
    repository: Path,
    resolved_revisions: Sequence[ResolvedRevision] | None = None,
) -> int:
    """Run one ASV subcommand with a temporary config rooted at the repository."""

    if not command:
        raise ValueError("ASV command must contain a subcommand")

    repository = repository.resolve()
    config = build_asv_config(
        campaign, repository=repository, resolved_revisions=resolved_revisions
    )
    with tempfile.NamedTemporaryFile(
        "w",
        prefix=".asv-campaign-",
        suffix=".json",
        dir=repository,
        delete=False,
        encoding="utf-8",
    ) as handle:
        json.dump(config, handle, indent=2)
        config_path = Path(handle.name)
    try:
        environment = os.environ.copy()
        if campaign.environment_profile == "reference-comparison":
            constraints = (repository / REFERENCE_CONSTRAINTS).resolve()
            if not constraints.is_file():
                raise FileNotFoundError(
                    f"reference-comparison constraints file is missing: {constraints}"
                )
            # ASV 0.6.6's uv environment installs matrix and build requirements
            # one declaration at a time with ``pip install --upgrade``. Apply one
            # process-level constraint set so later declarations cannot silently
            # upgrade an earlier exact matrix pin. This also constrains the
            # project build-system Setuptools requirement for ObsPy 1.4.2
            # compatibility. The benchmark-side environment preflight verifies
            # the final installed state independently before accepting timing.
            environment["PIP_CONSTRAINT"] = str(constraints)
        completed = subprocess.run(
            ["asv", *command, "--config", str(config_path)],
            cwd=repository,
            env=environment,
        )
        return completed.returncode
    finally:
        config_path.unlink(missing_ok=True)


def _write_plan_record(
    campaign: Campaign,
    *,
    repository: Path,
    resolved_revisions: Sequence[ResolvedRevision],
    source_config: Path,
    append_samples: bool,
    tool_versions: dict[str, str | None],
) -> tuple[Path, str]:
    """Retain one immutable effective campaign plan and return its digest."""

    plan = campaign.plan(
        repository=repository,
        resolved_revisions=resolved_revisions,
        append_samples=append_samples,
        source_config=source_config,
        tool_versions=tool_versions,
    )
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    path = (
        repository.resolve() / ".asv" / "feregion-plans" / campaign.campaign_id / f"{digest}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "plan_sha256": digest, "plan": plan}
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != encoded:
        raise RuntimeError(f"content-addressed campaign plan changed unexpectedly: {path}")
    path.write_text(encoded, encoding="utf-8")
    return path, digest


def _observed_runner_versions(
    repository: Path,
    commit: str,
    *,
    environments: Sequence[str],
) -> tuple[str, ...]:
    """Return runner versions observed for the campaign's expected environments."""

    root = repository.resolve() / ".asv" / "feregion-environments" / commit
    expected = set(environments)
    versions: set[str] = set()
    if not root.is_dir():
        return ()
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("environment") not in expected:
            continue
        value = payload.get("asv_runner_version")
        if value is not None:
            versions.add(str(value))
    return tuple(sorted(versions))


def _write_run_record(
    campaign: Campaign,
    revision: ResolvedRevision,
    *,
    repository: Path,
    returncode: int,
    append_samples: bool,
    plan_path: Path,
    plan_sha256: str,
    tool_versions: dict[str, str | None],
) -> Path:
    """Retain one revision-run outcome for failures that precede benchmark JSON."""

    path = (
        repository.resolve()
        / ".asv"
        / "feregion-runs"
        / campaign.campaign_id
        / f"{revision.commit}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    observed_runner_versions = _observed_runner_versions(
        repository,
        revision.commit,
        environments=expected_environment_names(campaign.environment_profile),
    )
    observed_runner = observed_runner_versions[0] if len(observed_runner_versions) == 1 else None
    payload = {
        "schema_version": 2,
        "campaign_id": campaign.campaign_id,
        "requested_revision": revision.requested,
        "commit": revision.commit,
        "returncode": returncode,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "cases": list(campaign.cases),
        "load_sizes": list(campaign.load_sizes),
        "environment_profile": campaign.environment_profile,
        "repetitions": campaign.repetitions,
        "rounds": campaign.rounds,
        "record_samples": campaign.record_samples,
        "append_samples": append_samples,
        "machine_policy": campaign.machine_policy,
        "report_steps": list(campaign.report_steps),
        "plan_path": plan_path.relative_to(repository.resolve()).as_posix(),
        "plan_sha256": plan_sha256,
        "asv_version": tool_versions.get("asv_version"),
        "asv_runner_version": observed_runner or tool_versions.get("asv_runner_version"),
        "operator_asv_runner_version": tool_versions.get("asv_runner_version"),
        "observed_asv_runner_versions": list(observed_runner_versions),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def check_release_campaign(
    campaign: Campaign,
    *,
    resolved_revisions: Sequence[ResolvedRevision],
    repository: Path,
    machine: str | None = None,
    output: Path | None = None,
) -> tuple[RegressionDecision, Path]:
    """Evaluate one two-revision release campaign from retained ASV evidence.

    This function performs no timing work. It normalizes already-retained ASV
    result JSON and applies the project-owned release decision.
    """

    if len(resolved_revisions) != 2:
        raise ValueError("check requires exactly two campaign revisions")
    if campaign.environment_profile != "release-history":
        raise ValueError("check requires the fixed release-history environment profile")
    if "lookup_geographic_numbers" not in campaign.cases:
        raise ValueError("check requires the lookup_geographic_numbers benchmark case")

    repository = repository.resolve()
    records = collect_asv_evidence(
        repository / ".asv" / "results",
        campaign_id=campaign.campaign_id,
        revisions=resolved_revisions,
        cases=campaign.cases,
        load_sizes=campaign.load_sizes,
        machine=machine,
        environments=expected_environment_names(campaign.environment_profile),
    )
    evidence_path = output or (
        repository / "dist" / "benchmarks" / f"{campaign.campaign_id}-evidence.json"
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    write_evidence(evidence_path, records)
    baseline = [record for record in records if record.revision == resolved_revisions[0].commit]
    candidate = [record for record in records if record.revision == resolved_revisions[1].commit]
    required_loads = tuple(size for size in campaign.load_sizes if size >= 10_000)
    decision = compare_release_evidence(
        baseline,
        candidate,
        required_loads=required_loads,
    )
    return decision, evidence_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_campaign_arguments(item: argparse.ArgumentParser) -> None:
        item.add_argument("config", type=Path)
        item.add_argument(
            "--baseline",
            help=(
                "explicit accepted prior candidate for a campaign whose source uses "
                f"{EXPLICIT_BASELINE_MARKER!r}"
            ),
        )

    for name in ("plan", "compare", "report"):
        add_campaign_arguments(subparsers.add_parser(name))
    run = subparsers.add_parser("run")
    add_campaign_arguments(run)
    run.add_argument("--repetitions", type=int)
    run.add_argument("--rounds", type=int)
    run.add_argument(
        "--append-samples",
        action="store_true",
        help="append raw samples to compatible retained ASV results",
    )
    check = subparsers.add_parser("check")
    add_campaign_arguments(check)
    check.add_argument("--machine")
    check.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the campaign operator CLI."""

    args = _parser().parse_args(argv)
    campaign = Campaign.from_toml(args.config)
    try:
        campaign = campaign.with_explicit_baseline(args.baseline)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.command == "run":
        repetitions = args.repetitions if args.repetitions is not None else campaign.repetitions
        rounds = args.rounds if args.rounds is not None else campaign.rounds
        if repetitions < 1 or rounds < 1:
            raise SystemExit("run overrides must be positive integers")
        campaign = replace(campaign, repetitions=repetitions, rounds=rounds)
    repository = Path(__file__).resolve().parents[1]
    try:
        resolved_revisions = resolve_revisions(campaign, repository=repository)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.command == "plan":
        print(
            json.dumps(
                campaign.plan(repository=repository, resolved_revisions=resolved_revisions),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "run":
        if args.append_samples and not campaign.record_samples:
            raise SystemExit("--append-samples requires record_samples=true")
        tool_versions = benchmark_tool_versions()
        plan_path, plan_sha256 = _write_plan_record(
            campaign,
            repository=repository,
            resolved_revisions=resolved_revisions,
            source_config=args.config,
            append_samples=args.append_samples,
            tool_versions=tool_versions,
        )
        for revision in resolved_revisions:
            command: list[str] = [
                "run",
                revision.asv_run_selector,
                "--bench",
                benchmark_regex(campaign),
            ]
            command.extend(["--attribute", f"repeat={campaign.repetitions}"])
            command.extend(["--attribute", f"rounds={campaign.rounds}"])
            if campaign.record_samples:
                command.append("--record-samples")
            if args.append_samples:
                command.append("--append-samples")
            status = _run_asv(
                campaign,
                command,
                repository=repository,
                resolved_revisions=resolved_revisions,
            )
            _write_run_record(
                campaign,
                revision,
                repository=repository,
                returncode=status,
                append_samples=args.append_samples,
                plan_path=plan_path,
                plan_sha256=plan_sha256,
                tool_versions=tool_versions,
            )
            if status != 0:
                return status
        return 0
    if args.command == "compare":
        if len(resolved_revisions) != 2:
            raise SystemExit("compare requires exactly two campaign revisions")
        return _run_asv(
            campaign,
            ["compare", resolved_revisions[0].commit, resolved_revisions[1].commit],
            repository=repository,
            resolved_revisions=resolved_revisions,
        )
    if args.command == "check":
        try:
            decision, evidence_path = check_release_campaign(
                campaign,
                resolved_revisions=resolved_revisions,
                repository=repository,
                machine=args.machine,
                output=args.output,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        payload = {
            "baseline": asdict(resolved_revisions[0]),
            "candidate": asdict(resolved_revisions[1]),
            "complete": decision.complete,
            "triggered": decision.triggered,
            "reason": decision.reason,
            "comparisons": [asdict(item) for item in decision.comparisons],
            "evidence": str(evidence_path),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        if not decision.complete:
            return 2
        return 1 if decision.triggered else 0
    return _run_asv(
        campaign,
        ["publish"],
        repository=repository,
        resolved_revisions=resolved_revisions,
    )


if __name__ == "__main__":
    sys.exit(main())
