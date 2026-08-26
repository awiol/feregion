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
    """The broad legacy ``dev`` extra must cover test, lint, and benchmark tools."""

    data = _pyproject()
    expected = {
        *_requirements_for_group(data, "test"),
        *_requirements_for_group(data, "lint"),
        *_requirements_for_group(data, "benchmark"),
    }
    assert set(data["project"]["optional-dependencies"]["dev"]) == expected


def test_current_contract_documents_match_runtime_version_and_are_traceable() -> None:
    """Only one current versioned contract set exists and every requirement is mapped."""

    version = feregion.__version__
    contract_files = sorted(
        path
        for path in DOCS.glob("feregion-*-v*.md")
        if "requirements" in path.name
        or "design" in path.name
        or "quality-assurance" in path.name
        or "decisions" in path.name
        or "verification-traceability" in path.name
    )
    assert len(contract_files) == 7
    assert all(f"-v{version}-" in path.name for path in contract_files)

    traceability = next(DOCS.glob("feregion-verification-traceability-v*.md"))
    trace_text = traceability.read_text(encoding="utf-8")
    requirement_id_list: list[str] = []
    for path in DOCS.glob("feregion-*requirements-v*.md"):
        requirement_id_list.extend(
            re.findall(r"\bREQ-[A-Z]+-\d{3}\b", path.read_text(encoding="utf-8"))
        )
    requirement_ids = set(requirement_id_list)
    assert requirement_ids
    assert len(requirement_id_list) == len(requirement_ids)
    assert all(trace_text.count(f"`{requirement_id}`") == 1 for requirement_id in requirement_ids)


def test_readme_lists_every_current_versioned_contract_document() -> None:
    """The repository entry point must not point maintainers at superseded contracts."""

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for path in DOCS.glob("feregion-*-v*.md"):
        is_contract = (
            "requirements" in path.name
            or "design" in path.name
            or "quality-assurance" in path.name
            or "decisions" in path.name
            or "verification-traceability" in path.name
        )
        if is_contract:
            assert f"docs/{path.name}" in readme


def test_ci_matrix_covers_declared_python_versions() -> None:
    """The hosted test matrix includes every explicitly verified Python version."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for version in ("3.11", "3.12", "3.13"):
        assert f'"{version}"' in workflow


def test_ci_declares_direct_oracle_and_lower_bound_jobs() -> None:
    """CI keeps reference-oracle and dependency-range evidence explicit."""

    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "reference-oracle:" in workflow
    assert "tests/test_obspy_oracle.py" in workflow
    assert "minimum-dependencies:" in workflow
    for requirement in ("numpy==1.26.0", "pandas==2.1.0", "shapely==2.0.0"):
        assert requirement in workflow
