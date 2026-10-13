"""Create a machine-readable handoff of retained benchmark evidence."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class EvidenceFile:
    """One source file selected for the benchmark evidence handoff."""

    source: Path
    archive_path: str
    family: str


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest for one evidence file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class EvidenceBundleError(RuntimeError):
    """Raised when retained evidence crosses the declared preservation boundary."""


@contextlib.contextmanager
def _regular_stream(path: Path) -> Iterator[tuple[BinaryIO, os.stat_result]]:
    """Open one evidence file without intentionally following a leaf symlink."""

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EvidenceBundleError(f"cannot open retained evidence file safely: {path}") from exc
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise EvidenceBundleError(f"retained evidence path is not a regular file: {path}")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            yield stream, file_stat
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _regular_file(path: Path, archive_path: str, family: str) -> EvidenceFile:
    """Classify one retained path without dereferencing symbolic links."""

    try:
        file_stat = path.lstat()
    except FileNotFoundError as exc:
        raise EvidenceBundleError(f"retained evidence path disappeared: {path}") from exc
    if stat.S_ISLNK(file_stat.st_mode):
        raise EvidenceBundleError(f"symbolic links are not valid retained evidence: {path}")
    if not stat.S_ISREG(file_stat.st_mode):
        raise EvidenceBundleError(f"retained evidence path is not a regular file: {path}")
    return EvidenceFile(path, archive_path, family)


def _files_under(root: Path, archive_root: str, family: str) -> list[EvidenceFile]:
    """Return non-symlink regular files below one retained-evidence root."""

    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return []
    if stat.S_ISLNK(root_stat.st_mode):
        raise EvidenceBundleError(f"evidence root must not be a symbolic link: {root}")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise EvidenceBundleError(f"evidence root is not a directory: {root}")
    files: list[EvidenceFile] = []
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for directory_name in tuple(directory_names):
            directory = current_path / directory_name
            directory_stat = directory.lstat()
            if stat.S_ISLNK(directory_stat.st_mode):
                raise EvidenceBundleError(
                    f"symbolic-link directory is not valid retained evidence: {directory}"
                )
            if not stat.S_ISDIR(directory_stat.st_mode):
                raise EvidenceBundleError(f"evidence path is not a directory: {directory}")
        for file_name in file_names:
            path = current_path / file_name
            relative = path.relative_to(root).as_posix()
            files.append(_regular_file(path, f"{archive_root}/{relative}", family))
    return sorted(files, key=lambda item: item.archive_path)


def _optional_file(path: Path, archive_path: str, family: str) -> list[EvidenceFile]:
    """Return one regular evidence item when the source path exists."""

    try:
        path.lstat()
    except FileNotFoundError:
        return []
    return [_regular_file(path, archive_path, family)]


def _regular_file_identity(path: Path) -> tuple[int, str]:
    """Return byte count and SHA-256 from one safely opened regular file."""

    digest = hashlib.sha256()
    count = 0
    with _regular_stream(path) as (stream, _):
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(chunk)
            digest.update(chunk)
    return count, digest.hexdigest()


def _git_output(args: Sequence[str]) -> str | None:
    """Return one Git query result, or ``None`` outside a usable checkout."""

    completed = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def collect_evidence_files() -> list[EvidenceFile]:
    """Collect raw, normalized, predecessor, and configuration evidence files."""

    files: list[EvidenceFile] = []
    files.extend(_files_under(PROJECT_ROOT / ".asv" / "results", "asv/results", "asv-results"))
    files.extend(
        _files_under(
            PROJECT_ROOT / ".asv" / "feregion-state",
            "asv/feregion-state",
            "asv-state",
        )
    )
    files.extend(
        _files_under(
            PROJECT_ROOT / ".asv" / "feregion-runs",
            "asv/feregion-runs",
            "asv-runs",
        )
    )
    files.extend(
        _files_under(
            PROJECT_ROOT / ".asv" / "feregion-plans",
            "asv/feregion-plans",
            "asv-plans",
        )
    )
    files.extend(
        _files_under(
            PROJECT_ROOT / ".asv" / "feregion-environments",
            "asv/feregion-environments",
            "asv-environments",
        )
    )
    files.extend(
        _files_under(
            PROJECT_ROOT / ".asv" / "feregion-reports",
            "asv/feregion-reports",
            "asv-reports",
        )
    )

    env_root = PROJECT_ROOT / ".asv" / "env"
    if env_root.is_dir():
        for path in sorted(env_root.glob("*/asv-env-info.json")):
            files.append(
                EvidenceFile(
                    path,
                    f"asv/environment-metadata/{path.parent.name}/asv-env-info.json",
                    "asv-environment-metadata",
                )
            )

    normalized_root = PROJECT_ROOT / "dist" / "benchmarks"
    if normalized_root.is_dir():
        for path in sorted(normalized_root.glob("*.json")):
            files.append(EvidenceFile(path, f"normalized/{path.name}", "normalized-evidence"))
    files.extend(
        _files_under(
            PROJECT_ROOT / ".tox" / "benchmark-results",
            "predecessor/tox-benchmark-results",
            "predecessor-tox",
        )
    )
    for path in sorted(PROJECT_ROOT.glob("benchmark*.json")):
        files.append(EvidenceFile(path, f"predecessor/{path.name}", "predecessor-json"))

    files.extend(_optional_file(PROJECT_ROOT / "asv.conf.json", "config/asv.conf.json", "config"))
    files.extend(
        _files_under(
            PROJECT_ROOT / "benchmarks" / "campaigns",
            "config/campaigns",
            "config",
        )
    )
    files.extend(
        _files_under(
            PROJECT_ROOT / "benchmarks" / "constraints",
            "config/constraints",
            "config",
        )
    )
    files.extend(_optional_file(PROJECT_ROOT / "pyproject.toml", "config/pyproject.toml", "config"))
    files.extend(_optional_file(PROJECT_ROOT / "uv.lock", "config/uv.lock", "config"))

    by_archive_path: dict[str, EvidenceFile] = {}
    for item in files:
        by_archive_path[item.archive_path] = item
    return [by_archive_path[key] for key in sorted(by_archive_path)]


def _project_version() -> str | None:
    """Return the package version from project metadata when available."""

    path = PROJECT_ROOT / "pyproject.toml"
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def build_manifest(files: Iterable[EvidenceFile]) -> dict[str, object]:
    """Build the machine-readable manifest for one handoff archive."""

    inventory = []
    families: dict[str, int] = {}
    for item in files:
        size, digest = _regular_file_identity(item.source)
        inventory.append(
            {
                "path": item.archive_path,
                "family": item.family,
                "size": size,
                "sha256": digest,
            }
        )
        families[item.family] = families.get(item.family, 0) + 1

    expected = (
        "asv-results",
        "asv-state",
        "asv-runs",
        "asv-plans",
        "asv-environments",
        "asv-reports",
        "normalized-evidence",
        "predecessor-json",
        "predecessor-tox",
    )
    return {
        "schema_version": 1,
        "artifact": "feregion-benchmark-evidence-handoff",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "project_version": _project_version(),
        "git": {
            "head": _git_output(["rev-parse", "HEAD"]),
            "status_porcelain": _git_output(["status", "--porcelain"]),
            "tags": _git_output(["show-ref", "--tags"]),
        },
        "families": {
            name: {"present": families.get(name, 0) > 0, "file_count": families.get(name, 0)}
            for name in expected
        },
        "derived_html_included": False,
        "inventory": inventory,
    }


def default_output_path() -> Path:
    """Return a timestamped default handoff path below ``dist/benchmarks``."""

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    version = _project_version() or "unknown"
    filename = f"feregion-{version}-benchmark-evidence-{stamp}.zip"
    return PROJECT_ROOT / "dist" / "benchmarks" / filename


def create_bundle(output: Path) -> tuple[Path, dict[str, object]]:
    """Create one ZIP handoff and return its path and manifest."""

    output = output.resolve()
    files = [item for item in collect_evidence_files() if item.source.resolve() != output]
    manifest = build_manifest(files)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary: Path | None = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for item in files:
                with (
                    _regular_stream(item.source) as (source, _),
                    archive.open(item.archive_path, "w", force_zip64=True) as target,
                ):
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        target.write(chunk)
            archive.writestr(
                "benchmark-evidence-manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            )
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output, manifest


def _parser() -> argparse.ArgumentParser:
    """Build the human-operator command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="ZIP path; defaults to a timestamped file under dist/benchmarks",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Create the evidence handoff and print a compact machine-readable result."""

    args = _parser().parse_args(argv)
    output, manifest = create_bundle(args.output or default_output_path())
    payload = {
        "output": str(output),
        "sha256": _sha256(output),
        "families": manifest["families"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
