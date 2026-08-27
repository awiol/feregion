# feregion design

| Field | Value |
|---|---|
| Behavioral contract series | `0.1` |
| Status | Implemented alpha design |

## 1. Design result

The runtime uses one dense lookup table with shape `(4, 91, 181)`. Its axes are
quadrant, absolute integer latitude, and absolute integer longitude. The table
stores `uint16` Flinn-Engdahl (FE) region numbers.

The **batch lookup** path validates a numeric `(n, 2)` coordinate array and uses
a vectorized dense-table implementation. It has no Python loop over points. The
scalar path validates two values directly and indexes the same table.

The design retains the dense-table architecture. Prior extensive review found
boundary-contract defects, not a reason to replace the numeric core.

## 2. Behavioral model

A valid coordinate pair is `[longitude, latitude]` in WGS84 degrees.

The lookup procedure is:

1. validate type, finiteness, and range;
2. map exact longitude `-180` to the `+180` lookup behavior;
3. choose a quadrant from coordinate signs;
4. compute `int(abs(longitude))` and `int(abs(latitude))`; and
5. read the dense table at the resulting indices.

Negative zero behaves as zero because sign comparisons use `< 0`.

ObsPy `FlinnEngdahl` at the pinned source revision is the **reference
implementation**. `tests/reference.py` is an independent **source-table
scanner** used for differential verification and performance baselines.

## 3. Runtime data lifecycle

The repository does not version downloaded ObsPy FE source tables.
`tools/fetch_obspy_fe_data.py` fetches the required files from immutable ObsPy
commit `a629e8c021052904b6b8d62699d03f2a3721ae63`, which is the commit for tag
`1.4.2`. Every file must match its pinned SHA-256 value before use.

Downloaded source tables are stored under the ignored `.cache/` directory.
`tools/build_assets.py` generates the version-controlled runtime assets:

- `fe_table.npy`: `uint16[4, 91, 181]`;
- `fe_names.npy`: one-based Unicode packaged region names; and
- `metadata.json`: source identity, hash, name-source, license-status, and
  generated-asset metadata.

The packaged region-name mapping is generated from ObsPy 1.4.2 `names.asc`.
The package does not claim that this mapping is the unique authoritative FE naming
scheme across all historical sources.

ObsPy states that the ObsPy software is licensed under LGPL v3.0. That software
license does not establish the license of the historical FE source tables.
Metadata and third-party notices therefore record the source-data license status
as unresolved. This is provenance information, not legal advice.

## 4. Resource cache and engine ownership

Normal package use has two process-local single-flight caches:

1. `load_packaged_assets()` loads and validates the packaged `.npy` files once;
2. `get_default_lookup()` constructs one default `FlinnEngdahlLookup` instance.

Concurrent first callers wait for the initializing caller and then receive the
same cached objects. Steady-state reads do not take the initialization locks.

Explicit `FlinnEngdahlLookup` construction is a different ownership boundary.
The constructor validates the supplied arrays, copies them once, and marks the
engine-owned copies read-only. Later mutation of caller-owned source arrays
cannot change engine behavior. The copy cost is bounded by the small fixed FE
table and name array.

## 5. Coordinate and adapter validation

The core batch API validates shape and dtype before numeric conversion. String,
object, Boolean, and complex coordinate dtypes are rejected. Finiteness and
range are checked before narrowing a wider floating dtype to `float64`.

The pandas adapter follows the same semantic coordinate-type contract. It:

- requires distinct longitude and latitude selectors;
- requires each selected label to occur exactly once;
- rejects Boolean coordinate columns;
- rejects missing or ambiguous selectors with `DataFrameColumnError`;
- converts each selected numeric Series without forcing `float64`; and
- delegates source-dtype finiteness/range classification to the core batch API.

Output columns are additive. They cannot replace coordinate columns or any
existing input column. Number and name output columns must differ when names
are enabled.

