"""Pinned ObsPy Flinn-Engdahl source-data definition.

The repository does not version downloaded ObsPy source tables. Development
commands fetch this pinned upstream revision into the ignored project cache and
verify every file before asset generation or source-reference tests use it.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

OBSPY_REVISION = "1.4.2"
OBSPY_COMMIT = "a629e8c021052904b6b8d62699d03f2a3721ae63"
OBSPY_REPOSITORY = "https://github.com/obspy/obspy"
OBSPY_DATA_PATH = "obspy/geodetics/data"
RAW_BASE_URL = f"https://raw.githubusercontent.com/obspy/obspy/{OBSPY_COMMIT}/{OBSPY_DATA_PATH}"
DEFAULT_SOURCE_DIR = (
    Path(__file__).resolve().parents[1] / ".cache" / "feregion" / f"obspy-fe-{OBSPY_REVISION}"
)

SOURCE_SHA256 = {
    "names.asc": "4b827d5f66bf47256fed52bd0bbf265751d0e34e3356477d2bbda1fcca980ce7",
    "nesect.asc": "201316b895c2da2e373dce1f5e20e0bd0df6ce730cf40ad2f607c5f34b5f4728",
    "nwsect.asc": "dcbca0ae4fe2c020d6e9ce5406b40466271e79dcc8785acf285e7fd6046ad29d",
    "quadsidx.asc": "3e3a7553780c2233f11c2ebef014393a7bd32617a353de4e7f1214dd2f68e9e0",
    "sesect.asc": "831256e2c4c2fd5543816a62a7d68840987200bd13bf8633b6ae628fecd739d8",
    "swsect.asc": "f041077c0ea68add8d9d67ace0b3548bf969650c4efdd2ad4dfabb528d28b4bf",
}
SOURCE_FILES = tuple(SOURCE_SHA256)


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of ``data``."""

    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest of one source file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_dir(
    source_dir: Path = DEFAULT_SOURCE_DIR,
    expected_sha256: Mapping[str, str] = SOURCE_SHA256,
) -> None:
    """Verify that all pinned source files exist and match their expected hashes.

    Raises:
        FileNotFoundError: If a required source file is absent.
        ValueError: If a source file does not match the pinned SHA-256 digest.
    """

    for name, expected_digest in expected_sha256.items():
        path = source_dir / name
        if not path.is_file():
            raise FileNotFoundError(
                f"missing ObsPy FE source file: {path}; run "
                "`uv run python -m tools.fetch_obspy_fe_data`"
            )
        observed_sha256 = sha256_file(path)
        if observed_sha256 != expected_digest:
            raise ValueError(
                f"unexpected SHA-256 for {path}: expected {expected_digest}, got {observed_sha256}"
            )
