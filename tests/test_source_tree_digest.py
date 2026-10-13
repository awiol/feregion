"""Tests for the delivery source-tree digest contract and executable verifier."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tools.source_tree_digest import source_tree_entries, source_tree_sha256

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_source_tree_digest_sorts_by_relative_path_before_emitting_records(tmp_path: Path) -> None:
    """Digest order is path order, not lexical order of mode/hash/path records."""

    root = tmp_path / "feregion"
    root.mkdir()
    executable = root / "a-tool"
    executable.write_bytes(b"tool\n")
    executable.chmod(0o755)
    ordinary = root / "z-data"
    ordinary.write_bytes(b"data\n")

    entries = source_tree_entries(root)
    assert [entry.relative_path for entry in entries] == ["a-tool", "z-data"]
    assert [entry.mode for entry in entries] == ["100755", "100644"]

    expected = hashlib.sha256(b"".join(entry.record() for entry in entries)).hexdigest()
    assert source_tree_sha256(root) == expected


def test_source_tree_digest_ignores_python_cache_side_effects(tmp_path: Path) -> None:
    """Interpreter-created ``__pycache__`` files cannot change the digest domain."""

    root = tmp_path / "feregion"
    cache = root / "tools" / "__pycache__"
    cache.mkdir(parents=True)
    (root / "README.md").write_text("source\n", encoding="utf-8")
    (cache / "source_tree_digest.cpython-313.pyc").write_bytes(b"transient")

    entries = source_tree_entries(root)
    assert [entry.relative_path for entry in entries] == ["README.md"]


def _fresh_cli_fixture(tmp_path: Path) -> Path:
    """Create a fresh extracted-source analogue containing the real verifier."""

    root = tmp_path / "feregion"
    tools = root / "tools"
    tools.mkdir(parents=True)
    shutil.copy2(
        PROJECT_ROOT / "tools" / "__init__.py",
        tools / "__init__.py",
    )
    shutil.copy2(
        PROJECT_ROOT / "tools" / "source_tree_digest.py",
        tools / "source_tree_digest.py",
    )
    (root / "README.md").write_text("fresh extraction\n", encoding="utf-8")
    return root


def _run_cli(root: Path, *command: str) -> subprocess.CompletedProcess[str]:
    """Run one verifier CLI form in the fresh extracted-source analogue."""

    environment = os.environ.copy()
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    return subprocess.run(
        command,
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_source_tree_digest_cli_is_stable_across_script_and_module_invocation(
    tmp_path: Path,
) -> None:
    """Both supported CLI forms verify the same fresh tree despite module bytecode."""

    root = _fresh_cli_fixture(tmp_path)
    expected_digest = source_tree_sha256(root)
    expected_files = len(source_tree_entries(root))
    assert expected_files == 3

    direct = _run_cli(
        root,
        sys.executable,
        "tools/source_tree_digest.py",
        ".",
        "--expect-sha256",
        expected_digest,
        "--expect-files",
        str(expected_files),
    )
    assert direct.returncode == 0, direct.stderr
    assert f"sha256: {expected_digest}" in direct.stdout
    assert f"files: {expected_files}" in direct.stdout

    module = _run_cli(
        root,
        sys.executable,
        "-m",
        "tools.source_tree_digest",
        ".",
        "--expect-sha256",
        expected_digest,
        "--expect-files",
        str(expected_files),
    )
    assert module.returncode == 0, module.stderr
    assert f"sha256: {expected_digest}" in module.stdout
    assert f"files: {expected_files}" in module.stdout
    assert list((root / "tools" / "__pycache__").glob("*.pyc"))
    assert len(source_tree_entries(root)) == expected_files
    assert source_tree_sha256(root) == expected_digest
