"""Tests for the project-owned ASV benchmark contract and thin campaign layer."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

import benchmarks.campaign as campaign_module
import benchmarks.release_workflow as release_workflow
from benchmarks.asv_suite.contracts import CASES, STANDARD_LOAD_SIZES, workload_fingerprint
from benchmarks.campaign import (
    ASV_BUILD_COMMAND,
    ASV_INSTALL_COMMAND,
    PROFILE_CONFIG,
    Campaign,
    benchmark_regex,
    build_asv_config,
    check_release_campaign,
    resolve_revision,
)
from benchmarks.evidence import EvidenceRecord, normalize_asv_result
from benchmarks.regression import compare_release_evidence
from benchmarks.reporting import build_publisher_payload, install_report_extension


def test_case_versions_have_stable_sha256_identity() -> None:
    """Semantic case identity must map to ASV without using source-code hashes."""

    digest = CASES["lookup_geographic_numbers"].semantic_version_hash
    assert len(digest) == 64
    assert digest == CASES["lookup_geographic_numbers"].semantic_version_hash


def test_workload_fingerprint_changes_with_load_size() -> None:
    """Different canonical workload specifications must have different identities."""

    assert workload_fingerprint(size=100) != workload_fingerprint(size=1_000)


def test_initial_environment_profiles_are_sparse_and_named() -> None:
    """The accepted sparse matrix must not become an uncontrolled Cartesian sweep."""

    assert set(PROFILE_CONFIG) == {
        "release-history",
        "python-supported",
        "numpy-sensitivity",
        "pandas-sensitivity",
        "dependency-matrix",
        "reference-comparison",
    }
    assert PROFILE_CONFIG["release-history"]["pythons"] == ["3.12"]
    assert PROFILE_CONFIG["numpy-sensitivity"]["matrix"]["req"]["numpy"] == [
        "1.26.4",
        "2.0.2",
        "2.2.6",
        "2.5.2",
    ]


def test_campaign_parses_and_resolves_plan(tmp_path: Path) -> None:
    """Operator TOML must resolve to explicit revisions, cases, loads, and timing controls."""

    path = tmp_path / "campaign.toml"
    path.write_text(
        "[campaign]\n"
        "id = 'slice'\n"
        "revisions = ['v0.3.0b1', 'v0.2.0b1']\n"
        "cases = ['lookup_geographic_numbers']\n"
        "load_sizes = [10000, 100000]\n"
        "repetitions = 7\n"
        "rounds = 4\n"
        "environment_profile = 'release-history'\n"
        "record_samples = true\n",
        encoding="utf-8",
    )
    campaign = Campaign.from_toml(path)
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    (repository / "tracked").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "tracked"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v0.3.0b1"], cwd=repository, check=True)
    subprocess.run(["git", "tag", "v0.2.0b1"], cwd=repository, check=True)
    plan = campaign.plan(repository=repository)
    assert plan["repetitions"] == 7
    assert plan["case_versions"] == {"lookup_geographic_numbers": 1}
    assert [item["requested"] for item in plan["resolved_revisions"]] == [
        "v0.3.0b1",
        "v0.2.0b1",
    ]
    assert all(len(item["commit"]) == 40 for item in plan["resolved_revisions"])


def test_campaign_rejects_unknown_case(tmp_path: Path) -> None:
    """A typo must fail planning instead of silently reducing benchmark coverage."""

    path = tmp_path / "campaign.toml"
    path.write_text("[campaign]\nid='x'\nrevisions=['HEAD']\ncases=['missing']\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown benchmark cases"):
        Campaign.from_toml(path)


def test_campaign_rejects_empty_case_or_load_selection(tmp_path: Path) -> None:
    """Empty selectors must fail instead of turning into broad ASV regex matches."""

    cases_path = tmp_path / "empty-cases.toml"
    cases_path.write_text(
        "[campaign]\nid='x'\nrevisions=['HEAD']\ncases=[]\nload_sizes=[100]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="at least one benchmark case"):
        Campaign.from_toml(cases_path)

    loads_path = tmp_path / "empty-loads.toml"
    loads_path.write_text(
        "[campaign]\n"
        "id='x'\n"
        "revisions=['HEAD']\n"
        "cases=['lookup_geographic_numbers']\n"
        "load_sizes=[]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="at least one load size"):
        Campaign.from_toml(loads_path)


def test_asv_config_uses_uv_and_project_owned_benchmark_dir() -> None:
    """The campaign layer must delegate generic environment execution to ASV."""

    campaign = Campaign(
        "slice",
        "test",
        ("HEAD",),
        ("lookup_geographic_numbers",),
        STANDARD_LOAD_SIZES,
        5,
        3,
        "release-history",
        True,
    )
    config = build_asv_config(campaign, repository=Path("."))
    assert config["environment_type"] == "uv"
    assert config["benchmark_dir"] == "benchmarks/asv_suite"
    assert config["build_command"] == ASV_BUILD_COMMAND
    assert config["install_command"] == ASV_INSTALL_COMMAND
    assert "--no-deps" in config["build_command"][0]
    assert "--no-deps" in config["install_command"][0]


def test_persistent_asv_config_matches_project_build_install_contract() -> None:
    """Direct ASV use must preserve the same project-only wheel ownership boundary."""

    project_root = Path(__file__).resolve().parents[1]
    config = json.loads((project_root / "asv.conf.json").read_text(encoding="utf-8"))
    assert config["build_command"] == ASV_BUILD_COMMAND
    assert config["install_command"] == ASV_INSTALL_COMMAND


def test_benchmark_regex_selects_only_requested_load_values() -> None:
    """A partial load selection must not overmatch larger decimal prefixes."""

    campaign = Campaign(
        "slice",
        "test",
        ("HEAD",),
        ("lookup_geographic_numbers",),
        (100, 10_000),
        5,
        3,
        "release-history",
        True,
    )
    regex = re.compile(benchmark_regex(campaign))
    assert regex.search("benchmarks.Time.time_lookup_geographic_numbers(100)")
    assert regex.search("benchmarks.Time.time_lookup_geographic_numbers(10000)")
    assert not regex.search("benchmarks.Time.time_lookup_geographic_numbers(1000)")
    assert not regex.search("benchmarks.Time.time_lookup_geographic_numbers(100000)")
    assert not regex.search("benchmarks.Time.time_lookup_geographic_numbers(1000000)")


def test_benchmark_regex_keeps_scalar_cases_when_loads_are_filtered() -> None:
    """Load-size selection must not discard selected scalar benchmark cases."""

    campaign = Campaign(
        "slice",
        "test",
        ("HEAD",),
        ("lookup_geographic_number", "lookup_geographic_numbers"),
        (100,),
        5,
        3,
        "release-history",
        True,
    )
    regex = re.compile(benchmark_regex(campaign))
    assert regex.search("benchmarks.Time.time_lookup_geographic_number")
    assert regex.search("benchmarks.Time.time_lookup_geographic_numbers(100)")
    assert not regex.search("benchmarks.Time.time_lookup_geographic_numbers(1000)")


def test_run_asv_uses_supported_cli_order_and_repository_rooted_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The external ASV boundary must preserve its CLI and relative-path contracts."""

    repository = tmp_path / "repo"
    (repository / "benchmarks" / "asv_suite").mkdir(parents=True)
    campaign = Campaign(
        "slice",
        "test",
        ("HEAD",),
        ("lookup_geographic_numbers",),
        (100,),
        2,
        1,
        "release-history",
        True,
    )
    observed_config: Path | None = None

    def fake_run(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        nonlocal observed_config
        assert argv[:2] == ["asv", "run"]
        assert "-c" not in argv
        config_index = argv.index("--config")
        assert config_index > 1
        observed_config = Path(argv[config_index + 1])
        assert observed_config.parent == repository.resolve()
        assert cwd == repository.resolve()
        config = json.loads(observed_config.read_text(encoding="utf-8"))
        assert config["benchmark_dir"] == "benchmarks/asv_suite"
        assert (observed_config.parent / config["benchmark_dir"]).is_dir()
        assert observed_config.parent / config["results_dir"] == repository / ".asv/results"
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(campaign_module.subprocess, "run", fake_run)
    status = campaign_module._run_asv(campaign, ["run", "HEAD"], repository=repository)

    assert status == 0
    assert observed_config is not None
    assert not observed_config.exists()


def test_run_asv_crosses_real_subprocess_boundary_with_supported_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stub ASV executable verifies argv and config semantics across subprocess."""

    repository = tmp_path / "repo"
    (repository / "benchmarks" / "asv_suite").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sentinel = tmp_path / "observed-config.txt"
    executable = bin_dir / "asv"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "if not args or args[0] != 'run' or '-c' in args:\n"
        "    raise SystemExit(41)\n"
        "try:\n"
        "    index = args.index('--config')\n"
        "except ValueError:\n"
        "    raise SystemExit(42) from None\n"
        "config_path = Path(args[index + 1]).resolve()\n"
        "if config_path.parent != Path.cwd().resolve():\n"
        "    raise SystemExit(43)\n"
        "config = json.loads(config_path.read_text(encoding='utf-8'))\n"
        "if config['benchmark_dir'] != 'benchmarks/asv_suite':\n"
        "    raise SystemExit(44)\n"
        "if not (config_path.parent / config['benchmark_dir']).is_dir():\n"
        "    raise SystemExit(45)\n"
        "Path(os.environ['ASV_STUB_SENTINEL']).write_text(str(config_path), encoding='utf-8')\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    monkeypatch.setenv("ASV_STUB_SENTINEL", str(sentinel))
    campaign = Campaign(
        "slice",
        "test",
        ("HEAD",),
        ("lookup_geographic_numbers",),
        (100,),
        2,
        1,
        "release-history",
        True,
    )

    status = campaign_module._run_asv(campaign, ["run", "HEAD"], repository=repository)

    assert status == 0
    config_path = Path(sentinel.read_text(encoding="utf-8"))
    assert not config_path.exists()


def test_supported_asv_parser_accepts_generated_argument_order_when_installed() -> None:
    """Use ASV's own parser as the oracle when the benchmark dependency is installed."""

    pytest.importorskip("asv")
    from asv import commands

    parser, _ = commands.make_argparser()
    args = parser.parse_args(["run", "HEAD", "--config", "asv.conf.json"])
    assert args.config == "asv.conf.json"


def test_asv_suite_isolated_from_legacy_pytest_benchmark_module() -> None:
    """ASV discovery must not import the retained predecessor pytest benchmark module."""

    project_root = Path(__file__).resolve().parents[1]
    suite = project_root / "benchmarks" / "asv_suite"
    assert suite.is_dir()
    assert (suite / "benchmarks.py").is_file()
    assert not (suite / "test_lookup_benchmark.py").exists()


def _init_revision_repo(path: Path) -> tuple[str, str]:
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    tracked = path / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "one"], cwd=path, check=True)
    first = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    tracked.write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "two"], cwd=path, check=True)
    subprocess.run(["git", "tag", "v-test"], cwd=path, check=True)
    second = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    return first, second