## 6. CSV structured-input contract

CSV processing uses the Python standard library and bounded chunks. It does not
require pandas.

Before row processing, the command validates that:

- the header exists;
- every header field name is unique;
- longitude and latitude selectors are distinct and present; and
- requested output fields do not collide with input or coordinate fields.

Filesystem CSV input is decoded as UTF-8 and parsed with strict CSV syntax.
Unicode decoding failures and `csv.Error` parser failures are converted to
`CsvInputError` at the command boundary. The installed command returns status 2
with a bounded diagnostic rather than leaking a Python traceback.

For every row, the number of fields must exactly match the header width.
Surplus fields and missing fields raise `CsvInputError`. The command does not
silently discard surplus input or synthesize absent fields.

## 7. Atomic filesystem publication

A filesystem CSV destination uses **atomic filesystem publication**, not a
broader storage-transaction guarantee:

1. reject input/output aliasing;
2. open the input;
3. create an exclusive temporary sibling with normal process-umask semantics;
4. validate and process all input into the sibling;
5. if a destination exists, copy its permission bits to the sibling;
6. close the sibling; and
7. publish it with `os.replace()`.

An ordinary processing failure before replacement leaves an existing
destination unchanged and does not publish a new partial destination. The
contract does not claim crash durability, directory fsync, ACL preservation,
owner preservation, or cross-filesystem atomicity.

stdout is a streaming sink. A later failure can leave earlier bytes visible.
The command still returns its failure status and diagnostic.

## 8. GeoJSON derivation

GeoJSON is a derived visualization representation. The utility samples the
centers of the `360 * 180` one-degree cells, resolves FE region numbers, merges
horizontal runs, and dissolves rectangles by region.

The geometry is **area-equivalent one-degree GeoJSON**. It is not an exact
encoding of FE ownership for every coordinate on an integer boundary line.
Ordinary closed polygons share their common boundaries, while FE point lookup
uses directional integer-truncation semantics. Numeric lookup is authoritative
for an exact boundary coordinate.

Each feature records:

- region number;
- packaged region name;
- `boundary_model = "area-equivalent 1-degree cells"`; and
- a boundary-semantics note directing exact point queries to numeric lookup.

The utility creates features only for the 754 region numbers present in the
active cell grid. It does not fabricate geometry for retired IDs 172, 299, or
550.

## 9. Performance design

Routine benchmarks cover in-process scalar, batch, name-conversion, and pandas
interfaces. CLI and GeoJSON timing are excluded because their dominant costs
belong to different subsystems.

A batch performance claim must compare the dense-table candidate and the
source-table scanner on identical deterministic coordinates. Reports record the
environment, workload, repetitions, median duration, throughput, correctness
check, and speedup.

Scalar performance is a review signal. The batch interface remains the
performance-oriented API.

Cross-Python benchmarking is a separate matrix from compatibility testing. Four
lock-backed tox-uv environments run the same standalone benchmark harness on
Python 3.11 through 3.14 and write raw JSON below `.tox/benchmark-results/`. A
report reducer selects eight public-path throughput metrics: three scalar
operations, two batch-number workloads, one batch name-conversion workload, and
two pandas copy workloads. The report records exact Python, NumPy, pandas, and
package versions and normalizes throughput to Python 3.11. Using one lock and one
machine reduces dependency and hardware confounding; recorded versions keep any
remaining environment-marker differences visible.

The proposed mask-only longitude/quadrant kernel remains deferred in this
iteration. Scratch evidence suggested lower temporary allocation and a modest
kernel improvement, but the project will not change the hot path until a
full-public-API and process-level peak-memory comparison confirms a material
benefit.

A Rust backend remains deferred. Current NumPy throughput does not establish a
need for another runtime backend.

## 10. Verification architecture

The repository uses `uv` as the development and build frontend.

GitHub Actions contains:

