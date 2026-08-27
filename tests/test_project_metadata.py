"""Repository metadata synchronization contracts."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import feregion

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"


def _pyproject() -> dict:
    """Load project metadata from the repository authority file."""

    with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def _requirements_for_group(data: dict, name: str) -> list[str]:
    """Flatten one dependency group, including explicit group references."""

    result: list[str] = []
    for item in data["dependency-groups"][name]:
        if isinstance(item, str):
            result.append(item)
        else:
            result.extend(_requirements_for_group(data, item["include-group"]))
    return result


def test_runtime_version_matches_project_metadata() -> None:
    """The importable package version must match the build metadata version."""

    assert feregion.__version__ == _pyproject()["project"]["version"]


def test_compatibility_test_extra_matches_test_dependency_group() -> None:
    """The retained ``test`` extra must not drift from the authoritative uv test group."""

    data = _pyproject()
    assert data["project"]["optional-dependencies"]["test"] == _requirements_for_group(data, "test")


def test_compatibility_benchmark_extra_matches_benchmark_dependency_group() -> None:
    """The retained benchmark extra must match the authoritative uv benchmark group."""

    data = _pyproject()
    assert data["project"]["optional-dependencies"]["benchmark"] == _requirements_for_group(
        data, "benchmark"
    )


def test_compatibility_dev_extra_covers_all_development_groups() -> None:
    """The broad legacy ``dev`` extra must cover test, lint, matrix, and benchmark tools."""

    data = _pyproject()
    expected = {
        *_requirements_for_group(data, "test"),
        *_requirements_for_group(data, "lint"),
        *_requirements_for_group(data, "matrix"),
        *_requirements_for_group(data, "benchmark"),
    }
    assert set(data["project"]["optional-dependencies"]["dev"]) == expected


def test_current_contract_documents_use_stable_names_and_are_traceable() -> None:
    """Maintained contracts use stable Git-tracked paths and map every requirement."""

    expected = {
        "feregion-requirements.md",
        "feregion-engineering-requirements.md",
        "feregion-repository-delivery-requirements.md",
        "feregion-design.md",
        "feregion-quality-assurance.md",
        "feregion-decisions.md",
        "feregion-verification-traceability.md",
    }
    contract_files = {path.name for path in DOCS.glob("feregion-*.md")}
    assert expected <= contract_files
    assert not list(DOCS.glob("feregion-*-v*.md"))

    trace_text = (DOCS / "feregion-verification-traceability.md").read_text(encoding="utf-8")
    requirement_id_list: list[str] = []
    for name in (
        "feregion-requirements.md",
        "feregion-engineering-requirements.md",
        "feregion-repository-delivery-requirements.md",
    ):
        requirement_id_list.extend(
            re.findall(r"\bREQ-[A-Z]+-\d{3}\b", (DOCS / name).read_text(encoding="utf-8"))
        )
    requirement_ids = set(requirement_id_list)
    assert requirement_ids
    assert len(requirement_id_list) == len(requirement_ids)
    assert all(trace_text.count(f"`{requirement_id}`") == 1 for requirement_id in requirement_ids)


def test_readme_lists_every_maintained_contract_document() -> None:
    """The repository entry point links every maintained contract by its stable path."""

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for name in (
        "feregion-requirements.md",
        "feregion-engineering-requirements.md",
        "feregion-repository-delivery-requirements.md",
        "feregion-design.md",
        "feregion-quality-assurance.md",
        "feregion-decisions.md",
        "feregion-verification-traceability.md",
    ):
        assert f"docs/{name}" in readme


def test_maintained_contracts_do_not_embed_current_release_identity() -> None:
    """Git history owns document revision identity; maintained contracts stay release-agnostic."""

    version = _pyproject()["project"]["version"]
    for path in DOCS.glob("feregion-*.md"):
        assert version not in path.read_text(encoding="utf-8")


def test_pre_commit_is_in_uv_development_toolchain() -> None:
    """The commit-time runner is installed through the authoritative uv development group."""

    data = _pyproject()
    assert "pre-commit>=4,<5" in _requirements_for_group(data, "dev")


def test_pre_commit_runs_ruff_format_check_and_pytest_through_uv() -> None:
    """Commit-time hooks reuse the synchronized project environment and required checks."""

    config = (PROJECT_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "entry: uv run --locked --no-sync ruff format" in config
    assert "entry: uv run --locked --no-sync ruff check" in config
    assert "entry: uv run --locked --no-sync pytest -q" in config
    assert "pass_filenames: false" in config


def test_ci_matrix_covers_declared_python_versions() -> None:
    """The hosted test matrix includes every explicitly verified Python version."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for version in ("3.11", "3.12", "3.13", "3.14"):
        assert f'"{version}"' in workflow