def test_revision_identity_resolves_to_one_commit_and_exact_asv_selector(tmp_path: Path) -> None:
    """A release tag must become one immutable commit, never an ASV history walk."""

    repository = tmp_path / "repo"
    _first, second = _init_revision_repo(repository)
    resolved = resolve_revision("v-test", repository=repository)
    assert resolved.commit == second
    history = subprocess.check_output(
        ["git", "rev-list", "--first-parent", resolved.asv_run_selector, "--"],
        cwd=repository,
        text=True,
    ).splitlines()
    assert history == [second]
    unbounded = subprocess.check_output(
        ["git", "rev-list", "--first-parent", "v-test", "--"],
        cwd=repository,
        text=True,
    ).splitlines()
    assert len(unbounded) == 2


@pytest.mark.parametrize("revision", ["HEAD^!", "main..HEAD", "HEAD~1", "HEAD^{commit}"])
def test_campaign_rejects_git_range_or_expression_syntax(revision: str, tmp_path: Path) -> None:
    """Campaign revisions are identities; ASV/Git execution syntax is internal."""

    repository = tmp_path / "repo"
    _init_revision_repo(repository)
    with pytest.raises(ValueError, match="one ref/commit identity"):
        resolve_revision(revision, repository=repository)


def test_missing_campaign_revision_fails_during_preflight(tmp_path: Path) -> None:
    """A nonexistent ref must fail before ASV environment or build work starts."""

    repository = tmp_path / "repo"
    _init_revision_repo(repository)
    with pytest.raises(ValueError, match="cannot resolve campaign revision"):
        resolve_revision("v-missing", repository=repository)


