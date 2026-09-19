"""Verify ASV benchmark environments against their requested dependency profile."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
import traceback
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any


class EnvironmentIntegrityError(RuntimeError):
    """Raised when an ASV environment does not satisfy its recorded profile."""


@dataclass(frozen=True, slots=True)
class EnvironmentVerification:
    """Observed dependency state for one ASV benchmark environment.

    Attributes:
        managed: Whether the current process runs inside an ASV-managed virtual
            environment with ``asv-env-info.json`` metadata.
        environment: ASV environment identity, when available.
        requested: Requirement versions recorded by ASV for the environment.
        observed: Installed distribution versions observed in the running
            interpreter.
        asv_runner_version: Exact asv-runner distribution version executing the benchmark
            environment, when installed.
        imports: Import checks for requested benchmark dependencies.
        pip_check_returncode: Exit status from ``python -m pip check``.
        pip_check_output: Combined diagnostic output from ``pip check``.
        valid: Whether requested versions, imports, and dependency consistency
            all passed.
        reason: Human-readable failure summary when ``valid`` is false.
    """

    managed: bool
    environment: str | None
    requested: dict[str, str]
    observed: dict[str, str | None]
    asv_runner_version: str | None
    imports: dict[str, str]
    pip_check_returncode: int | None
    pip_check_output: str | None
    valid: bool
    reason: str | None

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the verification."""

        return asdict(self)


_IMPORT_TARGETS = {
    "numpy": "numpy",
    "pandas": "pandas",
    "obspy": "obspy",
    "setuptools": "setuptools",
}


def _environment_info_path() -> Path | None:
    """Return the ASV environment metadata path for the current interpreter.

    ASV exports ``ASV_ENV_DIR`` for benchmark processes. The ``uv`` backend
    executes the environment interpreter without guaranteeing that
    ``VIRTUAL_ENV`` is present, so the ASV-owned path is authoritative here.
    ``VIRTUAL_ENV`` remains a fallback for direct or test invocation.
    """

    environment_dir = os.environ.get("ASV_ENV_DIR") or os.environ.get("VIRTUAL_ENV")
    if not environment_dir:
        return None
    path = Path(environment_dir) / "asv-env-info.json"
    return path if path.is_file() else None


def _environment_record_path(environment: str | None) -> Path | None:
    """Return the retained project environment-verification path."""

    conf_dir = os.environ.get("ASV_CONF_DIR")
    commit = os.environ.get("ASV_COMMIT")
    if not conf_dir or not commit or not environment:
        return None
    digest = sha256(environment.encode("utf-8")).hexdigest()[:16]
    return Path(conf_dir) / ".asv" / "feregion-environments" / commit / f"{digest}.json"


def _write_environment_record(report: EnvironmentVerification) -> None:
    """Retain one atomic environment-verification record during an ASV run."""

    path = _environment_record_path(report.environment)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_json()
    payload.update(
        {
            "schema_version": 1,
            "commit": os.environ.get("ASV_COMMIT"),
            "python_executable": sys.executable,
            "python_version": sys.version,
        }
    )
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _import_diagnostics(requested: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Import requested benchmark dependencies and return diagnostics."""

    imports: dict[str, str] = {}
    failures: list[str] = []
    for requirement in requested:
        module = _IMPORT_TARGETS.get(requirement)
        if module is None:
            continue
        try:
            importlib.import_module(module)
        except Exception:
            detail = traceback.format_exc().strip()
            imports[requirement] = detail
            failures.append(f"required import {module!r} failed")
        else:
            imports[requirement] = "ok"

    # ObsPy 1.4.2 imports pkg_resources through its normal top-level import.
    # Keep this explicit so a future packaging change cannot silently recreate
    # the environment failure observed during the b1 reference comparison.
    if "obspy" in requested:
        try:
            module = importlib.import_module("obspy.geodetics")
            _flinn_engdahl = module.FlinnEngdahl
        except Exception:
            detail = traceback.format_exc().strip()
            imports["obspy.geodetics.FlinnEngdahl"] = detail
            failures.append("required ObsPy FlinnEngdahl import failed")
        else:
            imports["obspy.geodetics.FlinnEngdahl"] = "ok"

    return imports, failures


def _pip_check() -> tuple[int, str]:
    """Return the dependency-consistency result for the running interpreter."""

    completed = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    return completed.returncode, output


@lru_cache(maxsize=1)
def verify_benchmark_environment() -> EnvironmentVerification:
    """Verify the current ASV environment before benchmark timing.

    Outside an ASV-managed environment this function returns an unmanaged,
    successful report so repository tests and direct imports remain usable.
    During an ASV run it compares the exact requirement versions recorded by
    ``asv-env-info.json`` with installed distribution metadata, imports known
    benchmark dependencies, executes ``pip check``, and retains the observed
    environment record under ``.asv/feregion-environments``.

    Returns:
        The retained environment verification record.

    Raises:
        EnvironmentIntegrityError: If the ASV environment differs from its
            requested profile, a required import fails, or dependency metadata
            is inconsistent.
    """

    info_path = _environment_info_path()
    environment = os.environ.get("ASV_ENV_NAME")
    if info_path is None:
        return EnvironmentVerification(
            managed=False,
            environment=environment,
            requested={},
            observed={},
            asv_runner_version=None,
            imports={},
            pip_check_returncode=None,
            pip_check_output=None,
            valid=True,
            reason=None,
        )

    payload = json.loads(info_path.read_text(encoding="utf-8"))
    requested_raw = payload.get("requirements", {})
    if not isinstance(requested_raw, dict):
        raise EnvironmentIntegrityError("ASV environment metadata has invalid requirements")
    requested = {str(name): str(value) for name, value in requested_raw.items()}

    observed: dict[str, str | None] = {}
    failures: list[str] = []
    for name, expected in requested.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        observed[name] = actual
        if actual != expected:
            failures.append(f"{name} requested {expected}, observed {actual or 'not installed'}")

    try:
        asv_runner_version = importlib.metadata.version("asv-runner")
    except importlib.metadata.PackageNotFoundError:
        asv_runner_version = None

    imports, import_failures = _import_diagnostics(requested)
    failures.extend(import_failures)
    pip_returncode, pip_output = _pip_check()
    if pip_returncode != 0:
        failures.append("pip check reported an inconsistent environment")

    reason = "; ".join(failures) if failures else None
    report = EnvironmentVerification(
        managed=True,
        environment=environment,
        requested=requested,
        observed=observed,
        asv_runner_version=asv_runner_version,
        imports=imports,
        pip_check_returncode=pip_returncode,
        pip_check_output=pip_output,
        valid=not failures,
        reason=reason,
    )
    _write_environment_record(report)
    if not report.valid:
        raise EnvironmentIntegrityError(reason or "benchmark environment integrity check failed")
    return report


def clear_environment_verification_cache() -> None:
    """Clear cached preflight state for tests that mutate environment metadata."""

    verify_benchmark_environment.cache_clear()
