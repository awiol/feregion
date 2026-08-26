"""Wheel archive inspection contracts for release verification."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools.verify_wheel import REQUIRED_PACKAGE_FILES, inspect_wheel


def _write_valid_synthetic_wheel(path: Path) -> None:
    """Create the smallest ZIP archive that satisfies wheel inspection fields."""

    dist = "feregion-9.8.7.dist-info"
    metadata = [
        "Metadata-Version: 2.4",
        "Name: feregion",
        "Version: 9.8.7",
        "Requires-Python: >=3.11",
    ]
    metadata.extend(
        f"Provides-Extra: {extra}" for extra in ("pandas", "geo", "test", "benchmark", "dev")
    )
    with zipfile.ZipFile(path, "w") as archive:
        for name in REQUIRED_PACKAGE_FILES:
            archive.writestr(name, b"placeholder")
        archive.writestr(f"{dist}/METADATA", "\n".join(metadata) + "\n")
        archive.writestr(
            f"{dist}/entry_points.txt",
            "[console_scripts]\nfe-region = feregion.cli:main\n",
        )
        archive.writestr(f"{dist}/licenses/LICENSE", "license")
        archive.writestr(f"{dist}/licenses/THIRD_PARTY_NOTICES.md", "notice")
        archive.writestr(f"{dist}/licenses/LICENSES/GPL-3.0.txt", "gpl")


def test_wheel_inspection_accepts_complete_runtime_archive(tmp_path: Path) -> None:
    """A wheel with the runtime contract, extras, entry point, and notices passes."""

    wheel = tmp_path / "feregion-9.8.7-py3-none-any.whl"
    _write_valid_synthetic_wheel(wheel)

    assert inspect_wheel(wheel, expected_version="9.8.7") == "9.8.7"


def test_wheel_inspection_rejects_repository_only_source(tmp_path: Path) -> None:
    """Tests and developer tooling must not leak into the runtime wheel."""

    wheel = tmp_path / "feregion-9.8.7-py3-none-any.whl"
    _write_valid_synthetic_wheel(wheel)
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("tests/test_example.py", "pass\n")

    with pytest.raises(ValueError, match="repository-only"):
        inspect_wheel(wheel, expected_version="9.8.7")
