# feregion engineering requirements

| Field | Value |
|---|---|
| Requirements document version | `0.1.1a2` |
| Implementation target | `0.1.1a2` |
| Document date | `2026-08-23` |
| Current filename | `feregion-engineering-requirements-v0.1.1a2-2026-08-23.md` |
| Status | Implemented alpha engineering contract |

This document uses the normative profile defined by `feregion-requirements-v0.1.1a2-2026-08-23.md`.

## Runtime data and dependency behavior

**REQ-DATA-001** — ObsPy must not be a runtime dependency.

**REQ-DATA-002** — The distributed package must contain generated lookup data
that is sufficient for all normal FE lookup operations.

**REQ-DATA-003** — The repository must contain a deterministic tool that can
regenerate runtime assets from hash-verified pinned FE source tables. Downloaded upstream
source tables must not be version-controlled project source.

**REQ-DATA-004** — Source and generated asset provenance must include SHA-256
values, the ObsPy release tag, the immutable ObsPy commit, the source-table
path, and the packaged-region-name source.

**REQ-DATA-005** — Normal package use must read and validate the generated
asset pair no more than once per Python process, including concurrent first
use.

**REQ-DATA-006** — Normal package use must construct no more than one default
lookup engine per Python process, including concurrent first use. Concurrent
first callers must receive the same default-engine instance.

**REQ-DATA-007** — Generated data arrays used by the default engine must be
read-only.

**REQ-DATA-008** — Repository tooling must fetch the required ObsPy FE source
tables from a pinned upstream revision into an ignored local cache. It must
verify each file against the expected SHA-256 digest before source-reference
tests or asset generation use the file.

**REQ-DATA-009** — Generated runtime assets must remain version-controlled
because installed packages require them and normal runtime lookup must not
require network access or the upstream source tables.

**REQ-DATA-010** — The packaged region-name mapping must be generated from
ObsPy 1.4.2 `names.asc`. Documentation must call these values packaged region
names and must not claim that they are the unique authoritative names across all FE
sources.

**REQ-DATA-011** — Provenance metadata and third-party notices must distinguish
the ObsPy software license from the historical FE source-table license. If the
source-table license is not established, the project must record that status as
unresolved instead of inferring a license from the ObsPy repository license.

**REQ-NP-005** — The vectorized dense-table implementation must use compact
integer indices suitable for the fixed FE grid and must store region numbers as
`uint16`. This is an engineering constraint, not a requirement on caller input
storage.

## Tests and benchmarks

**REQ-TEST-001** — pytest tests must cover normal, boundary, invalid, and
failure behavior for each material public interface.

**REQ-TEST-002** — Each test must express one coherent behavioral claim. Cases
with different contracts or failure interpretations must use separate tests.

**REQ-TEST-003** — Parameterized cases must have stable diagnostic IDs when the
case identity is material.

**REQ-TEST-004** — Tests for package exceptions must assert the exact exception
class.

**REQ-TEST-005** — Tests must cover all four quadrants, coordinate limits,
negative zero, `-180` normalization, fractional truncation, empty arrays,
invalid shape, invalid dtype, NaN, infinity, and out-of-range values.

**REQ-TEST-006** — Integration tests must verify generated assets against the
hash-verified pinned upstream source tables after a maintainer fetches them. A
development-only test must compare results with ObsPy when ObsPy is installed.

**REQ-TEST-007** — Tests must cover synchronized concurrent first use of both
the packaged asset cache and default-engine cache.

**REQ-TEST-008** — Tests must cover CSV path alias rejection, preservation of
an existing destination after malformed input, preservation after a later
chunk fails, permission-mode behavior, and the documented non-atomic stdout
behavior.

**REQ-TEST-009** — Tests must cover pandas and CSV output-column collisions,
including identical number/name columns, coordinate-column collisions, and
pre-existing unrelated columns.

**REQ-TEST-010** — On platforms where `longdouble` has a wider finite range
than `float64`, tests must verify that a wide finite out-of-range value raises
`CoordinateRangeError` without narrowing it first.

**REQ-TEST-011** — Source-reproduction tests must give a clear acquisition
instruction when the local upstream-data cache is absent. Release verification
must run those tests with the hash-verified pinned source data present.

**REQ-TEST-012** — Regression tests must cover duplicate CSV headers, CSV row
width mismatch, distinct coordinate selectors, duplicate pandas coordinate
labels, pandas Boolean coordinates, explicit-engine ownership, packaged name
authority, and GeoJSON boundary metadata.

**REQ-TEST-013** — Repository tests must detect drift between the runtime
version and `pyproject.toml`, between retained compatibility extras and
authoritative dependency groups, and between the current contract filenames and
the implementation version.

**REQ-PERF-001** — The repository must contain automated benchmarks for the
implemented in-process lookup interfaces: scalar number lookup, scalar region
lookup, scalar number-to-name conversion, batch number lookup, batch
region-number-to-name conversion, and the optional pandas adapter with and without
names. CLI and GeoJSON operations are excluded from the routine lookup
benchmark suite.

**REQ-PERF-002** — A performance claim must record workload, environment,
baseline, candidate, repeated measurements, and correctness checks. For batch
performance, the same coordinate workload must be measured directly with the
candidate and source-table scanner baseline. The report must include median
timing, throughput, and candidate speedup in one comparison table.

**REQ-PERF-003** — Benchmark tooling must remain repository-side development
tooling rather than public runtime API. The project must provide a compatible
`benchmark` optional dependency and a `uv` benchmark dependency group. The
source distribution and source bundle must include the benchmark harnesses.

**REQ-PERF-004** — Scalar lookup performance must be compared with the ObsPy
reference implementation when ObsPy is available and with the source-table scanner
otherwise. Scalar performance is a review signal, not a throughput SLA. A
material scalar regression must not justify changes that complicate the batch
hot path without corresponding evidence.

## Packaging, development environment, and license

**REQ-PKG-001** — The package must require Python 3.11 or newer. Automated
repository verification must cover Python 3.11, 3.12, and 3.13. Newer Python
versions are permitted by package metadata but are not verified by this matrix
until the matrix is extended.

**REQ-PKG-002** — NumPy must be the only mandatory third-party runtime
dependency.

**REQ-PKG-003** — pandas and Shapely must be optional dependencies.

**REQ-PKG-004** — The source tree must include the project license and
third-party provenance notices. Those notices must not assign the ObsPy
software license to historical FE source tables unless evidence establishes
that license.

**REQ-PKG-005** — Repository development must use `uv` as the authoritative
environment, dependency, execution, and build frontend. Development-only
dependencies must be declared with dependency groups in `pyproject.toml`.

**REQ-PKG-006** — The repository must not require a Makefile for authoritative
development operations when the equivalent `uv` command is short and explicit.
Authoritative commands must be documented in `README.md` and `docs/testing.md`.

**REQ-PKG-007** — The previously published `test`, `dev`, and `benchmark`
optional dependency extras must remain available for compatibility in this
patch release. Repository development must use dependency groups as the
authoritative dependency source for `uv` workflows.

**REQ-PKG-008** — GitHub Actions CI must run the full test suite with branch
coverage on Python 3.11, 3.12, and 3.13. A separate quality job must run Ruff,
mypy, distribution builds, and dependency-isolated wheel verification.

**REQ-PKG-009** — The repository must contain automated synchronization checks
for the package version and duplicated compatibility dependency declarations.

**REQ-PKG-010** — `uv.lock` must not be ignored. The project should generate
and commit it when dependency resolution is available in the maintenance
environment. Until then, verification records must state that the development
dependency graph is not locked.
