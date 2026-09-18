"""Create a clean source handoff archive from a Git working tree.

The exporter intentionally treats Git-tracked paths as the repository boundary.
It reads the current working-tree bytes for those paths, so local formatting or
other tracked edits are preserved even before commit. Untracked files are not
included because they cannot be distinguished reliably from editor settings,
local runs, caches, virtual environments, or other maintainer-only state.

``uv.lock`` is a project-specific exception: it may be tracked in the maintainer
repository but is always excluded from AI/source handoffs. The command warns
about non-ignored untracked paths so newly created source files can be staged or
committed before export.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

_ARCHIVE_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_EXCLUDED_TRACKED_PATHS = {PurePosixPath("uv.lock")}


class RepositoryExportError(RuntimeError):
    """Raised when a clean repository handoff archive cannot be produced."""


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Describe one completed repository handoff export.

    Attributes:
        output: Final ZIP path.
        repository_root: Git working-tree root used for discovery.
        included_files: Number of tracked working-tree files in the archive.
        omitted_tracked_files: Tracked paths omitted by explicit handoff policy.
        untracked_files: Non-ignored untracked paths that were not exported.
        sha256: SHA-256 digest of the completed archive.
    """

    output: Path
    repository_root: Path
    included_files: int
    omitted_tracked_files: tuple[str, ...]
    untracked_files: tuple[str, ...]
    sha256: str


def _git_bytes(repository_root: Path, *arguments: str) -> bytes:
    """Run one Git query and return its stdout bytes.

    Args:
        repository_root: Directory in or below the target Git working tree.
        *arguments: Arguments passed after ``git``.

    Returns:
        Raw stdout bytes from Git.

    Raises:
        RepositoryExportError: If Git is unavailable or the query fails.
    """

    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        message = detail.decode("utf-8", errors="replace").strip()
        suffix = f": {message}" if message else ""
        raise RepositoryExportError(f"Git repository query failed{suffix}") from exc
    return completed.stdout


