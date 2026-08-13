# feregion requirements

| Field | Value |
|---|---|
| Requirements document version | `0.1.1a1` |
| Behavioral contract series | `0.1` |
| Implementation target | `0.1.1a1` |
| Document date | `2026-08-13` |
| Canonical filename | `feregion-requirements-v0.1.1a1-2026-08-13.md` |
| Status | Implemented alpha contract |

## 1. Purpose and terms

The package shall map WGS84 longitude/latitude coordinates to Flinn-Engdahl
(FE) geographical region numbers. A **coordinate pair** is ordered as
`[longitude, latitude]`. A **region number** is the positive integer FE
identifier. A **region name** is the canonical name associated with a region
number.

## 2. Reference behavior

**REQ-FE-001** — For each valid finite coordinate pair, the default lookup shall
return the same region number as the ObsPy FE reference implementation and the
same source-data revision used to generate the package assets.

**REQ-FE-002** — Longitude shall be in `[-180, 180]` degrees. Latitude shall be
in `[-90, 90]` degrees.

**REQ-FE-003** — Longitude `-180` shall have the same lookup behavior as
longitude `+180`.

**REQ-FE-004** — Lookup shall select one of four quadrants from coordinate
signs, then use the integer part of each absolute coordinate. Negative zero
shall behave as zero.

## 3. Scalar interface

**REQ-API-001** — The package shall provide a scalar function that returns one
region number from one longitude and latitude.

**REQ-API-002** — The package shall provide a scalar function that returns a
`Region` value with the region number and name.

**REQ-API-003** — `Region` shall be immutable and slotted.

**REQ-API-004** — The package shall provide a scalar region-number-to-name
function.

**REQ-API-005** — Scalar coordinate lookup shall preserve the same coordinate
validation and FE mapping semantics as batch lookup. Scalar lookup is a
convenience interface. Batch lookup is the performance-oriented interface.

## 4. NumPy interface

**REQ-NP-001** — Array lookup shall accept a numeric two-dimensional input with
shape `(n, 2)`. Column 0 shall contain longitude. Column 1 shall contain
latitude.

**REQ-NP-002** — Array lookup shall return one-dimensional `uint16` region
numbers with shape `(n,)`.

**REQ-NP-003** — Array lookup shall not return region names.

**REQ-NP-004** — A separate array function shall convert integer region numbers
to a same-shape Unicode name array.

**REQ-NP-005** — Lookup shall normalize absolute integer longitude and latitude
to `uint8` indices. It shall store region numbers as `uint16`.

**REQ-NP-006** — Array lookup shall not modify caller-owned coordinate data.

**REQ-NP-007** — An empty input with shape `(0, 2)` shall return an empty
`uint16` result.

## 5. pandas interface

**REQ-PD-001** — The optional pandas adapter shall accept configurable longitude
and latitude column names.

**REQ-PD-002** — The pandas adapter shall add a region-number column.

**REQ-PD-003** — The pandas adapter shall add a region-name column only when the
caller requests names.

**REQ-PD-004** — The pandas adapter shall return a copy by default and shall
support an explicit in-place mode.

**REQ-PD-005** — pandas output columns shall be additive. A requested output
column shall not replace a coordinate column or any existing input column. When
names are enabled, the number and name output columns shall be different.
Invalid output schemas shall raise `DataFrameColumnError` before caller data is
modified.

## 6. Errors and invalid input

**REQ-ERR-001** — Public package failures shall use package-specific exception
classes where the package owns the failure semantics.

**REQ-ERR-002** — Invalid coordinate shape, coordinate type, non-finite value,
and out-of-range value shall have distinct exception classes.

**REQ-ERR-003** — Unknown or invalid region numbers shall raise
`RegionNumberError`.

**REQ-ERR-004** — Missing pandas coordinate columns shall raise
`DataFrameColumnError`. A non-DataFrame input shall raise `DataFrameTypeError`.
A missing optional pandas installation shall raise `PandasDependencyError`.

**REQ-ERR-005** — The array API shall reject string, object, Boolean, and complex
coordinate dtypes instead of silently coercing them.

**REQ-ERR-006** — For supported floating dtypes, validation shall classify
finiteness and range in the source dtype before narrowing to `float64`. A value
that is finite in its source dtype but outside the coordinate range shall raise
`CoordinateRangeError`, not `CoordinateValueError`, and validation shall not
emit a narrowing-overflow warning before that classification.

## 7. Runtime data and dependency behavior

**REQ-DATA-001** — ObsPy shall not be a runtime dependency.

**REQ-DATA-002** — The distributed package shall contain generated lookup data
that is sufficient for all normal FE lookup operations.

**REQ-DATA-003** — The repository shall contain a deterministic tool that can
regenerate runtime assets from verified FE source tables. Downloaded upstream
source tables shall not be version-controlled project source.

**REQ-DATA-004** — Source and generated asset provenance shall include SHA-256
values and the pinned ObsPy source revision.