def test_exact_selector_and_build_contract_cross_subprocess_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exact revision selection and single-wheel build policy cross the ASV subprocess boundary."""

    repository = tmp_path / "repo"
    _first, second = _init_revision_repo(repository)
    (repository / "benchmarks" / "asv_suite").mkdir(parents=True)
    campaign = Campaign(
        "slice",
        "test",
        ("v-test",),
        ("lookup_geographic_numbers",),
        (100,),
        2,
        1,
        "release-history",
        True,
    )
    resolved = (campaign_module.ResolvedRevision("v-test", second),)
    observed: list[list[str]] = []

    def fake_run(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        observed.append(argv)
        assert argv[1:3] == ["run", f"{second}^!"]
        config_path = Path(argv[argv.index("--config") + 1])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert config["branches"] == [second]
        assert config["build_command"] == ASV_BUILD_COMMAND
        assert config["install_command"] == ASV_INSTALL_COMMAND
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(campaign_module.subprocess, "run", fake_run)
    status = campaign_module._run_asv(
        campaign,
        ["run", resolved[0].asv_run_selector],
        repository=repository,
        resolved_revisions=resolved,
    )
    assert status == 0
    assert observed


def test_asv_fixture_normalizes_raw_samples() -> None:
    """Version-specific ASV storage parsing must terminate at the evidence adapter."""

    record = normalize_asv_result(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision="abc",
        campaign_id="slice",
        result={"result": [0.2, 0.4], "samples": [[0.19, 0.21], [0.39, 0.41]]},
        parameter_index=1,
        load_size=100_000,
        machine="host",
        environment="py3.12-np1.26.4",
        asv_version="0.6.6",
    )
    assert record.result_state == "measured"
    assert record.samples == (0.39, 0.41)
    assert record.statistic_seconds == 0.4


def test_asv_null_and_nan_results_remain_distinct_states() -> None:
    """ASV failure and explicit skip must not collapse into one applicability state."""

    failed = normalize_asv_result(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision="abc",
        campaign_id="slice",
        result={"result": [None], "samples": [None]},
        load_size=10_000,
    )
    skipped = normalize_asv_result(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision="abc",
        campaign_id="slice",
        result={"result": [float("nan")], "samples": [None]},
        load_size=10_000,
    )
    assert failed.result_state == "execution_failed"
    assert skipped.result_state == "not_applicable"


def _record(load: int, seconds: float, revision: str) -> EvidenceRecord:
    operations = load
    return EvidenceRecord(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision=revision,
        load_size=load,
        result_state="measured",
        correctness_state="passed",
        samples=(seconds,),
        statistic_seconds=seconds,
        operation_count_unit="points",
        operations=operations,
        operations_per_second=operations / seconds,
        stored_benchmark_version=CASES["lookup_geographic_numbers"].semantic_version_hash,
        machine="host",
        environment="env",
        campaign_id="release",
    )


def test_release_gate_triggers_only_on_two_adjacent_slow_loads() -> None:
    """The 25% two-adjacent-load rule remains project-owned and deterministic."""

    baseline = [
        _record(10_000, 1.0, "base"),
        _record(20_000, 2.0, "base"),
        _record(50_000, 5.0, "base"),
    ]
    candidate = [
        _record(10_000, 1.4, "cand"),
        _record(20_000, 2.8, "cand"),
        _record(50_000, 5.5, "cand"),
    ]
    decision = compare_release_evidence(baseline, candidate)
    assert decision.complete is True
    assert decision.triggered is True


def test_standard_load_grid_uses_one_two_five_decades_through_fifty_million() -> None:
    """The maintained load contract must cover the requested 1-2-5 grid through 5e7."""

    assert STANDARD_LOAD_SIZES == (
        1,
        2,
        5,
        10,
        20,
        50,
        100,
        200,
        500,
        1_000,
        2_000,
        5_000,
        10_000,
        20_000,
        50_000,
        100_000,
        200_000,
        500_000,
        1_000_000,
        2_000_000,
        5_000_000,
        10_000_000,
        20_000_000,
        50_000_000,
    )


def test_dependency_matrix_profile_is_sparse_union_not_cartesian() -> None:
    """The broad dependency campaign must remain a bounded union of sensitivity sweeps."""

    profile = PROFILE_CONFIG["dependency-matrix"]
    assert profile["matrix"] == {"req": {"numpy": ["1.26.4"], "pandas": ["2.1.4"]}}
    assert len(profile["include"]) == 6
    config = build_asv_config(
        Campaign(
            "deps",
            "test",
            ("HEAD",),
            ("lookup_geographic_numbers",),
            (10_000,),
            2,
            1,
            "dependency-matrix",
            True,
        ),
        repository=Path("."),
    )
    assert config["include"] == profile["include"]


def test_predefined_campaigns_cover_operator_workflows() -> None:
    """Canonical campaign files must cover smoke, history, release, matrix, and full-HEAD work."""

    project_root = Path(__file__).resolve().parents[1]
    campaigns = project_root / "benchmarks" / "campaigns"
    expected = {
        "smoke.toml",
        "head-full.toml",
        "release-compare.toml",
        "release-history.toml",
        "numpy-sensitivity.toml",
        "pandas-sensitivity.toml",
        "python-supported.toml",
        "dependency-matrix.toml",
        "reference-comparison.toml",
        "diagnostics.toml",
    }
    available = {path.name for path in campaigns.glob("*.toml")}
    assert expected <= available
    parsed = {name: Campaign.from_toml(campaigns / name) for name in expected}
    head_full = parsed["head-full.toml"]
    assert head_full.load_sizes == STANDARD_LOAD_SIZES
    expected_head_cases = {case_id for case_id, case in CASES.items() if not case.diagnostic}
    assert set(head_full.cases) == expected_head_cases
    release_compare = parsed["release-compare.toml"]
    assert release_compare.revisions == ("v0.4.0a9", "HEAD")
    assert max(release_compare.load_sizes) == 1_000_000
    dependency_matrix = parsed["dependency-matrix.toml"]
    assert {"pandas_lookup_numbers", "pandas_lookup_numbers_and_names"} <= set(
        dependency_matrix.cases
    )


def _write_asv_result(
    path: Path,
    *,
    commit: str,
    values: list[float],
    samples: list[list[float]],
    loads: list[int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "commit_hash": commit,
        "env_name": "uv-py3.12-numpy1.26.4-pandas2.1.4",
        "result_columns": ["result", "params", "version", "samples"],
        "results": {
            "benchmarks.TimeGeographicLookupNumbers.time_lookup_geographic_numbers": [
                values,
                [[str(load) for load in loads]],
                CASES["lookup_geographic_numbers"].semantic_version_hash,
                samples,
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    state_root = path.parent.parent.parent / "feregion-state" / commit / payload["env_name"]
    for load in loads:
        marker = state_root / "lookup_geographic_numbers" / f"{load}.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "case_id": "lookup_geographic_numbers",
                    "load_size": load,
                    "state": "correctness_passed",
                    "reason": None,
                    "commit": commit,
                    "environment": payload["env_name"],
                }
            ),
            encoding="utf-8",
        )


def test_collect_asv_evidence_reads_retained_results_without_rerunning(tmp_path: Path) -> None:
    """Project evidence must be reconstructable from documented ASV v2 result JSON."""

    from benchmarks.evidence import collect_asv_evidence

    base = "a" * 40
    cand = "b" * 40
    results = tmp_path / ".asv" / "results"
    _write_asv_result(
        results / "host" / "base.json",
        commit=base,
        values=[1.0, 2.0],
        samples=[[0.9, 1.1], [1.9, 2.1]],
        loads=[10_000, 20_000],
    )
    _write_asv_result(
        results / "host" / "cand.json",
        commit=cand,
        values=[1.3, 2.6],
        samples=[[1.2, 1.4], [2.5, 2.7]],
        loads=[10_000, 20_000],
    )
    revisions = (
        campaign_module.ResolvedRevision("base", base),
        campaign_module.ResolvedRevision("cand", cand),
    )
    records = collect_asv_evidence(
        results,
        campaign_id="release",
        revisions=revisions,
        cases=("lookup_geographic_numbers",),
        load_sizes=(10_000, 20_000),
    )
    assert len(records) == 4
    assert {record.revision for record in records} == {base, cand}
    assert {record.load_size for record in records} == {10_000, 20_000}
    assert all(record.machine == "host" for record in records)


def test_check_release_campaign_consumes_retained_results_and_writes_evidence(
    tmp_path: Path,
) -> None:
    """The operator gate must consume retained ASV evidence without invoking timing."""

    base = "a" * 40
    cand = "b" * 40
    results = tmp_path / ".asv" / "results"
    loads = [10_000, 20_000, 50_000]
    _write_asv_result(
        results / "host" / "base.json",
        commit=base,
        values=[1.0, 2.0, 5.0],
        samples=[[1.0], [2.0], [5.0]],
        loads=loads,
    )
    _write_asv_result(
        results / "host" / "cand.json",
        commit=cand,
        values=[1.40, 2.80, 5.10],
        samples=[[1.40], [2.80], [5.10]],
        loads=loads,
    )
    campaign = Campaign(
        "release",
        "test",
        ("base", "cand"),
        ("lookup_geographic_numbers",),
        tuple(loads),
        2,
        1,
        "release-history",
        True,
    )
    resolved = (
        campaign_module.ResolvedRevision("base", base),
        campaign_module.ResolvedRevision("cand", cand),
    )
    decision, evidence_path = check_release_campaign(
        campaign,
        resolved_revisions=resolved,
        repository=tmp_path,
    )
    assert decision.complete is True
    assert decision.triggered is True
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert len(payload["records"]) == 6


def test_release_gate_requires_maintained_adjacent_loads_and_complete_required_set() -> None:
    """Missing 1-2-5 neighbors must not be mistaken for adjacent regression evidence."""

    baseline = [_record(10_000, 1.0, "base"), _record(50_000, 5.0, "base")]
    candidate = [_record(10_000, 1.4, "cand"), _record(50_000, 7.0, "cand")]
    decision = compare_release_evidence(baseline, candidate)
    assert decision.complete is True
    assert decision.triggered is False

    incomplete = compare_release_evidence(
        baseline,
        candidate,
        required_loads=(10_000, 20_000, 50_000),
    )
    assert incomplete.complete is False
    assert "20000" in (incomplete.reason or "")


def test_benchmark_operator_runbook_covers_rerun_and_publication_workflow() -> None:
    """Maintained guidance must keep refresh/report/preview/publish responsibilities visible."""

    project_root = Path(__file__).resolve().parents[1]
    text = (project_root / "docs" / "benchmark-operations.md").read_text(encoding="utf-8")
    assert "python -m benchmarks.release_workflow refresh" in text
    assert "--history --repetitions 15 --rounds 7 --append-samples" in text
    assert "python -m benchmarks.campaign check" in text
    assert "python -m benchmarks.release_workflow report" in text
    assert "python -m benchmarks.release_workflow preview" in text
    assert "python -m benchmarks.release_workflow publish --push" in text
    assert "feregion summary" in text
    assert ".asv/results" in text


def test_benchmark_supporting_documents_cover_evidence_choice_and_roadmap() -> None:
    """Retain the evidence summary, user choice guide, and future-work boundary.

    These documents preserve the final-alpha benchmark evidence and planned-work context.
    """

    project_root = Path(__file__).resolve().parents[1]
    results = (project_root / "docs" / "benchmark-results.md").read_text(encoding="utf-8")
    choice = (project_root / "docs" / "obspy-or-feregion.md").read_text(encoding="utf-8")
    roadmap = (project_root / "docs" / "benchmark-roadmap.md").read_text(encoding="utf-8")
    assert "Python-version sensitivity" in results
    assert "NumPy-version sensitivity" in results
    assert "pandas-version sensitivity" in results
    assert "Performance across feregion releases" in results
    assert "direct ObsPy" in choice
    assert "predecessor" in choice
    assert "planned or investigatory work" in roadmap


def test_asv_config_loads_feregion_output_publisher_plugin() -> None:
    """Persistent and generated ASV configs must load the local publisher plugin."""

    persistent = json.loads((Path(__file__).resolve().parents[1] / "asv.conf.json").read_text())
    assert persistent["plugins"] == [".benchmarks.asv_plugin"]
    campaign = Campaign(
        "report",
        "test",
        ("HEAD",),
        ("lookup_geographic_numbers",),
        (10_000,),
        2,
        1,
        "release-history",
        True,
    )
    generated = build_asv_config(campaign, repository=Path("."))
    assert generated["plugins"] == [".benchmarks.asv_plugin"]


def test_benchmark_bindings_expose_human_readable_asv_metadata() -> None:
    """Every ASV timing class must provide a useful display name and source explanation."""

    from benchmarks.asv_suite import benchmarks as asv_benchmarks

    classes = [
        value
        for name, value in vars(asv_benchmarks).items()
        if name.startswith("Time") and isinstance(value, type)
    ]
    assert len(classes) == len(CASES)
    for cls in classes:
        assert getattr(cls, "pretty_name", "")
        assert getattr(cls, "pretty_source", "")


def test_asv_samples_with_missing_first_parameter_select_later_sample_list() -> None:
    """A null first parameter must not make the ASV sample param-list look scalar."""

    record = normalize_asv_result(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision="abc",
        campaign_id="slice",
        result={"result": [None, 0.4], "samples": [None, [0.39, 0.41]]},
        parameter_index=1,
        load_size=20_000,
    )
    assert record.samples == (0.39, 0.41)
    assert record.statistic_seconds == 0.4


def test_report_extension_adds_page_without_replacing_asv_assets(tmp_path: Path) -> None:
    """The project page must be additive and idempotent over a stock-like ASV index."""

    html = tmp_path / "html"
    html.mkdir()
    (html / "index.html").write_text(
        "<html><head>  </head><body><ul>\n"
        '\t<li id="nav-li-regressions"><a href="#/regressions">Regressions</a></li>\n'
        '</ul>    <div id="regressions-display"></div></body></html>',
        encoding="utf-8",
    )
    install_report_extension(html)
    install_report_extension(html)
    text = (html / "index.html").read_text(encoding="utf-8")
    assert text.count("feregion-report-extension") == 1
    assert "nav-li-feregion" in text
    assert "feregion-display" in text
    assert (html / "feregion-report.js").is_file()
    assert (html / "feregion-report.css").is_file()


def test_publisher_payload_links_parameterized_cases_to_scaling_view(tmp_path: Path) -> None:
    """The summary payload must expose curated load-size links and ASV signal counts."""

    (tmp_path / "regressions.json").write_text(
        json.dumps({"regressions": [["a"], ["b"]]}), encoding="utf-8"
    )

    class Graphs:
        def get_params(self):
            return {"machine": {"host"}, "python": {"3.12", "3.14"}}

    class Repo:
        def get_tags(self):
            return {"v1": "a" * 40}

    payload = build_publisher_payload(
        html_dir=tmp_path,
        benchmarks={
            "bench.time_batch": {
                "pretty_name": "Batch",
                "pretty_source": "Map coordinates to geographic numbers.",
                "code": "time batch",
                "params": [["100", "1000"]],
                "param_names": ["size"],
            }
        },
        graphs=Graphs(),
        revisions={"a" * 40: 1},
        repo=Repo(),
    )
    assert payload["regression_count"] == 2
    assert payload["benchmarks"][0]["scaling_href"].endswith("x-axis=size&y-axis-scale=log")
    assert payload["benchmarks"][0]["pretty_source"] == "Map coordinates to geographic numbers."
    assert payload["revisions"][0]["tags"] == ["v1"]


def test_release_workflow_refresh_uses_maintained_population_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release refresh must cover current/full/matrix/history roles through maintained campaigns."""

    commands: list[list[str]] = []

    def fake_run(command):
        commands.append(list(command))
        return 0

    monkeypatch.setattr(release_workflow, "_run", fake_run)
    status = release_workflow.refresh(
        repetitions=15,
        rounds=7,
        append_samples=True,
        include_history=True,
    )
    assert status == 0
    rendered = [" ".join(command) for command in commands]
    assert any(
        "head-full.toml --repetitions 15 --rounds 7 --append-samples" in item for item in rendered
    )
    assert any("dependency-matrix.toml" in item for item in rendered)
    assert any("python-supported.toml" in item for item in rendered)
    assert any("reference-comparison.toml" in item for item in rendered)
    assert any("diagnostics.toml" in item for item in rendered)
    assert any("release-history.toml" in item for item in rendered)
    assert not any("numpy-sensitivity.toml" in item for item in rendered)
    assert not any("pandas-sensitivity.toml" in item for item in rendered)
    assert rendered[-1] == "asv publish --no-pull --config asv.conf.json"


