"""Compute the deterministic source-tree digest used by feregion deliveries.

The digest is defined over regular source files below one extracted source root.
Entries are sorted lexicographically by POSIX relative path. For each entry the
verifier emits the UTF-8 record ``"{mode} {file_sha256} {relative_path}\\n"``
where ``mode`` is ``100755`` for executable files and ``100644`` otherwise. The
SHA-256 of the concatenated record bytes is the source-tree digest.

Python may create ``__pycache__`` directories while this verifier is imported,
notably for ``python -m tools.source_tree_digest``. Such interpreter-generated
cache directories are outside the source-tree digest domain. Source delivery
archives must not contain them, and the delivery archive inventory/checksum is
verified separately. Ignoring those transient directories makes the digest
stable across the supported direct-script and module invocation forms.
"""

from __future__ import annotations

import argparse
import hashlib
import stat
from dataclasses import dataclass
from pathlib import Path

_TRANSIENT_DIRECTORY_NAMES = frozenset({"__pycache__"})


class SourceTreeDigestError(RuntimeError):
    """Raised when a source tree cannot be represented by the digest contract."""


@dataclass(frozen=True, slots=True)
class SourceTreeEntry:
    """Describe one regular source-tree file in digest order."""

    relative_path: str
    mode: str
    file_sha256: str

    def record(self) -> bytes:
        """Return the exact UTF-8 record incorporated into the tree digest."""

        return f"{self.mode} {self.file_sha256} {self.relative_path}\n".encode()


def _entry(root: Path, path: Path) -> SourceTreeEntry:
    """Return one digest entry for a regular file below ``root``."""

    file_stat = path.lstat()
    if stat.S_ISLNK(file_stat.st_mode):
        raise SourceTreeDigestError(f"symbolic links are not supported: {path}")
    if not stat.S_ISREG(file_stat.st_mode):
        raise SourceTreeDigestError(f"non-regular source-tree path is not supported: {path}")

    relative_path = path.relative_to(root).as_posix()
    mode = "100755" if file_stat.st_mode & stat.S_IXUSR else "100644"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return SourceTreeEntry(relative_path=relative_path, mode=mode, file_sha256=digest)


def _is_transient_interpreter_path(root: Path, path: Path) -> bool:
    """Return whether ``path`` belongs to an interpreter-created cache directory."""

    relative = path.relative_to(root)
    return any(part in _TRANSIENT_DIRECTORY_NAMES for part in relative.parts)


def source_tree_entries(root: Path) -> tuple[SourceTreeEntry, ...]:
    """Return source-tree entries sorted lexicographically by relative path.

    Args:
        root: Extracted source root whose direct descendants form the repository
            tree (for example the ``feregion/`` directory from a source archive).

    Returns:
        Deterministically ordered regular-file entries. Files below a directory
        named ``__pycache__`` are excluded because Python can create them as a
        side effect of invoking this verifier as a module.

    Raises:
        SourceTreeDigestError: If ``root`` is invalid or the digest domain
            contains a symbolic link/non-regular file.
    """

    root = root.resolve()
    if not root.is_dir():
        raise SourceTreeDigestError(f"source root is not a directory: {root}")

    paths = sorted(
        (
            path
            for path in root.rglob("*")
            if not _is_transient_interpreter_path(root, path)
            and not stat.S_ISDIR(path.lstat().st_mode)
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    return tuple(_entry(root, path) for path in paths)


def source_tree_sha256(root: Path) -> str:
    """Return the path-ordered source-tree SHA-256 digest for ``root``."""

    digest = hashlib.sha256()
    for entry in source_tree_entries(root):
        digest.update(entry.record())
    return digest.hexdigest()


def _verify_expected(
    parser: argparse.ArgumentParser,
    *,
    digest: str,
    file_count: int,
    expected_digest: str | None,
    expected_files: int | None,
) -> None:
    """Reject a digest or file-count mismatch requested by the CLI caller."""

    if expected_digest is not None and digest != expected_digest:
        parser.exit(1, f"error: expected sha256 {expected_digest}, got {digest}\n")
    if expected_files is not None and file_count != expected_files:
        parser.exit(1, f"error: expected {expected_files} files, got {file_count}\n")


def main(argv: list[str] | None = None) -> int:
    """Print and optionally verify the digest and path count for one source root."""

    parser = argparse.ArgumentParser(description="Compute the feregion source-tree digest.")
    parser.add_argument("root", type=Path, help="extracted source root, e.g. ./feregion")
    parser.add_argument(
        "--expect-sha256",
        help="exit unsuccessfully unless the computed digest matches this value",
    )
    parser.add_argument(
        "--expect-files",
        type=int,
        help="exit unsuccessfully unless the digest domain contains this many files",
    )
    args = parser.parse_args(argv)
    try:
        entries = source_tree_entries(args.root)
    except SourceTreeDigestError as exc:
        parser.exit(2, f"error: {exc}\n")

    digest = hashlib.sha256(b"".join(entry.record() for entry in entries)).hexdigest()
    _verify_expected(
        parser,
        digest=digest,
        file_count=len(entries),
        expected_digest=args.expect_sha256,
        expected_files=args.expect_files,
    )
    print(f"sha256: {digest}")
    print(f"files: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
