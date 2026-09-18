"""Contract tests for clean Git-tracked repository handoff export.

These tests create small temporary Git working trees so the exporter is checked
against the same tracked/untracked distinction used in a maintainer repository.
They verify current working-tree bytes rather than only committed/index bytes,
because a handoff must preserve local formatting and checking edits while still
excluding local-only state and the project-specific ``uv.lock`` exception.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from tools.export_repository import RepositoryExportError, export_repository, main


def _git(repo: Path, *arguments: str) -> None:
    """Run one Git command in the temporary repository used by a test."""

    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)


def _repository(tmp_path: Path) -> Path:
    """Create a representative tracked repository with ignored local state."""

    repo = tmp_path / "feregion"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text(".venv/\n.cache/\nlocal-run.json\n", encoding="utf-8")
    (repo / "README.md").write_text("before\n", encoding="utf-8")
    (repo / "script.py").write_text("print('ok')\n", encoding="utf-8")
    os.chmod(repo / "script.py", 0o755)
    (repo / "uv.lock").write_text("local lock\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "feregion"\nversion = "0.4.0a2"\n',
        encoding="utf-8",
    )
    _git(repo, "add", ".gitignore", "README.md", "script.py", "uv.lock", "pyproject.toml")

    (repo / ".venv").mkdir()
    (repo / ".venv" / "state.txt").write_text("private\n", encoding="utf-8")
    (repo / ".cache").mkdir()
    (repo / ".cache" / "tool.dat").write_text("cache\n", encoding="utf-8")
    (repo / "local-run.json").write_text("{}\n", encoding="utf-8")
    return repo


def test_export_uses_tracked_worktree_and_excludes_local_state(tmp_path: Path) -> None:
    """Tracked edits are exported while lock, ignored, and untracked files stay out."""

    repo = _repository(tmp_path)
    (repo / "README.md").write_text("formatted locally\n", encoding="utf-8")
    (repo / "personal.toml").write_text("editor = true\n", encoding="utf-8")
    output = tmp_path / "handoff.zip"

    result = export_repository(repo, output)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert archive.read("feregion/README.md") == b"formatted locally\n"
        assert "feregion/script.py" in names
        assert "feregion/uv.lock" not in names
        assert "feregion/personal.toml" not in names
        assert not any(".venv" in name or ".cache" in name for name in names)
        mode = archive.getinfo("feregion/script.py").external_attr >> 16
        assert mode & 0o111

    assert result.omitted_tracked_files == ("uv.lock",)
    assert result.untracked_files == ("personal.toml",)
    assert result.sha256 == hashlib.sha256(output.read_bytes()).hexdigest()


def test_export_is_deterministic_for_unchanged_worktree(tmp_path: Path) -> None:
    """Two exports of unchanged tracked bytes are byte-identical."""

    repo = _repository(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    export_repository(repo, first)
    export_repository(repo, second)

    assert first.read_bytes() == second.read_bytes()


def test_strict_export_rejects_nonignored_untracked_source(tmp_path: Path) -> None:
    """Strict mode catches a likely new source file that Git does not track yet."""

    repo = _repository(tmp_path)
    (repo / "new_module.py").write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(RepositoryExportError, match="non-ignored untracked files"):
        export_repository(repo, tmp_path / "handoff.zip", fail_on_untracked=True)


def test_default_cli_output_uses_dist_version_and_utc_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default CLI exports go to dist with package version and UTC date."""

    repo = _repository(tmp_path)

    assert main(["--repository", str(repo)]) == 0

    stdout = capsys.readouterr().out
    archive_line = next(line for line in stdout.splitlines() if line.startswith("archive: "))
    output = Path(archive_line.removeprefix("archive: "))
    assert output.parent == repo / "dist"
    assert output.name.startswith("feregion-v0.4.0a2-")
    assert output.name.endswith("-handoff.zip")
    date_part = output.name.removeprefix("feregion-v0.4.0a2-").removesuffix("-handoff.zip")
    assert len(date_part) == 10
    assert date_part[4] == "-"
    assert date_part[7] == "-"
    assert output.is_file()


def test_export_identity_is_independent_of_checkout_directory(tmp_path: Path) -> None:
    """Project metadata, not checkout-directory name, controls handoff identity."""

    repo = _repository(tmp_path)
    renamed = tmp_path / "renamed-checkout"
    repo.rename(renamed)
    output = tmp_path / "renamed.zip"

    export_repository(renamed, output)

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert names
        assert all(name.startswith("feregion/") for name in names)
        assert not any(name.startswith("renamed-checkout/") for name in names)
