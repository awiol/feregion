"""Project-owned contracts for the feregion benchmark system."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

STANDARD_LOAD_SIZES: Final[tuple[int, ...]] = (1, 100, 1_000, 10_000, 100_000, 1_000_000)
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
    load_parameterized: bool = False

    @property
    def semantic_version_hash(self) -> str:
        """Return an ASV-compatible stable digest for this semantic case version."""

        payload = f"{self.case_id}:{self.case_version}:{WORKLOAD_VERSION}".encode()
        return hashlib.sha256(payload).hexdigest()


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
