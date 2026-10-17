"""Regression tests for exact source-to-sdist release evidence binding."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from tools.verify_sdist import verify_sdist


def _write_sdist(path: Path, members: dict[str, bytes]) -> None:
    """Write a small deterministic gzip tar source distribution for one test."""

    with tarfile.open(path, "w:gz") as archive:
        for relative, payload in sorted(members.items()):
            info = tarfile.TarInfo(f"feregion-0.0.0/{relative}")
            info.size = len(payload)
            info.mtime = 0
            archive.addfile(info, io.BytesIO(payload))


def test_verify_sdist_accepts_exact_source_members_and_generated_metadata(tmp_path: Path) -> None:
    """Exact source bytes plus recognized packaging metadata satisfy the parity contract."""

    source = tmp_path / "source"
    (source / "docs").mkdir(parents=True)
    (source / "src" / "feregion").mkdir(parents=True)
    (source / "README.md").write_text("readme\n", encoding="utf-8")
    (source / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")
    (source / "src" / "feregion" / "__init__.py").write_text("VERSION = 1\n", encoding="utf-8")

    sdist = tmp_path / "feregion.tar.gz"
    _write_sdist(
        sdist,
        {
            "README.md": b"readme\n",
            "docs/guide.md": b"guide\n",
            "src/feregion/__init__.py": b"VERSION = 1\n",
            "PKG-INFO": b"generated\n",
            "setup.cfg": b"generated\n",
            "src/feregion.egg-info/PKG-INFO": b"generated\n",
        },
    )

    result = verify_sdist(source, sdist)
    assert result.ok
    assert result.source_files == 3
    assert result.missing == ()
    assert result.mismatched == ()
    assert result.unexpected == ()


def test_verify_sdist_rejects_one_byte_source_drift(tmp_path: Path) -> None:
    """A one-byte or whitespace-only source difference must fail exact package evidence."""

    source = tmp_path / "source"
    source.mkdir()
    (source / "decision.md").write_text("decision\n\n", encoding="utf-8")

    sdist = tmp_path / "feregion.tar.gz"
    _write_sdist(sdist, {"decision.md": b"decision\n", "PKG-INFO": b"generated\n"})

    result = verify_sdist(source, sdist)
    assert not result.ok
    assert result.mismatched == ("decision.md",)


def test_verify_sdist_rejects_unexpected_extra_member(tmp_path: Path) -> None:
    """Unclassified sdist files cannot enter exact-target evidence silently."""

    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("readme\n", encoding="utf-8")

    sdist = tmp_path / "feregion.tar.gz"
    _write_sdist(sdist, {"README.md": b"readme\n", "mystery.txt": b"unexpected\n"})

    result = verify_sdist(source, sdist)
    assert not result.ok
    assert result.unexpected == ("mystery.txt",)
