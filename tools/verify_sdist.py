"""Verify that a source distribution is byte-bound to a frozen source authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_ALLOWED_GENERATED_EXACT = {"PKG-INFO", "setup.cfg"}
_ALLOWED_GENERATED_PREFIXES = ("src/feregion.egg-info/",)


@dataclass(frozen=True)
class SdistParityResult:
    """Summarize source-to-sdist byte parity for one frozen source tree.

    Attributes:
        source_files: Number of authoritative source files checked.
        generated_members: Additional sdist members accepted as generated packaging metadata.
        missing: Authoritative source paths absent from the sdist.
        mismatched: Authoritative source paths whose sdist bytes differ.
        unexpected: Extra sdist members outside the accepted generated-metadata set.
    """

    source_files: int
    generated_members: tuple[str, ...]
    missing: tuple[str, ...]
    mismatched: tuple[str, ...]
    unexpected: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Return whether the sdist is exactly bound to the authoritative source bytes."""

        return not (self.missing or self.mismatched or self.unexpected)


def _source_files(root: Path) -> dict[str, bytes]:
    """Read every regular file from a clean frozen source-recovery tree.

    The release verifier intentionally operates on the exported source-recovery
    authority rather than a mutable Git working tree. Interpreter/build caches and
    version-control metadata are therefore rejected if they appear instead of being
    silently excluded from the verification denominator.
    """

    if not root.is_dir():
        raise ValueError(f"source root is not a directory: {root}")

    forbidden_parts = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
    }
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in forbidden_parts or part.endswith(".egg-info") for part in relative.parts):
            raise ValueError(
                f"source authority contains transient/build path: {relative.as_posix()}"
            )
        if path.is_symlink():
            raise ValueError(
                f"source authority contains unsupported symlink: {relative.as_posix()}"
            )
        if path.is_file():
            files[relative.as_posix()] = path.read_bytes()
    return files


def _sdist_members(sdist: Path) -> tuple[str, dict[str, bytes]]:
    """Return the one top-level sdist directory and its regular-file payloads."""

    if not sdist.is_file():
        raise ValueError(f"sdist does not exist: {sdist}")

    with tarfile.open(sdist, "r:gz") as archive:
        files = [member for member in archive.getmembers() if member.isfile()]
        roots = {PurePosixPath(member.name).parts[0] for member in files}
        if len(roots) != 1:
            raise ValueError(
                f"sdist must contain exactly one top-level directory, got {sorted(roots)}"
            )
        root = next(iter(roots))
        payloads: dict[str, bytes] = {}
        for member in files:
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != root:
                raise ValueError(f"sdist member escapes top-level root: {member.name}")
            relative = PurePosixPath(*parts[1:]).as_posix()
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"unable to read sdist member: {member.name}")
            payloads[relative] = extracted.read()
    return root, payloads


def verify_sdist(source_root: Path, sdist: Path) -> SdistParityResult:
    """Compare all frozen source files with the corresponding sdist members.

    Args:
        source_root: Clean extracted source-recovery authority directory.
        sdist: Built ``.tar.gz`` source distribution.

    Returns:
        Detailed parity result. ``result.ok`` is true only when every source file
        is present byte-for-byte and all extra files are recognized generated
        packaging metadata.
    """

    source_files = _source_files(source_root)
    _, sdist_files = _sdist_members(sdist)

    missing = tuple(sorted(set(source_files) - set(sdist_files)))
    mismatched = tuple(
        sorted(
            path
            for path in set(source_files) & set(sdist_files)
            if source_files[path] != sdist_files[path]
        )
    )

    extras = sorted(set(sdist_files) - set(source_files))
    generated = tuple(
        path
        for path in extras
        if path in _ALLOWED_GENERATED_EXACT
        or any(path.startswith(prefix) for prefix in _ALLOWED_GENERATED_PREFIXES)
    )
    unexpected = tuple(sorted(set(extras) - set(generated)))
    return SdistParityResult(
        source_files=len(source_files),
        generated_members=generated,
        missing=missing,
        mismatched=mismatched,
        unexpected=unexpected,
    )


def _sha256(path: Path) -> str:
    """Return one file's SHA-256 hexadecimal digest."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    """Verify one sdist against a clean source-recovery authority."""

    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args(argv)

    result = verify_sdist(args.source_root.resolve(), args.sdist.resolve())
    record = {
        "schema": "feregion-source-sdist-parity/v1",
        "source_root": str(args.source_root.resolve()),
        "sdist": str(args.sdist.resolve()),
        "sdist_sha256": _sha256(args.sdist.resolve()),
        "source_files": result.source_files,
        "generated_members": list(result.generated_members),
        "missing": list(result.missing),
        "mismatched": list(result.mismatched),
        "unexpected": list(result.unexpected),
        "result": "pass" if result.ok else "fail",
    }
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.json_path is not None:
        args.json_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
