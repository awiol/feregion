# feregion testing and verification

## Purpose

The test suite provides evidence for public behavior, generated data, failure
semantics, packaging, and performance-sensitive lookup paths. Coverage is an
omission check, not proof of correctness.

## Standard commands

Prepare the development environment and run the normal checks:

```bash
uv sync
uv run ruff check .
uv run mypy src/feregion tools benchmarks
uv run pytest -q
uv run pytest -q --cov=feregion --cov-branch --cov-report=term-missing
```

Build distributable artifacts with:

```bash
uv build
```

## Test layers

1. Core tests use synthetic tables and names. They isolate coordinate behavior
   from package-resource I/O.
2. Package-resource tests verify generated asset structure, immutability, and
   known FE results.
3. Source-reproduction tests compare packaged assets with the pinned ObsPy
   source tables through an independent breakpoint scan.
4. Optional ObsPy oracle tests compare package behavior with ObsPy when it is
   installed.
5. pandas, CLI, and GeoJSON tests verify their public boundaries and failure
   behavior.
6. Benchmark harnesses measure scalar, NumPy, name-conversion, and pandas
   interfaces. Routine benchmarks exclude CLI and GeoJSON.

## Upstream source-data tests

Downloaded ObsPy source tables are not repository source. Fetch and verify them
before source-reproduction tests or benchmarks that use the direct source
reference:

```bash
uv run python -m tools.fetch_obspy_fe_data
```

The command fetches pinned ObsPy revision `1.4.2` into the ignored local cache
and verifies the expected SHA-256 digest for every required file. Tests that
need these files skip with an acquisition instruction when the cache is absent.
Release verification must run them with the verified cache present.

## Required behavior classes

The suite covers normal input, coordinate limits, quadrant selection,
fractional truncation, malformed shape, unsupported dtype, NaN, infinity,
out-of-range values, invalid region numbers, DataFrame and CSV schema failures,
CSV transaction failures, concurrent first initialization, extended floating
range classification, source regeneration, and installed command behavior.

Tests for package-owned failures assert the exact exception class. Parameterized
cases share one setup, contract, and failure interpretation.

## Performance evidence

Before timing a candidate, benchmark code checks its output against a semantic
oracle. Direct batch comparisons time the vectorized lookup and verified-source
breakpoint scan on identical deterministic coordinates. Reports retain the
workload, environment, repetitions, median timing, throughput, and speedup.

Performance reports and raw benchmark JSON are delivery artifacts. Do not
commit them to the source repository by default.