def repository_root(start: Path) -> Path:
    """Return the absolute Git working-tree root containing ``start``.

    Args:
        start: Directory from which Git discovery starts.

    Returns:
        Resolved repository root path.

    Raises:
        RepositoryExportError: If ``start`` is not inside a Git working tree.
    """

    root = _git_bytes(start, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if not root:
        raise RepositoryExportError("Git returned an empty repository root")
    return Path(root).resolve()


def _nul_paths(payload: bytes) -> tuple[PurePosixPath, ...]:
    """Decode one NUL-delimited Git path list into POSIX relative paths."""

    return tuple(
        PurePosixPath(item.decode("utf-8", errors="surrogateescape"))
        for item in payload.split(b"\0")
        if item
    )


def _tracked_paths(root: Path) -> tuple[PurePosixPath, ...]:
    """Return tracked repository paths in deterministic lexical order."""

    return tuple(sorted(_nul_paths(_git_bytes(root, "ls-files", "-z")), key=str))


def _untracked_paths(root: Path) -> tuple[PurePosixPath, ...]:
    """Return non-ignored untracked repository paths in lexical order."""

    payload = _git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z")
    return tuple(sorted(_nul_paths(payload), key=str))


def _zip_info(archive_path: PurePosixPath, source_path: Path) -> zipfile.ZipInfo:
    """Return deterministic ZIP metadata while preserving executable state."""

    file_stat = source_path.lstat()
    if stat.S_ISLNK(file_stat.st_mode):
        raise RepositoryExportError(
            f"tracked symbolic links are not supported by the handoff exporter: {source_path}"
        )
    if not stat.S_ISREG(file_stat.st_mode):
        raise RepositoryExportError(f"tracked path is not a regular file: {source_path}")

    permissions = 0o755 if file_stat.st_mode & stat.S_IXUSR else 0o644
    info = zipfile.ZipInfo(str(archive_path), date_time=_ARCHIVE_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | permissions) << 16
    info.create_system = 3
    return info


def export_repository(
    start: Path,
    output: Path,
    *,
    fail_on_untracked: bool = False,
) -> ExportResult:
    """Export tracked working-tree files to a deterministic handoff ZIP.

    Args:
        start: Directory in or below the Git working tree.
        output: Destination ZIP path. It may be inside or outside the repository;
            the archive itself is never added because only tracked paths are read.
        fail_on_untracked: If true, reject the export when Git reports any
            non-ignored untracked path.

    Returns:
        Metadata for the completed archive.

    Raises:
        RepositoryExportError: If Git discovery fails, an unsupported tracked
            path is encountered, or strict untracked-file checking fails.
    """

    root = repository_root(start)
    tracked = _tracked_paths(root)
    untracked = _untracked_paths(root)
    if fail_on_untracked and untracked:
        joined = ", ".join(str(path) for path in untracked[:10])
        if len(untracked) > 10:
            joined += f", ... ({len(untracked)} total)"
        raise RepositoryExportError(f"non-ignored untracked files are present: {joined}")

    omitted: list[str] = []
    included: list[tuple[PurePosixPath, Path]] = []
    for relative in tracked:
        if relative in _EXCLUDED_TRACKED_PATHS:
            omitted.append(str(relative))
            continue
        source_path = root / Path(relative)
        if not source_path.exists():
            # A tracked file deleted in the working tree should remain deleted in
            # the handoff rather than resurrecting its index/HEAD bytes.
            continue
        included.append((relative, source_path))

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    project_name, _ = _project_identity(root)
    archive_root = PurePosixPath(project_name)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for relative, source_path in included:
                archive_path = archive_root / relative
                info = _zip_info(archive_path, source_path)
                archive.writestr(info, source_path.read_bytes(), compresslevel=9)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return ExportResult(
        output=output,
        repository_root=root,
        included_files=len(included),
        omitted_tracked_files=tuple(omitted),
        untracked_files=tuple(str(path) for path in untracked),
        sha256=digest,
    )


def _project_identity(root: Path) -> tuple[str, str]:
    """Return the canonical project name and version from repository metadata.

    Args:
        root: Resolved repository root containing ``pyproject.toml``.

    Returns:
        Pair of non-empty ``project.name`` and ``project.version`` values.

    Raises:
        RepositoryExportError: If the project metadata cannot be read or does
            not contain usable identity values.
    """

    metadata_path = root / "pyproject.toml"
    try:
        metadata = tomllib.loads(metadata_path.read_text(encoding="utf-8"))
        name = metadata["project"]["name"]
        version = metadata["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise RepositoryExportError(
            f"cannot determine project identity from {metadata_path}"
        ) from exc
    if not isinstance(name, str) or not name.strip() or "/" in name or "\\" in name:
        raise RepositoryExportError(
            f"project.name in {metadata_path} must be a non-empty path-safe string"
        )
    if not isinstance(version, str) or not version.strip():
        raise RepositoryExportError(
            f"project.version in {metadata_path} must be a non-empty string"
        )
    return name.strip(), version.strip()


def _default_output(start: Path) -> Path:
    """Return the versioned, UTC-dated handoff path under ``dist/``."""

    root = repository_root(start)
    project_name, version = _project_identity(root)
    date = datetime.now(UTC).date().isoformat()
    return root / "dist" / f"{project_name}-v{version}-{date}-handoff.zip"


def main(argv: list[str] | None = None) -> int:
    """Create one clean repository handoff archive and print its summary."""

    parser = argparse.ArgumentParser(
        description="Export tracked working-tree source without local repository state."
    )
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fail-on-untracked",
        action="store_true",
        help="fail instead of warning when non-ignored untracked files exist",
    )
    args = parser.parse_args(argv)

    try:
        output = args.output or _default_output(args.repository)
        result = export_repository(
            args.repository,
            output,
            fail_on_untracked=args.fail_on_untracked,
        )
    except RepositoryExportError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(f"archive: {result.output}")
    print(f"tracked files included: {result.included_files}")
    if result.omitted_tracked_files:
        print("policy exclusions: " + ", ".join(result.omitted_tracked_files))
    if result.untracked_files:
        preview = ", ".join(result.untracked_files[:10])
        if len(result.untracked_files) > 10:
            preview += f", ... ({len(result.untracked_files)} total)"
        print(
            "warning: non-ignored untracked files were not included: " + preview,
            file=sys.stderr,
        )
    print(f"sha256: {result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