**REQ-DATA-005** — Normal package use shall read and validate the generated
asset pair no more than once per Python process, including concurrent first
use.

**REQ-DATA-006** — Normal package use shall construct no more than one default
lookup engine per Python process, including concurrent first use. Concurrent
first callers shall receive the same default-engine instance.

**REQ-DATA-007** — Generated data arrays used by the default engine shall be
read-only.

**REQ-DATA-008** — Repository tooling shall fetch the required ObsPy FE source
tables from a pinned upstream revision into an ignored local cache. It shall
verify each file against the expected SHA-256 digest before source-reference
tests or asset generation use the file.

**REQ-DATA-009** — Generated runtime assets shall remain version-controlled
because installed packages require them and normal runtime lookup shall not
require network access or the upstream source tables.

## 8. Command-line interface

**REQ-CLI-001** — The package shall install the `fe-region` command.

**REQ-CLI-002** — The command shall support one longitude/latitude pair.

**REQ-CLI-003** — The command shall support CSV input with configurable
coordinate column names.

**REQ-CLI-004** — CSV processing shall use bounded chunks and vectorized lookup.
It shall not require pandas.

**REQ-CLI-005** — CSV output shall contain region numbers and shall optionally
contain region names.

**REQ-CLI-006** — When input and output are filesystem paths, the CSV command
shall reject paths that identify the same file before opening the destination
for writing.

**REQ-CLI-007** — A filesystem CSV destination shall be transactional. The
command shall write to a temporary sibling and atomically replace the requested
destination only after all input has been processed successfully. Header,
conversion, lookup, or later-chunk failure shall leave an existing destination
unchanged and shall not publish a new partial destination.

**REQ-CLI-008** — stdout is a streaming destination and is not transactional. If
a later row fails, rows already written to stdout may remain visible. The
command shall still return the normal failure status and diagnostic.

**REQ-CLI-009** — CSV output columns shall be additive. A requested output
column shall not replace a coordinate column or any existing input field. When
names are enabled, the number and name output columns shall be different.
Invalid output schemas shall fail before an output header is committed to a
filesystem destination.

## 9. GeoJSON feature

**REQ-GEO-001** — The optional GeoJSON utility shall create one feature for each
of the 754 active geographical regions present in the global one-degree lookup
grid. Retired region numbers 172, 299, and 550 shall not receive fabricated
polygons.

**REQ-GEO-002** — Each feature shall contain the region number and name.

**REQ-GEO-003** — GeoJSON geometry shall represent the union of
lookup-equivalent one-degree cells. The package shall not describe this derived
geometry as an independent authoritative FE vector boundary source.

**REQ-GEO-004** — GeoJSON generation may require an optional geometry
dependency. Core lookup shall not require that dependency.

## 10. Tests and benchmarks

**REQ-TEST-001** — pytest tests shall cover normal, boundary, invalid, and
failure behavior for each material public interface.

**REQ-TEST-002** — Each test shall express one coherent behavioral claim. Cases
with different contracts or failure interpretations shall use separate tests.

**REQ-TEST-003** — Parameterized cases shall have stable diagnostic IDs when the
case identity is material.

**REQ-TEST-004** — Tests for package exceptions shall assert the exact exception
class.

**REQ-TEST-005** — Tests shall cover all four quadrants, coordinate limits,
negative zero, `-180` normalization, fractional truncation, empty arrays,
invalid shape, invalid dtype, NaN, infinity, and out-of-range values.

**REQ-TEST-006** — Integration tests shall verify generated assets against the
verified upstream source tables after a maintainer fetches them. A
development-only test shall compare results with ObsPy when ObsPy is installed.

**REQ-TEST-007** — Tests shall cover synchronized concurrent first use of both
the packaged asset cache and default-engine cache.

**REQ-TEST-008** — Tests shall cover CSV path alias rejection, preservation of
an existing destination after malformed input, preservation after a later
chunk fails, and the documented non-transactional stdout behavior.

**REQ-TEST-009** — Tests shall cover pandas and CSV output-column collisions,
including identical number/name columns, coordinate-column collisions, and
pre-existing unrelated columns.

**REQ-TEST-010** — On platforms where `longdouble` has a wider finite range
than `float64`, tests shall verify that a wide finite out-of-range value raises
`CoordinateRangeError` without narrowing it first.

**REQ-TEST-011** — Source-reproduction tests shall give a clear acquisition
instruction when the local upstream-data cache is absent. Release verification
shall run those tests with the verified pinned source data present.

**REQ-PERF-001** — The repository shall contain automated benchmarks for the
implemented in-process lookup interfaces: scalar number lookup, scalar region
lookup, scalar number-to-name conversion, vectorized number lookup, vectorized
number-to-name conversion, and the optional pandas adapter with and without
names. CLI and GeoJSON operations are excluded from the routine lookup
benchmark suite.

