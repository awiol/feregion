"""Generate compact runtime assets from verified ObsPy FE source tables."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.obspy_fe_source import (
    DEFAULT_SOURCE_DIR,
    OBSPY_DATA_PATH,
    OBSPY_REPOSITORY,
    OBSPY_REVISION,
    SOURCE_FILES,
    verify_source_dir,
)

QUADRANTS = ("ne", "nw", "se", "sw")
SECTION_FILES = {
    "ne": "nesect.asc",
    "nw": "nwsect.asc",
    "se": "sesect.asc",
    "sw": "swsect.asc",
}
EXPECTED_LATITUDE_ROWS = 91
EXPECTED_NAME_COUNT = 757


def sha256(path: Path) -> str:
    """Return a lowercase SHA-256 digest for one file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_integer_tokens(path: Path) -> list[int]:
    """Read whitespace-separated decimal integers from an FE source table."""

    return [int(token) for token in path.read_text(encoding="ascii").split()]


def read_names(path: Path) -> list[str]:
    """Read the one-based FE region name sequence from ``names.asc``."""

    names = [line.strip() for line in path.read_text(encoding="ascii").splitlines()]
    if len(names) != EXPECTED_NAME_COUNT or any(not name for name in names):
        raise ValueError(
            f"names.asc must contain {EXPECTED_NAME_COUNT} non-empty names, got {len(names)}"
        )
    return names


def parse_source(source_dir: Path) -> tuple[dict[str, list[int]], dict[str, np.ndarray]]:
    """Parse and validate quadrant row counts and section breakpoint pairs."""

    counts = read_integer_tokens(source_dir / "quadsidx.asc")
    expected = len(QUADRANTS) * EXPECTED_LATITUDE_ROWS
    if len(counts) != expected:
        raise ValueError(f"quadsidx.asc must contain {expected} counts, got {len(counts)}")

    per_latitude = {
        quadrant: counts[index * 91 : (index + 1) * 91] for index, quadrant in enumerate(QUADRANTS)
    }
    sections: dict[str, np.ndarray] = {}
    for quadrant in QUADRANTS:
        values = read_integer_tokens(source_dir / SECTION_FILES[quadrant])
        if len(values) % 2:
            raise ValueError(f"{SECTION_FILES[quadrant]} has an odd token count")
        pairs = np.asarray(values, dtype=np.uint16).reshape(-1, 2)
        expected_pairs = sum(per_latitude[quadrant])
        if pairs.shape[0] != expected_pairs:
            raise ValueError(
                f"{SECTION_FILES[quadrant]} has {pairs.shape[0]} pairs; expected {expected_pairs}"
            )
        sections[quadrant] = pairs
    return per_latitude, sections


def build_table(source_dir: Path) -> np.ndarray:
    """Build the dense ``uint16[4, 91, 181]`` runtime lookup table."""

    counts, sections = parse_source(source_dir)
    table = np.empty((4, 91, 181), dtype=np.uint16)
    longitudes = np.arange(181, dtype=np.uint16)

    for quadrant_index, quadrant in enumerate(QUADRANTS):
        pairs = sections[quadrant]
        begin = 0
        for latitude, count in enumerate(counts[quadrant]):
            end = begin + count
            row = pairs[begin:end]
            breakpoints = row[:, 0]
            regions = row[:, 1]
            if count < 1 or breakpoints[0] != 0:
                raise ValueError(f"{quadrant} latitude {latitude} does not start at longitude 0")
            if np.any(breakpoints[1:] <= breakpoints[:-1]):
                raise ValueError(f"{quadrant} latitude {latitude} breakpoints are not increasing")
            positions = np.searchsorted(breakpoints, longitudes, side="right") - 1
            table[quadrant_index, latitude, :] = regions[positions]
            begin = end
    if np.any(table == 0):
        raise ValueError("generated table contains region number 0")
    return table


def build_names(source_dir: Path) -> np.ndarray:
    """Build a direct one-based Unicode region-name array."""

    source_names = read_names(source_dir / "names.asc")
    width = max(len(name) for name in source_names)
    names = np.empty(len(source_names) + 1, dtype=f"<U{width}")
    names[0] = ""
    names[1:] = source_names
    return names


def build_assets(source_dir: Path, output_dir: Path) -> None:
    """Validate source data and write deterministic runtime assets and metadata."""

    verify_source_dir(source_dir)
    table = build_table(source_dir)
    names = build_names(source_dir)
    if int(table.max()) >= names.size or np.any(names[np.unique(table)] == ""):
        raise ValueError("generated table references an unknown region name")

    output_dir.mkdir(parents=True, exist_ok=True)
    table_path = output_dir / "fe_table.npy"
    names_path = output_dir / "fe_names.npy"
    np.save(table_path, table, allow_pickle=False)
    np.save(names_path, names, allow_pickle=False)

    metadata = {
        "schema_version": 1,
        "source": {
            "project": "ObsPy",
            "repository": OBSPY_REPOSITORY,
            "revision": OBSPY_REVISION,
            "path": OBSPY_DATA_PATH,
            "license": "LGPL-3.0",
            "files": {name: {"sha256": sha256(source_dir / name)} for name in SOURCE_FILES},
        },
        "assets": {
            "fe_table.npy": {
                "sha256": sha256(table_path),
                "dtype": str(table.dtype),
                "shape": list(table.shape),
            },
            "fe_names.npy": {
                "sha256": sha256(names_path),
                "dtype": str(names.dtype),
                "shape": list(names.shape),
            },
        },
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/feregion/data"),
    )
    args = parser.parse_args()
    build_assets(args.source_dir, args.output_dir)


if __name__ == "__main__":
    main()
