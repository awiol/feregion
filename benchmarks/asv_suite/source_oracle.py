"""Independent pinned-source oracle used by authoritative ASV benchmark setup."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import numpy.typing as npt

OBSPY_REVISION = "1.4.2"
SOURCE_SHA256 = {
    "names.asc": "4b827d5f66bf47256fed52bd0bbf265751d0e34e3356477d2bbda1fcca980ce7",
    "nesect.asc": "201316b895c2da2e373dce1f5e20e0bd0df6ce730cf40ad2f607c5f34b5f4728",
    "nwsect.asc": "dcbca0ae4fe2c020d6e9ce5406b40466271e79dcc8785acf285e7fd6046ad29d",
    "quadsidx.asc": "3e3a7553780c2233f11c2ebef014393a7bd32617a353de4e7f1214dd2f68e9e0",
    "sesect.asc": "831256e2c4c2fd5543816a62a7d68840987200bd13bf8633b6ae628fecd739d8",
    "swsect.asc": "f041077c0ea68add8d9d67ace0b3548bf969650c4efdd2ad4dfabb528d28b4bf",
}
_QUADRANTS = ("ne", "nw", "se", "sw")
_FILES = {"ne": "nesect.asc", "nw": "nwsect.asc", "se": "sesect.asc", "sw": "swsect.asc"}
_MAX_ORACLE_SAMPLES = 257


class OracleUnavailable(RuntimeError):
    """Indicate that authoritative benchmark oracle inputs are unavailable or invalid."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def source_dir() -> Path:
    """Return the expected ignored cache directory for pinned ObsPy FE source tables."""

    return _repository_root() / ".cache" / "feregion" / f"obspy-fe-{OBSPY_REVISION}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_dir(path: Path | None = None) -> Path:
    """Verify the pinned source-table cache and return its path."""

    resolved = source_dir() if path is None else path
    for name, expected in SOURCE_SHA256.items():
        item = resolved / name
        if not item.is_file():
            raise OracleUnavailable(
                f"missing pinned FE source file {item}; run "
                "`uv run python -m tools.fetch_obspy_fe_data` before authoritative benchmarks"
            )
        observed = _sha256(item)
        if observed != expected:
            raise OracleUnavailable(
                f"unexpected SHA-256 for pinned FE source file {item}: {observed}"
            )
    return resolved


class SourceReference:
    """Parse pinned FE source tables and perform direct breakpoint lookup."""

    def __init__(self, path: Path) -> None:
        counts = [int(value) for value in (path / "quadsidx.asc").read_text().split()]
        self.counts = {
            quadrant: counts[index * 91 : (index + 1) * 91]
            for index, quadrant in enumerate(_QUADRANTS)
        }
        self.rows: dict[str, list[list[tuple[int, int]]]] = {}
        for quadrant in _QUADRANTS:
            values = [int(value) for value in (path / _FILES[quadrant]).read_text().split()]
            pairs = list(zip(values[0::2], values[1::2], strict=True))
            rows: list[list[tuple[int, int]]] = []
            offset = 0
            for count in self.counts[quadrant]:
                rows.append(pairs[offset : offset + count])
                offset += count
            if offset != len(pairs):
                raise OracleUnavailable(f"invalid source-table row partition for {quadrant}")
            self.rows[quadrant] = rows
        self.names = tuple((path / "names.asc").read_text(encoding="utf-8").splitlines())

    @staticmethod
    def quadrant(longitude: float, latitude: float) -> str:
        if longitude >= 0 and latitude >= 0:
            return "ne"
        if longitude < 0 and latitude >= 0:
            return "nw"
        if longitude >= 0 and latitude < 0:
            return "se"
        return "sw"

    def number(self, longitude: float, latitude: float) -> int:
        if longitude == -180:
            longitude = 180
        quadrant = self.quadrant(longitude, latitude)
        abs_longitude = int(abs(longitude))
        abs_latitude = int(abs(latitude))
        result = None
        for breakpoint, number in self.rows[quadrant][abs_latitude]:
            if breakpoint > abs_longitude:
                break
            result = number
        if result is None:
            raise AssertionError("source oracle did not resolve a region number")
        return result

    def name(self, number: int) -> str:
        return self.names[number - 1]


@lru_cache(maxsize=1)
def source_reference() -> SourceReference:
    """Return the verified process-local pinned-source reference."""

    return SourceReference(verify_source_dir())


@lru_cache(maxsize=1)
def geographic_to_seismic() -> npt.NDArray[np.uint8]:
    """Return the current project-owned geographic-to-seismic oracle crosswalk."""

    path = _repository_root() / "src" / "feregion" / "data" / "fe_seismic_by_geographic.npy"
    if not path.is_file():
        raise OracleUnavailable(f"missing project crosswalk oracle asset: {path}")
    return np.load(path, allow_pickle=False)


@lru_cache(maxsize=1)
def seismic_names() -> npt.NDArray[np.str_]:
    """Return the current project-owned seismic-name oracle array."""

    path = _repository_root() / "src" / "feregion" / "data" / "fe_seismic_names.npy"
    if not path.is_file():
        raise OracleUnavailable(f"missing project seismic-name oracle asset: {path}")
    return np.load(path, allow_pickle=False)


def sample_indices(size: int, *, limit: int = _MAX_ORACLE_SAMPLES) -> npt.NDArray[np.intp]:
    """Return deterministic indices for bounded untimed semantic checking."""

    if size <= 0:
        return np.empty(0, dtype=np.intp)
    if size <= limit:
        return np.arange(size, dtype=np.intp)
    return np.linspace(0, size - 1, num=limit, dtype=np.intp)