def test_source_manifest_includes_report_assets() -> None:
    """The source delivery must retain the JS/CSS needed by the local ASV publisher."""

    project_root = Path(__file__).resolve().parents[1]
    manifest = (project_root / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include benchmarks *.py *.md *.toml *.js *.css" in manifest


def test_release_workflow_rebuilds_report_when_project_gate_triggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A regression signal must not prevent report generation needed to investigate it."""

    commands: list[list[str]] = []

    def fake_run(command):
        rendered = list(command)
        commands.append(rendered)
        if "benchmarks.campaign" in rendered and "check" in rendered:
            return 1
        return 0

    monkeypatch.setattr(release_workflow, "_run", fake_run)
    status = release_workflow.refresh(
        repetitions=None,
        rounds=None,
        append_samples=False,
        include_history=False,
    )
    assert status == 1
    assert commands[-1] == ["asv", "publish", "--no-pull", "--config", "asv.conf.json"]


def test_release_workflow_publication_requires_explicit_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper must keep local publication staging separate from an external push."""

    commands: list[list[str]] = []
    monkeypatch.setattr(
        release_workflow, "_run", lambda command: commands.append(list(command)) or 0
    )
    assert release_workflow.stage_publication(push=False) == 0
    assert "--no-push" in commands[-1]
    assert release_workflow.stage_publication(push=True) == 0
    assert "--no-push" not in commands[-1]


def test_semantic_oracle_rejects_wrong_in_range_geographic_numbers() -> None:
    """A valid-shape/range but wrong identity must fail untimed benchmark correctness."""

    import numpy as np

    from benchmarks.asv_suite.workloads import assert_geographic_numbers_match_source

    class Reference:
        def number(self, longitude: float, latitude: float) -> int:
            return 2

    coordinate_values = np.asarray([[12.0, 34.0], [-45.0, 20.0]])
    wrong = np.ones(2, dtype=np.uint16)
    with pytest.raises(AssertionError):
        assert_geographic_numbers_match_source(
            wrong,
            coordinate_values,
            reference=Reference(),
        )


def test_nested_asv_sample_groups_flatten_only_after_parameter_selection() -> None:
    """Round/repeat sample groups may nest without mixing neighboring load parameters."""

    record = normalize_asv_result(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision="abc",
        campaign_id="slice",
        result={
            "result": [0.2, 0.4],
            "samples": [[[0.19], [0.21]], [[0.39], [0.41]]],
        },
        parameter_index=1,
        load_size=20_000,
    )
    assert record.samples == (0.39, 0.41)


def test_stored_asv_version_must_map_to_project_case_version(tmp_path: Path) -> None:
    """Unknown stored benchmark semantics must not collapse to the current case version."""

    from benchmarks.evidence import collect_asv_evidence

    commit = "c" * 40
    results = tmp_path / ".asv" / "results"
    path = results / "host" / "bad-version.json"
    _write_asv_result(
        path,
        commit=commit,
        values=[0.1],
        samples=[[0.1]],
        loads=[10_000],
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    row = payload["results"][
        "benchmarks.TimeGeographicLookupNumbers.time_lookup_geographic_numbers"
    ]
    row[2] = "unknown-semantic-version"
    path.write_text(json.dumps(payload), encoding="utf-8")
    records = collect_asv_evidence(
        results,
        campaign_id="release",
        revisions=(campaign_module.ResolvedRevision("HEAD", commit),),
        cases=("lookup_geographic_numbers",),
        load_sizes=(10_000,),
    )
    assert len(records) == 1
    assert records[0].result_state == "incompatible"
    assert records[0].case_version is None
    assert records[0].stored_benchmark_version == "unknown-semantic-version"


def test_setup_state_markers_preserve_failure_taxonomy(tmp_path: Path) -> None:
    """Correctness and environment/oracle failures must remain distinct in evidence."""

    from benchmarks.evidence import collect_asv_evidence

    commit = "d" * 40
    results = tmp_path / ".asv" / "results"
    path = results / "host" / "states.json"
    loads = [10_000, 20_000, 50_000]
    _write_asv_result(
        path,
        commit=commit,
        values=[None, None, None],
        samples=[None, None, None],
        loads=loads,
    )
    env = "uv-py3.12-numpy1.26.4-pandas2.1.4"
    root = tmp_path / ".asv" / "feregion-state" / commit / env / "lookup_geographic_numbers"
    for load, state in (
        (10_000, "correctness_failed"),
        (20_000, "build_unavailable"),
        (50_000, "execution_failed"),
    ):
        (root / f"{load}.json").write_text(
            json.dumps({"state": state, "reason": state}), encoding="utf-8"
        )
    records = collect_asv_evidence(
        results,
        campaign_id="release",
        revisions=(campaign_module.ResolvedRevision("HEAD", commit),),
        cases=("lookup_geographic_numbers",),
        load_sizes=loads,
    )
    assert [record.result_state for record in records] == [
        "correctness_failed",
        "build_unavailable",
        "execution_failed",
    ]
    assert records[0].correctness_state == "failed"
    assert records[1].correctness_state == "unknown"
    assert records[2].correctness_state == "unknown"


def test_throughput_gate_uses_rate_not_duration_increase() -> None:
    """A 26% duration increase is only ~20.6% throughput loss and must not trigger."""

    baseline = [_record(10_000, 1.0, "base"), _record(20_000, 2.0, "base")]
    candidate = [_record(10_000, 1.26, "cand"), _record(20_000, 2.52, "cand")]
    decision = compare_release_evidence(baseline, candidate)
    assert decision.complete is True
    assert decision.triggered is False

    slower = [_record(10_000, 1.34, "cand"), _record(20_000, 2.68, "cand")]
    triggered = compare_release_evidence(baseline, slower)
    assert triggered.triggered is True
    assert triggered.comparisons[0].slowdown_fraction > 0.25


def test_source_oracle_uses_packaged_hierarchy_asset_names() -> None:
    """The ASV semantic oracle must load the actual packaged seismic assets."""

    from benchmarks.asv_suite.source_oracle import geographic_to_seismic, seismic_names

    crosswalk = geographic_to_seismic()
    names = seismic_names()
    assert crosswalk.shape == (758,)
    assert int(crosswalk[0]) == 0
    assert names.shape == (51,)
    assert str(names[0]) == ""


def test_source_oracle_pin_matches_repository_source_definition() -> None:
    """Duplicated ASV pin metadata must not drift from the authoritative fetch helper."""

    from benchmarks.asv_suite import source_oracle
    from tools import obspy_fe_source

    assert source_oracle.OBSPY_REVISION == obspy_fe_source.OBSPY_REVISION
    assert source_oracle.SOURCE_SHA256 == obspy_fe_source.SOURCE_SHA256


def test_publisher_payload_marks_asv_as_supplementary_during_migration(tmp_path: Path) -> None:
    """The ASV summary must not imply benchmark authority before parity closure."""

    class Graphs:
        def get_params(self):
            return {}

    class Repo:
        def get_tags(self):
            return {}

    payload = build_publisher_payload(
        html_dir=tmp_path,
        benchmarks={},
        graphs=Graphs(),
        revisions={},
        repo=Repo(),
    )
    assert "supplementary" in payload["migration_authority_note"]
    assert "operations-per-second" in payload["throughput_note"]


def test_failed_revision_run_normalizes_conservatively_as_execution_failed(tmp_path: Path) -> None:
    """A run-level failure without phase evidence must not be mislabeled as a build failure."""

    from benchmarks.evidence import collect_asv_evidence

    commit = "e" * 40
    results = tmp_path / ".asv" / "results"
    results.mkdir(parents=True)
    run_record = tmp_path / ".asv" / "feregion-runs" / "release" / f"{commit}.json"
    run_record.parent.mkdir(parents=True)
    run_record.write_text(
        json.dumps({"schema_version": 1, "returncode": 1, "commit": commit}),
        encoding="utf-8",
    )
    records = collect_asv_evidence(
        results,
        campaign_id="release",
        revisions=(campaign_module.ResolvedRevision("HEAD", commit),),
        cases=("lookup_geographic_numbers",),
        load_sizes=(10_000,),
    )
    assert len(records) == 1
    assert records[0].result_state == "execution_failed"
    assert records[0].load_size == 10_000
    assert "does not identify a narrower build/setup phase" in (records[0].reason or "")


def test_migration_parity_document_preserves_predecessor_authority_and_throughput() -> None:
    """Migration docs must keep old harness authority and operations-per-second visible."""

    project_root = Path(__file__).resolve().parents[1]
    text = (project_root / "docs" / "benchmark-migration-parity.md").read_text(encoding="utf-8")
    assert "remain the current authoritative benchmark path" in text
    assert "Direct ObsPy scalar baseline" in text
    assert "median_operations_per_second" in text or "operations_per_second" in text
    assert "pytest-benchmark" in text
    assert "Tox" in text
