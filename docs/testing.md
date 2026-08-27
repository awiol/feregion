# feregion testing and verification

## Purpose

The test system provides evidence for public behavior, generated data,
structured-input preservation, failure semantics, packaging, and
performance-sensitive lookup paths. Coverage is an omission signal; it is not
proof of correctness or suitability.

## Local commands

Prepare the development environment and run the normal checks:

```bash
uv sync
uv run ruff check .
uv run pytest -q
uv run pytest -q --cov=feregion --cov-branch --cov-report=term-missing
```

Build distributions with:

```bash
uv build
```

Verify a wheel in a dependency-isolated environment when registry access is
available:

```bash
uv run python -m tools.verify_wheel dist/feregion-*.whl --python 3.11
```

The wheel verifier inspects package contents, metadata, extras, console entry
points, and license/provenance notices before installation. It then creates a
new uv virtual environment without system site packages and installs wheel
dependencies into that environment.

## Test layers

1. Core tests use synthetic tables and names to isolate coordinate behavior.
2. Package-resource tests verify generated asset structure, packaged names,
   provenance metadata, and known FE results.
3. Source-reproduction tests compare packaged assets with the hash-verified
   pinned ObsPy source tables through an independent source-table scanner.
4. Optional ObsPy oracle tests compare package behavior with the reference
   implementation when ObsPy is installed.
5. pandas and CSV tests verify selector identity, source-dtype validation
   parity, structured-input preservation, UTF-8/CSV parser failures, additive
   output, and publication behavior.
6. GeoJSON tests verify area-cell coverage and the explicit boundary limitation.
7. Repository metadata tests detect version, dependency, contract-file, CI
   matrix, and traceability drift.
8. Benchmark harnesses measure scalar, batch, name-conversion, and pandas
   interfaces. Routine benchmarks exclude CLI and GeoJSON.

## Upstream source-data checks

Fetch source data before source-reproduction tests:

```bash
uv run python -m tools.fetch_obspy_fe_data
```

The fetch tool resolves the required files at immutable ObsPy commit
`a629e8c021052904b6b8d62699d03f2a3721ae63` for tag `1.4.2`. It verifies each
file against its pinned SHA-256 value before publication to the ignored cache.

Tests that require the source cache skip with an acquisition instruction when
it is absent. Release verification must run these tests with the cache present.

## Structured-input checks

CSV tests cover:

- input/output path aliases;
- duplicate headers;
- surplus and missing row fields;
- invalid UTF-8 and malformed CSV syntax;
- distinct coordinate selectors;
- output-column collisions;
- preservation of existing files after early and late failures;
- existing destination permission bits;
- new-file process-umask behavior; and
- partial stdout behavior after a late failure.

pandas tests cover duplicate coordinate labels, identical coordinate selectors,
Boolean coordinate dtypes, wide finite out-of-range values, output collisions,
missing values, and copy versus in-place behavior.

For a corrected defect, preserve sensitivity evidence: execute the targeted
regression against the unchanged faulty baseline when practical, or record a
credible alternative sensitivity demonstration. A passing test that also passed
before the fix does not establish regression protection for that defect.

## Locked CI environment

CI accepts `uv>=0.10,<1`; `setup-uv` resolves a compatible release from that
range. Normal matrix, oracle, and quality jobs use the committed
`uv.lock` with `uv sync --locked` and `uv run --locked`. The minimum-dependency
job intentionally creates a separate environment at declared direct lower bounds.
Workflow jobs have explicit timeouts, and workflow concurrency cancels obsolete
runs for the same pull request or branch.

## CI authority

`.github/workflows/ci.yml` is the intended automated authority for:

- Python 3.11, 3.12, 3.13, and 3.14 test execution;
- branch coverage;
- source-reproduction checks;
- a direct installed-ObsPy oracle job;
- a Python 3.11 lower-bound dependency job;
- Ruff;
- distribution builds; and
- dependency-isolated wheel verification.

A local result must not be reported as a CI result. A configured check that
could not run must remain an explicit verification limitation.

## Performance evidence

Before timing a candidate, benchmark code compares its output with the
source-table scanner. Direct batch comparisons use identical deterministic
coordinates for candidate and baseline.

Reports retain workload, environment, repetitions, median duration, throughput,
and speedup. Generated benchmark JSON and human-readable reports are delivery
artifacts and should not be committed to the source repository.

## Commit-time checks

Install the development environment and hooks once:

```bash
uv sync --locked --group dev
uv run pre-commit install
```

Run the complete commit-time pipeline manually with:

```bash
uv run pre-commit run --all-files
```

The hooks use the synchronized project environment. Ruff formatting can modify
Python files; review and re-stage those changes before committing.
