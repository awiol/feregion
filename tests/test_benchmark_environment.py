"""Benchmark-environment integrity and evidence-handoff regressions."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import benchmarks.evidence_bundle as evidence_bundle
from benchmarks.asv_suite import environment as environment_module
from benchmarks.asv_suite.environment import EnvironmentIntegrityError


def _configure_managed_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    requirements: dict[str, str],
) -> Path:
    """Create minimal ASV metadata and environment variables for one test."""

    env = tmp_path / "env"
    env.mkdir()
    (env / "asv-env-info.json").write_text(
        json.dumps({"python": "3.12", "requirements": requirements, "tool_name": "uv"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("ASV_ENV_DIR", str(env))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setenv("ASV_CONF_DIR", str(tmp_path))
    monkeypatch.setenv("ASV_ENV_NAME", "uv-py3.12-test")
    monkeypatch.setenv("ASV_COMMIT", "a" * 40)
    environment_module.clear_environment_verification_cache()
    return env


def test_environment_preflight_falls_back_to_virtual_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct invocations may locate ASV metadata through ``VIRTUAL_ENV``."""

    env = _configure_managed_environment(
        tmp_path,
        monkeypatch,
        requirements={"numpy": "1.26.4"},
    )
    monkeypatch.delenv("ASV_ENV_DIR", raising=False)
    monkeypatch.setenv("VIRTUAL_ENV", str(env))
    monkeypatch.setattr(environment_module.importlib.metadata, "version", lambda name: "1.26.4")
    monkeypatch.setattr(environment_module.importlib, "import_module", lambda name: object())
    monkeypatch.setattr(
        environment_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="No broken requirements found.\n", stderr=""
        ),
    )

    report = environment_module.verify_benchmark_environment()
    assert report.managed is True
    assert report.valid is True


def test_environment_preflight_rejects_declared_installed_version_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requested ASV versions must match the distributions used for timing."""

    _configure_managed_environment(
        tmp_path,
        monkeypatch,
        requirements={"numpy": "1.26.4", "pandas": "2.1.4"},
    )
    versions = {"numpy": "2.5.3", "pandas": "2.1.4"}
    monkeypatch.setattr(
        environment_module.importlib.metadata,
        "version",
        lambda name: versions[name],
    )
    monkeypatch.setattr(environment_module.importlib, "import_module", lambda name: object())
    monkeypatch.setattr(
        environment_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="broken deps", stderr=""),
    )

    with pytest.raises(EnvironmentIntegrityError, match=r"numpy requested 1.26.4, observed 2.5.3"):
        environment_module.verify_benchmark_environment()

    records = list((tmp_path / ".asv" / "feregion-environments").rglob("*.json"))
    assert len(records) == 1
    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["valid"] is False
    assert payload["requested"]["numpy"] == "1.26.4"
    assert payload["observed"]["numpy"] == "2.5.3"
    assert payload["pip_check_returncode"] == 1


def test_environment_preflight_retains_successful_observed_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consistent requested profile must be retained as successful evidence."""

    requirements = {
        "obspy": "1.4.2",
        "numpy": "1.26.4",
        "pandas": "2.1.4",
        "setuptools": "81.0.0",
    }
    _configure_managed_environment(tmp_path, monkeypatch, requirements=requirements)
    monkeypatch.setattr(
        environment_module.importlib.metadata,
        "version",
        lambda name: requirements[name],
    )
    fake_obspy = SimpleNamespace(FlinnEngdahl=object)

    def fake_import(name: str):
        if name == "obspy.geodetics":
            return fake_obspy
        return object()

    monkeypatch.setattr(environment_module.importlib, "import_module", fake_import)
    monkeypatch.setattr(
        environment_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="No broken requirements found.\n", stderr=""
        ),
    )

    report = environment_module.verify_benchmark_environment()
    assert report.valid is True
    assert report.requested == requirements
    assert report.observed == requirements
    assert report.imports["obspy.geodetics.FlinnEngdahl"] == "ok"


def test_evidence_bundle_collects_machine_readable_preservation_set_without_html(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The operator handoff must preserve raw evidence and exclude rebuildable HTML."""

    monkeypatch.setattr(evidence_bundle, "PROJECT_ROOT", tmp_path)
    (tmp_path / ".asv" / "results" / "host").mkdir(parents=True)
    (tmp_path / ".asv" / "results" / "host" / "result.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".asv" / "feregion-state").mkdir(parents=True)
    (tmp_path / ".asv" / "feregion-state" / "state.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".asv" / "feregion-runs").mkdir(parents=True)
    (tmp_path / ".asv" / "feregion-runs" / "run.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".asv" / "feregion-environments").mkdir(parents=True)
    (tmp_path / ".asv" / "feregion-environments" / "env.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".asv" / "feregion-reports").mkdir(parents=True)
    (tmp_path / ".asv" / "feregion-reports" / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".asv" / "html").mkdir(parents=True)
    (tmp_path / ".asv" / "html" / "index.html").write_text("derived", encoding="utf-8")
    (tmp_path / "benchmarks" / "campaigns").mkdir(parents=True)
    (tmp_path / "benchmarks" / "campaigns" / "smoke.toml").write_text(
        "[campaign]\n", encoding="utf-8"
    )
    (tmp_path / "benchmarks" / "constraints").mkdir(parents=True)
    (tmp_path / "benchmarks" / "constraints" / "reference-comparison.txt").write_text(
        "setuptools==81.0.0\n", encoding="utf-8"
    )
    (tmp_path / "benchmark-standalone.json").write_text("{}", encoding="utf-8")
    (tmp_path / "asv.conf.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="feregion"\nversion="0.4.0b3"\n', encoding="utf-8"
    )
    monkeypatch.setattr(evidence_bundle, "_git_output", lambda args: None)

    output, manifest = evidence_bundle.create_bundle(tmp_path / "handoff.zip")
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        payload = json.loads(archive.read("benchmark-evidence-manifest.json"))

    assert "asv/results/host/result.json" in names
    assert "asv/feregion-environments/env.json" in names
    assert "asv/feregion-reports/report.json" in names
    assert "predecessor/benchmark-standalone.json" in names
    assert "config/constraints/reference-comparison.txt" in names
    assert not any(name.startswith("asv/html/") for name in names)
    assert payload["derived_html_included"] is False
    assert manifest["families"]["asv-results"]["present"] is True
    assert manifest["families"]["asv-reports"]["present"] is True
    assert manifest["families"]["predecessor-tox"]["present"] is False
