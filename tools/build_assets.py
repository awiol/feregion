"""Generate compact runtime assets from verified Flinn-Engdahl source data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from tools.isc_fe_source import (
    DEFAULT_ISC_SOURCE,
    EXPECTED_SEMANTIC_SHA256,
    ISC_FE_URL,
    RETIRED_GEOGRAPHIC_REGIONS,
    semantic_sha256,
)
from tools.obspy_fe_source import (
    DEFAULT_SOURCE_DIR,
    OBSPY_COMMIT,
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
EXPECTED_SEISMIC_COUNT = 50


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
    """Read the one-based FE geographical-region name sequence from ``names.asc``."""

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
    """Build the dense ``uint16[4, 91, 181]`` geographical lookup table."""

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
    """Build a direct one-based Unicode geographical-region-name array."""

    source_names = read_names(source_dir / "names.asc")
    width = max(len(name) for name in source_names)
    names = np.empty(len(source_names) + 1, dtype=f"<U{width}")
    names[0] = ""
    names[1:] = source_names
    return names


def read_isc_source(path: Path) -> dict[str, object]:
    """Read and semantically verify normalized ISC hierarchy source data."""

    document = json.loads(path.read_text(encoding="utf-8"))
    observed = semantic_sha256(document)
    if observed != EXPECTED_SEMANTIC_SHA256:
        raise ValueError(
            "normalized ISC FE hierarchy has unexpected semantic SHA-256: "
            f"expected {EXPECTED_SEMANTIC_SHA256}, got {observed}"
        )
    return document


def build_seismic_assets(isc_source: Path) -> tuple[np.ndarray, np.ndarray]:
    """Build the geographical-to-seismic crosswalk and seismic-name table."""

    document = read_isc_source(isc_source)
    regions = document["seismic_regions"]
    if not isinstance(regions, list) or len(regions) != EXPECTED_SEISMIC_COUNT:
        raise ValueError("ISC hierarchy must contain exactly 50 seismic regions")

    crosswalk = np.zeros(758, dtype=np.uint8)
    source_names: list[str] = [""]
    for expected_number, region in enumerate(regions, start=1):
        if not isinstance(region, dict) or region.get("number") != expected_number:
            raise ValueError("ISC seismic regions must be ordered 1 through 50")
        name = region.get("name")
        members = region.get("geographic_regions")
        if not isinstance(name, str) or not name:
            raise ValueError(f"ISC seismic region {expected_number} has no name")
        if not isinstance(members, list) or not members:
            raise ValueError(f"ISC seismic region {expected_number} has no geographical members")
        source_names.append(name)
        for geographic_number in members:
            if not isinstance(geographic_number, int) or not 1 <= geographic_number <= 757:
                raise ValueError("ISC hierarchy contains an invalid geographical region number")
            if crosswalk[geographic_number] != 0:
                raise ValueError(
                    f"geographical region {geographic_number} occurs in more "
                    f"than one seismic region"
                )
            crosswalk[geographic_number] = expected_number

    active = np.flatnonzero(crosswalk)
    if (
        active.size != 754
        or set(range(1, 758)) - set(map(int, active)) != RETIRED_GEOGRAPHIC_REGIONS
    ):
        raise ValueError("ISC hierarchy does not cover exactly the 754 active geographical regions")

    width = max(len(name) for name in source_names)
    seismic_names = np.asarray(source_names, dtype=f"<U{width}")
    return crosswalk, seismic_names


def _asset_metadata(path: Path, array: np.ndarray) -> dict[str, object]:
    """Return deterministic metadata for one generated NumPy runtime asset."""

    return {"sha256": sha256(path), "dtype": str(array.dtype), "shape": list(array.shape)}


def build_assets(source_dir: Path, isc_source: Path, output_dir: Path) -> None:
    """Validate source data and write deterministic runtime assets and provenance."""

    verify_source_dir(source_dir)
    table = build_table(source_dir)
    names = build_names(source_dir)
    seismic_by_geographic, seismic_names = build_seismic_assets(isc_source)
    if int(table.max()) >= names.size or np.any(names[np.unique(table)] == ""):
        raise ValueError("generated table references an unknown geographical-region name")
    if np.any(seismic_by_geographic[np.unique(table)] == 0):
        raise ValueError("generated crosswalk omits an active geographical region")

    output_dir.mkdir(parents=True, exist_ok=True)
    arrays = {
        "fe_table.npy": table,
        "fe_names.npy": names,
        "fe_seismic_by_geographic.npy": seismic_by_geographic,
        "fe_seismic_names.npy": seismic_names,
    }
    for filename, array in arrays.items():
        np.save(output_dir / filename, array, allow_pickle=False)

    metadata = {
        "schema_version": 3,
        "scheme": {"name": "Flinn-Engdahl", "structural_revision": "1995"},
        "sources": {
            "obspy-fe-data": {
                "project": "ObsPy",
                "repository": OBSPY_REPOSITORY,
                "revision": OBSPY_REVISION,
                "commit": OBSPY_COMMIT,
                "path": OBSPY_DATA_PATH,
                "roles": ["geographical-boundaries", "geographical-names"],
                "upstream_project_license": "LGPL-3.0",
                "source_data_license_status": "unresolved",
                "region_name_source": "names.asc",
                "files": {name: {"sha256": sha256(source_dir / name)} for name in SOURCE_FILES},
            },
            "young-1996": {
                "title": "The Flinn-Engdahl Regionalisation Scheme: The 1995 revision",
                "doi": "10.1016/0031-9201(96)03141-X",
                "publication_year": 1996,
                "role": "normative-structural-revision",
                "source_data_license_status": "unresolved",
            },
            "isc-fe-standard": {
                "project": "International Seismological Centre",
                "url": ISC_FE_URL,
                "roles": ["seismic-membership", "seismic-names"],
                "normalized_semantic_sha256": EXPECTED_SEMANTIC_SHA256,
                "source_data_license_status": "unresolved",
            },
        },
        "assets": {
            "fe_table.npy": {
                **_asset_metadata(output_dir / "fe_table.npy", table),
                "derived_from": ["obspy-fe-data"],
            },
            "fe_names.npy": {
                **_asset_metadata(output_dir / "fe_names.npy", names),
                "derived_from": ["obspy-fe-data"],
            },
            "fe_seismic_by_geographic.npy": {
                **_asset_metadata(
                    output_dir / "fe_seismic_by_geographic.npy", seismic_by_geographic
                ),
                "derived_from": ["young-1996", "isc-fe-standard"],
            },
            "fe_seismic_names.npy": {
                **_asset_metadata(output_dir / "fe_seismic_names.npy", seismic_names),
                "derived_from": ["young-1996", "isc-fe-standard"],
            },
        },
        "runtime": {
            "network_required": False,
            "source_retrieval_required_for_normal_use": False,
        },
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Run the source-to-runtime asset generator."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--isc-source", type=Path, default=DEFAULT_ISC_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=Path("src/feregion/data"))
    args = parser.parse_args()
    build_assets(args.source_dir, args.isc_source, args.output_dir)


if __name__ == "__main__":
    main()
