"""Project-owned contracts for the feregion benchmark system."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

STANDARD_LOAD_SIZES: Final[tuple[int, ...]] = (
    1,
    2,
    5,
    10,
    20,
    50,
    100,
    200,
    500,
    1_000,
    2_000,
    5_000,
    10_000,
    20_000,
    50_000,
    100_000,
    200_000,
    500_000,
    1_000_000,
    2_000_000,
    5_000_000,
    10_000_000,
    20_000_000,
    50_000_000,
)
REFERENCE_LOAD_SIZES: Final[tuple[int, ...]] = (100, 1_000, 10_000, 100_000)
DIAGNOSTIC_LOAD_SIZES: Final[tuple[int, ...]] = (
    1,
    100,
    1_000,
    10_000,
    100_000,
    1_000_000,
)
WORKLOAD_SEED: Final[int] = 20260917
WORKLOAD_VERSION: Final[str] = "coordinates-v1"


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """Describe stable benchmark semantics independently of ASV source identity."""

    case_id: str
    case_version: int
    operation_count: str
    requires_pandas: bool = False
    requires_seismic: bool = False
    requires_obspy: bool = False
    requires_source_oracle: bool = True
    load_parameterized: bool = False
    supported_load_sizes: tuple[int, ...] | None = None
    diagnostic: bool = False
    compatible_version_hashes: tuple[str, ...] = ()

    @property
    def semantic_version_hash(self) -> str:
        """Return an ASV-compatible stable digest for this semantic case version."""

        payload = f"{self.case_id}:{self.case_version}:{WORKLOAD_VERSION}".encode()
        return hashlib.sha256(payload).hexdigest()

    def accepts_asv_version(self, version: str | None) -> bool:
        """Return whether one stored ASV benchmark version maps to this case version."""

        if version is None:
            return False
        return version == self.semantic_version_hash or version in self.compatible_version_hashes


CASES: Final[dict[str, BenchmarkCase]] = {
    case.case_id: case
    for case in (
        BenchmarkCase("lookup_geographic_number", 1, "calls"),
        BenchmarkCase("lookup_geographic_region", 1, "calls"),
        BenchmarkCase("geographic_number_to_name", 1, "calls"),
        BenchmarkCase("lookup_geographic_numbers", 1, "points", load_parameterized=True),
        BenchmarkCase("lookup_seismic_number", 1, "calls", requires_seismic=True),
        BenchmarkCase("lookup_seismic_region", 1, "calls", requires_seismic=True),
        BenchmarkCase(
            "lookup_seismic_numbers",
            1,
            "points",
            requires_seismic=True,
            load_parameterized=True,
        ),
        BenchmarkCase(
            "geographic_numbers_to_seismic_numbers",
            1,
            "points",
            requires_seismic=True,
            load_parameterized=True,
        ),
        BenchmarkCase("geographic_numbers_to_names", 1, "points", load_parameterized=True),
        BenchmarkCase(
            "seismic_numbers_to_names",
            1,
            "points",
            requires_seismic=True,
            load_parameterized=True,
        ),
        BenchmarkCase(
            "pandas_lookup_numbers",
            1,
            "rows",
            requires_pandas=True,
            load_parameterized=True,
        ),
        BenchmarkCase(
            "pandas_lookup_numbers_and_names",
            1,
            "rows",
            requires_pandas=True,
            load_parameterized=True,
        ),
        BenchmarkCase(
            "pandas_lookup_inplace_numbers",
            1,
            "rows",
            requires_pandas=True,
            load_parameterized=True,
            supported_load_sizes=DIAGNOSTIC_LOAD_SIZES,
            diagnostic=True,
        ),
        BenchmarkCase(
            "pandas_lookup_inplace_numbers_and_names",
            1,
            "rows",
            requires_pandas=True,
            load_parameterized=True,
            supported_load_sizes=DIAGNOSTIC_LOAD_SIZES,
            diagnostic=True,
        ),
        BenchmarkCase(
            "pandas_lookup_inplace_seismic_numbers",
            1,
            "rows",
            requires_pandas=True,
            requires_seismic=True,
            load_parameterized=True,
            supported_load_sizes=DIAGNOSTIC_LOAD_SIZES,
            diagnostic=True,
        ),
        BenchmarkCase(
            "internal_split_geographic_numbers",
            1,
            "points",
            load_parameterized=True,
            supported_load_sizes=DIAGNOSTIC_LOAD_SIZES,
            diagnostic=True,
        ),
        BenchmarkCase(
            "internal_split_seismic_numbers",
            1,
            "points",
            requires_seismic=True,
            load_parameterized=True,
            supported_load_sizes=DIAGNOSTIC_LOAD_SIZES,
            diagnostic=True,
        ),
        BenchmarkCase(
            "stack_plus_geographic_numbers",
            1,
            "points",
            load_parameterized=True,
            supported_load_sizes=DIAGNOSTIC_LOAD_SIZES,
            diagnostic=True,
        ),
        BenchmarkCase(
            "obspy_geographic_number",
            1,
            "calls",
            requires_obspy=True,
            diagnostic=True,
        ),
        BenchmarkCase(
            "source_reference_geographic_number",
            1,
            "calls",
            diagnostic=True,
        ),
        BenchmarkCase(
            "source_reference_geographic_numbers",
            1,
            "points",
            load_parameterized=True,
            supported_load_sizes=REFERENCE_LOAD_SIZES,
            diagnostic=True,
        ),
    )
}


def workload_fingerprint(*, size: int, seed: int = WORKLOAD_SEED) -> str:
    """Return the canonical workload-specification fingerprint for one load size."""

    payload = {
        "distribution": "uniform-global-v1",
        "seed": seed,
        "size": size,
        "workload_version": WORKLOAD_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