**REQ-PERF-002** — A performance claim shall record workload, environment,
baseline, candidate, repeated measurements, and correctness checks. For batch
performance, the same coordinate workload shall be measured directly with the
candidate and verified source-table baseline. The report shall include median
timing, throughput, and candidate speedup in one comparison table.

**REQ-PERF-003** — Benchmark tooling shall remain repository-side development
tooling rather than public runtime API. The project shall provide a compatible
`benchmark` optional dependency and a `uv` benchmark dependency group. The
source distribution and source bundle shall include the benchmark harnesses.

**REQ-PERF-004** — Scalar lookup performance shall be compared with the ObsPy
reference when ObsPy is available and with the verified source-table reference
otherwise. Scalar performance is a review signal, not a throughput SLA. A
material scalar regression shall not justify changes that complicate the batch
hot path without corresponding evidence.

## 11. Packaging and license

**REQ-PKG-001** — The package shall support Python 3.11 or newer.

**REQ-PKG-002** — NumPy shall be the only mandatory third-party runtime
dependency.

**REQ-PKG-003** — pandas and Shapely shall be optional dependencies.

**REQ-PKG-004** — The source tree shall include license and third-party notices
for generated assets derived from ObsPy-distributed source data.

**REQ-PKG-005** — Repository development shall use `uv` as the canonical
environment, dependency, execution, and build frontend. Development-only
dependencies shall be declared with dependency groups in `pyproject.toml`.

**REQ-PKG-006** — The repository shall not require a Makefile for canonical
development operations when the equivalent `uv` command is short and explicit.
Canonical commands shall be documented in `README.md` and `docs/testing.md`.

**REQ-PKG-007** — The previously published `test`, `dev`, and `benchmark`
optional dependency extras shall remain available for compatibility in this
patch release. Repository development shall use dependency groups as the
canonical dependency source for `uv` workflows.

## 12. Repository and delivery boundary

**REQ-REPO-001** — The source archive shall use one stable internal
`feregion/` repository root. Project version and delivery date shall appear in
outer delivery filenames, not in that root name.

**REQ-REPO-002** — Requirements and design documents are versioned project
artifacts. Their filenames shall contain project version and UTC date. For this
iteration they are:

- `docs/feregion-requirements-v0.1.1a1-2026-08-13.md`;
- `docs/feregion-design-v0.1.1a1-2026-08-13.md`.

A new iteration shall intentionally rename these two files and update repository
references in the same change. This is an explicit project naming policy for
these documents.

**REQ-REPO-003** — Benchmark harnesses shall remain source-controlled developer
tooling. Generated benchmark reports, raw benchmark result files, coverage
reports, and per-iteration review reports shall remain outside the repository
source tree unless a later project policy explicitly makes one of those
artifacts product source.

**REQ-REPO-004** — A delivered full-source archive shall exclude
version-control internals, caches, bytecode, local coverage state, build
products, and prior delivery containers.

**REQ-REPO-005** — Repository verification commands shall not hard-code a
pre-release-specific distribution filename when project metadata or `uv build`
can determine it.

**REQ-REPO-006** — `.gitignore` shall cover local environments, Python/tool
caches, coverage output, benchmark output, build products, and retrieved
upstream source data. It shall not ignore requirements, design documents,
generated runtime assets, tests, project metadata, or a future `uv.lock`.

**REQ-REPO-007** — The repository shall contain only the current requirements
and design iteration. A new delivery shall rename those two files, update their
version/date metadata, remove the superseded filenames, and update all internal
references in the same change.

## 13. Iterative delivery contract

**REQ-DEL-001** — Each iterative source delivery shall provide a complete
versioned source archive, a versioned delivery manifest, and a versioned SHA-256
checksum list. When the exact prior delivered source is available, it shall also
provide an incremental Git patch from that exact baseline.

**REQ-DEL-002** — The delivery manifest shall record baseline identity, target
version, patch status, source/archive hashes, generation provenance, review
state, approval state, verification state, exclusions, and material
limitations. Review, approval, and verification shall remain separate from the
alpha/beta/rc maturity identifier.

**REQ-DEL-003** — Generated benchmark results, verification logs, and
per-iteration review evidence shall be delivery-side artifacts, not repository
source. When four or more related evidence files are delivered, they shall be
bundled with an index.

**REQ-DEL-004** — Final delivery hashes shall be calculated after the artifacts
are complete. The patch shall be checked against the exact baseline and shall
reconstruct the target source tree byte-for-byte except for explicitly recorded
metadata exclusions.

## 14. Non-goals

**NON-GOAL-001** — A Rust extension is not part of this implementation. Revisit
Rust only after the NumPy implementation has reproducible benchmark evidence.

**NON-GOAL-002** — This package does not redefine FE regions or claim a more
precise boundary model than the verified FE source tables provide.

**NON-GOAL-003** — The package does not guarantee rollback of bytes already
written to stdout or another caller-owned streaming sink.
