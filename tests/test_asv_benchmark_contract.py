"""Tests for the project-owned ASV benchmark contract and thin campaign layer."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

import benchmarks.campaign as campaign_module
from benchmarks.asv_suite.contracts import CASES, STANDARD_LOAD_SIZES, workload_fingerprint
from benchmarks.campaign import PROFILE_CONFIG, Campaign, benchmark_regex, build_asv_config
from benchmarks.evidence import EvidenceRecord, normalize_asv_result
from benchmarks.regression import compare_release_evidence


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
    plan = campaign.plan()
    assert plan["repetitions"] == 7
    assert plan["case_versions"] == {"lookup_geographic_numbers": 1}


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


def _record(load: int, seconds: float, revision: str) -> EvidenceRecord:
    return EvidenceRecord(
        "lookup_geographic_numbers",
        1,
        revision,
        load,
        "measured",
        (seconds,),
        seconds,
        "host",
        "env",
        "release",
    )


def test_release_gate_triggers_only_on_two_adjacent_slow_loads() -> None:
    """The 25% two-adjacent-load rule remains project-owned and deterministic."""

    baseline = [
        _record(10_000, 1.0, "base"),
        _record(100_000, 10.0, "base"),
        _record(1_000_000, 100.0, "base"),
    ]
    candidate = [
        _record(10_000, 1.3, "cand"),
        _record(100_000, 13.0, "cand"),
        _record(1_000_000, 110.0, "cand"),
    ]
    decision = compare_release_evidence(baseline, candidate)
    assert decision.complete is True
    assert decision.triggered is True