def test_ci_declares_direct_oracle_and_lower_bound_jobs() -> None:
    """CI keeps reference-oracle and dependency-range evidence explicit."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "reference-oracle:" in workflow
    assert "tests/test_obspy_oracle.py" in workflow
    assert "minimum-dependencies:" in workflow
    assert "tox run -e minimum" in workflow
    assert "--group matrix" in workflow


def test_tox_uv_matrix_covers_supported_python_and_declared_lower_bounds() -> None:
    """Local tox-uv environments mirror Python support and derive direct lower bounds."""

    with (PROJECT_ROOT / "tox.toml").open("rb") as stream:
        config = tomllib.load(stream)

    assert config["env_list"] == ["3.11", "3.12", "3.13", "3.14", "minimum"]
    assert config["env_run_base"]["runner"] == "uv-venv-runner"
    assert config["env_run_base"]["dependency_groups"] == ["test"]
    minimum = config["env"]["minimum"]
    assert minimum["base_python"] == ["3.11"]
    assert minimum["uv_resolution"] == "lowest-direct"


def test_tox_uv_is_in_development_matrix_toolchain() -> None:
    """The development environment installs tox with the uv-backed runner plugin."""

    data = _pyproject()
    matrix_group = data["dependency-groups"]["matrix"]
    assert matrix_group == ["tox>=4.51,<5", "tox-uv-bare>=1.33,<2"]
    assert set(matrix_group) <= set(_requirements_for_group(data, "dev"))


def test_python_314_is_explicitly_supported_without_raising_minimum() -> None:
    """Metadata must advertise 3.14 while preserving Python 3.11 as the floor."""

    data = _pyproject()
    assert data["project"]["requires-python"] == ">=3.11"
    classifiers = data["project"]["classifiers"]
    assert "Programming Language :: Python :: 3.14" in classifiers


def test_uv_version_uses_compatible_range_without_exact_ci_pin() -> None:
    """Repository tooling must allow compatible uv releases instead of one exact build."""

    data = _pyproject()
    required_version = data["tool"]["uv"]["required-version"]
    assert required_version == ">=0.10,<1"
    assert "==" not in required_version

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "UV_VERSION:" not in workflow
    assert "version: ${{ env.UV_VERSION }}" not in workflow


def test_ci_uses_locked_normal_environments_and_bounds_runs() -> None:
    """Normal CI jobs must preserve the lock and bound obsolete or hung work."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "uv sync --locked --group test" in workflow
    assert "uv sync --locked --group test --group benchmark" in workflow
    assert "uv sync --locked --group test --group lint" in workflow
    assert "uv run --locked pytest" in workflow
    assert "uv run --locked ruff format --check ." in workflow
    assert "uv run --locked ruff check ." in workflow
    assert "concurrency:" in workflow
    assert "cancel-in-progress: true" in workflow
    assert workflow.count("timeout-minutes:") == 4
    assert "branches: [main]" in workflow
    assert workflow.count("persist-credentials: false") == 4
    assert "uv build --locked" in workflow


def test_static_tooling_is_limited_to_ruff_and_pre_commit() -> None:
    """The lint group must contain only the approved static/commit-time tools."""

    data = _pyproject()
    lint_group = data["dependency-groups"]["lint"]
    assert lint_group == ["ruff>=0.15,<0.17", "pre-commit>=4,<5"]