GitHub Actions resolves a compatible `uv>=0.10,<1` release from repository metadata, validates normal environments against the committed lock, bounds job runtimes, and cancels obsolete runs for the same branch or pull request.

- a Python 3.11, 3.12, 3.13, and 3.14 matrix that fetches the hash-verified pinned FE
  source tables and runs the runtime suite with branch coverage;
- an independent-oracle job that installs ObsPy and executes both source-table
  reproduction and direct ObsPy comparison tests;
- a Python 3.11 lower-bound job that reuses the tox-uv `minimum` environment
  and resolves the lowest declared direct NumPy, pandas, Shapely, pytest, and
  pytest-cov versions; and
- a Python 3.11 quality job that runs Ruff, distribution builds, wheel
  archive inspection, and dependency-isolated wheel verification.

`tools/verify_wheel.py` first inspects the built archive for runtime files,
package data, metadata, extras, the console entry point, and license/provenance
notices. It then creates a fresh uv virtual environment without system site
packages, installs the wheel with dependencies, and exercises Python and CLI
APIs.

The repository uses local pre-commit hooks that execute the synchronized `uv`
development environment. The hooks run Ruff formatting and Ruff linting, then
invoke tox's `local` environment for behavioral tests. This keeps commit-time
tests aligned with the tox test definition without creating independent
hook-specific Python environments.

For local compatibility checks, `tox.toml` defines lock-backed `py311` through
`py314` environments plus a Python 3.11 `lowest-direct` environment. tox provides
environment orchestration; tox-uv delegates interpreter/environment creation and
dependency installation to uv. The minimum environment installs the project and
its `test` extra together with `uv-editable`, so direct NumPy and pandas lower
bounds are co-resolved instead of being installed in separate steps. Hosted
lower-bound CI invokes the same `minimum` environment to prevent local/CI
definition drift.

The repository also contains synchronization and integrity tests for:

- package runtime version versus `pyproject.toml`;
- compatibility extras versus authoritative dependency groups;
- generated runtime asset hashes versus packaged metadata; and
- stable maintained contract filenames and verification traceability.

Named defect regressions retain sensitivity evidence in delivery-side review
records when a predecessor can safely reproduce the defect.

`uv.lock` is not ignored. The repository should commit a resolved lock when the
maintenance environment can generate it. If lock generation is unavailable, the
release verification record must state that limitation instead of treating the
dependency graph as locked.

## 11. Maintained knowledge structure

The repository separates three requirement scopes:

1. product/public behavior;
2. engineering, verification, provenance, and packaging; and
3. repository and source-delivery rules.

The design is recorded in this document. The current quality-assurance document
defines selected quality scenarios, release gates, and maturity conditions. The
decision document records consequential choices and review triggers. A separate
verification-traceability document maps every requirement ID to tests or release
checks. `docs/testing.md` provides stable maintainer procedures.

The maintained contract set uses stable repository paths. Git history records
contract revisions. Delivery manifests, checksum lists, raw benchmark results,
verification logs, and per-iteration review reports remain outside the source
tree.

For maintainer-to-agent handoff, `tools.export_repository` uses Git-tracked paths
as the source boundary but reads their current working-tree bytes. This preserves
tracked local formatting/checking edits without collecting editor settings,
virtual environments, caches, benchmark runs, or other untracked state.
`uv.lock` is excluded explicitly. Non-ignored untracked paths are reported so a
new source file must be staged/committed (or otherwise deliberately handled)
before it can be mistaken for project source.

## 12. Compatibility and residual limits

The numeric FE mapping and public function names follow the declared public
contract. Ambiguous structured input fails instead of silently losing data.
Explicit engine construction copies input arrays to make the immutability
contract real.

The source-data license remains unresolved in project provenance. Release
records must state whether dependency locking, the supported-Python matrix,
lower-bound dependency checks, the direct ObsPy oracle, Ruff, and clean
installation were actually observed. Workflow configuration alone is not a
verification result.
