# feregion design

| Field | Value |
|---|---|
| Behavioral contract series | `0.2` |
| Status | Implemented alpha design |

## 1. Design result

The runtime keeps one dense geographical lookup table with shape
`(4, 91, 181)`. Its axes are quadrant, absolute integer latitude, and absolute
integer longitude. The table stores `uint16` FE geographical-region numbers.
A separate one-based `uint8[758]` crosswalk maps each active geographical
identifier to one of 50 seismic regions. Seismic coordinate lookup therefore
reuses the geographical lookup result; it does not duplicate the coordinate
grid in a second dense table.

The **batch lookup** path validates a numeric `(n, 2)` coordinate array and uses
a vectorized dense-table implementation. It has no Python loop over points. The
scalar path validates two values directly and indexes the same table. Explicit
geographical and seismic APIs are canonical. The pre-existing generic API
remains a geographical compatibility surface.

The design retains the dense-table geographical architecture and adds the
small hierarchy crosswalk as a distinct data relation.

## 2. Behavioral model

A valid coordinate pair is `[longitude, latitude]`. By package convention, values are interpreted as WGS84 geographic degrees. The package does not perform CRS transformation, and this convention is separate from the historical FE degree-grid definition.

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

### 2.1 Hierarchy model

The supported structural definition is the 1995 FE revision published by Young
et al. in 1996. It contains 50 seismic regions and 754 active geographical
regions. Geographical identifiers 172, 299, and 550 are retired storage-range
holes.

The runtime relation is:

```text
coordinate -> geographical region -> seismic region
```

`lookup_seismic_number()` and `lookup_seismic_numbers()` perform the same
coordinate validation as geographical lookup and then index the packaged
crosswalk. `geographic_to_seismic_number()` and its vector form expose the
hierarchy directly without repeating coordinate lookup.


## 3. Runtime data lifecycle

Runtime assets are processed repository artifacts. Normal installed use does
not contact ObsPy, ISC, USGS, or another remote service.

Repository retrieval paths are separate from runtime use:

- `tools/fetch_obspy_fe_data.py` downloads the pinned ObsPy geographical source
  files from commit `a629e8c021052904b6b8d62699d03f2a3721ae63` and verifies
  their byte-level SHA-256 values;
- `tools/fetch_isc_fe_regions.py` downloads the ISC FE standards page, extracts
  the 50 seismic names and active geographical memberships, validates complete
  hierarchy coverage, and verifies a normalized semantic SHA-256; and
- `tools/build_assets.py` consumes the retrieved source forms and produces the
  runtime representation.

Downloaded source material remains in ignored repository-local source/cache
directories. The distributed package contains these version-controlled runtime
assets:

- `fe_table.npy`: `uint16[4, 91, 181]` geographical ownership;
- `fe_names.npy`: one-based Unicode geographical packaged names;
- `fe_seismic_by_geographic.npy`: one-based `uint8[758]` parent crosswalk;
- `fe_seismic_names.npy`: one-based Unicode seismic packaged names; and
- `metadata.json`: schema 3 multi-source provenance and runtime-asset metadata.

The provenance model distinguishes three roles: pinned ObsPy data provides the
geographical lookup representation and packaged geographical names; Young et
al. (1996) defines the supported structural revision; the declared ISC FE
standards representation provides operational seismic membership and packaged
seismic names. Source-data license status remains unresolved where no explicit
redistribution grant has been established. A software license is not assigned
to historical FE data by inference.

## 4. Resource cache and engine ownership

Normal package use has two process-local single-flight caches:

1. `load_packaged_assets()` loads and validates the packaged `.npy` files once;
2. `get_default_lookup()` constructs one default `FlinnEngdahlLookup` instance.

Concurrent first callers wait for the initializing caller and then receive the
same cached objects. Steady-state reads do not take the initialization locks.

Explicit `FlinnEngdahlLookup` construction is a different ownership boundary.
The constructor validates the supplied arrays, copies them once, and marks the
engine-owned copies read-only. Later mutation of caller-owned source arrays
cannot change engine behavior.

The historical two-array construction remains valid and creates a
geographical-only engine. Optional seismic crosswalk/name arrays add seismic
capability. A geographical-only engine raises `SeismicDataUnavailableError`
for seismic operations. It never borrows the default engine's hierarchy,
because an arbitrary custom geographical table is not proven compatible with
that hierarchy.

## 5. Coordinate and adapter validation

The core batch API validates shape and dtype before cell-index computation.
String, object, Boolean, and complex coordinate dtypes are rejected. Finiteness
and range are checked in the source dtype. The lookup kernel preserves that
dtype until absolute integer cell indices and quadrant ownership are selected;
it does not narrow valid extended-precision coordinates to `float64` first.
Exact `-180` uses longitude index 180 with east-side quadrant semantics without
rewriting the full longitude array.

The pandas adapter follows the same semantic coordinate-type contract and accepts an explicit geographical/seismic `level`. The default remains geographical. It:

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

GeoJSON is a derived area representation. The utility samples the centers of
the `360 * 180` one-degree cells and resolves the geographical ownership grid.
For seismic output, it maps that integer grid through the hierarchy before the
shared horizontal-run and dissolve algorithm. It does not first create 754
polygons and union them into 50 parents.

Geometry selection and annotation selection are separate controls:

- `level="geographic"` produces 754 geographical features;
- `level="seismic"` produces 50 seismic features;
- `properties=()` permits geometry-only machine output;
- a controlled property vocabulary permits generic level-relative
  `number`/`name` fields and explicit cross-level identifiers/names;
- `label` optionally adds a small human-facing number, name, or combined label;
  and
- `include_metadata=False` removes collection metadata when payload size matters.

The API intentionally does not implement an arbitrary title/template language
or every property permutation. The selected property names remain stable
semantic fields that machines can consume. Expensive cross-level child lists
are computed only when requested.

Dataset-wide scheme, revision, selected level, boundary model, and exact-point
boundary semantics live once in a collection-level `feregion` foreign member
by default. Feature properties contain only values that vary per feature.

The geometry is **area-equivalent one-degree GeoJSON**. It is not an exact
encoding of FE ownership for every coordinate on an integer boundary line.
Numeric lookup remains authoritative for an exact boundary coordinate. Retired
geographical IDs 172, 299, and 550 receive no fabricated geometry.

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

**Active investigation `PERF-INV-001`:** exploratory evidence shows that callers
which already hold longitude and latitude separately can incur material stacking
and memory cost under the current `(n, 2)` public contract. The external review
requires correctness repair and controlled baseline evidence before adopting a
new public surface. The next optimization evaluation should measure a private
split-array kernel and pandas end-to-end/peak-memory behavior first. A public
split-array API remains undecided.

Cross-Python benchmarking is a separate matrix from compatibility testing. Four
lock-backed tox-uv environments run the same standalone benchmark harness on
Python 3.11 through 3.14 and write raw JSON below `.tox/benchmark-results/`. A
report reducer selects eight public-path throughput metrics: three scalar
operations, two batch-number workloads, one batch name-conversion workload, and
two pandas copy workloads. The report records exact Python, NumPy, pandas, and
package versions and normalizes throughput to Python 3.11. Using one lock and one
machine reduces dependency and hardware confounding; recorded versions keep any
remaining environment-marker differences visible.

The longitude/quadrant kernel now uses mask-only antimeridian handling as part
of the extended-precision correctness repair. This removes the prior full-size
normalized-longitude temporary without changing the public batch shape contract.
Further split-array and pandas allocation changes remain subject to
`PERF-INV-001`.

A Rust backend remains deferred. Current NumPy throughput does not establish a
need for another runtime backend.

## 10. Verification architecture

Coordinate-to-grid-index correctness has an exhaustive synthetic layer that is
independent from FE scientific table contents. Every one-degree area cell is
probed at its center and nearest representable interior edge/corner values. Every
integer grid intersection is also probed with previous/exact/next representable
longitude and latitude values. Expected ownership comes from enumerated
cell/boundary identity, and separate probe tables expose quadrant, latitude
index, and longitude index. Source-table reproduction remains a separate layer
that verifies the scientific region assignments stored at those indices.

The repository uses `uv` as the development and build frontend.

GitHub Actions contains:

GitHub Actions resolves a compatible `uv>=0.10,<1` release from repository metadata, validates normal environments against the committed lock, bounds job runtimes, and cancels obsolete runs for the same branch or pull request.

- a Python 3.11, 3.12, 3.13, and 3.14 matrix that can fetch/verify the declared
  source inputs and runs the runtime suite with branch coverage;
- an independent-oracle job that installs ObsPy and executes both source-table
  reproduction and direct ObsPy comparison tests;
- a Python 3.11 lower-bound job that reuses the tox-uv `minimum` environment
  and resolves the lowest declared direct NumPy, pandas, Shapely, pytest, and
  pytest-cov versions; and
- a Python 3.14 quality job that runs Ruff, mypy public typing, distribution
  builds, wheel archive inspection, and dependency-isolated wheel verification;
  and
- a scheduled/manual live ISC semantic check that remains outside ordinary
  pull-request tests.

`tools/verify_wheel.py` first inspects the built archive for runtime files,
package data, metadata, extras, the console entry point, and license/provenance
notices. It then creates a fresh uv virtual environment without system site
packages, installs the wheel with dependencies, and exercises Python and CLI
APIs.

The repository uses local pre-commit hooks that execute the synchronized `uv`
development environment. The hooks run Ruff formatting, Ruff linting, and
mypy public typing, then invoke tox's `local` environment for behavioral tests. This keeps commit-time
tests aligned with the tox test definition without creating independent
hook-specific Python environments.

For local compatibility checks, `tox.toml` defines lock-backed `py311` through
`py314` environments plus a Python 3.11 `lowest-direct` environment. tox provides
environment orchestration; tox-uv delegates interpreter/environment creation and
dependency installation to uv. The minimum environment installs the project and
its `test` extra together with `uv-editable` and is recreated for every run, so
stale tox installer metadata cannot affect lower-bound resolution. Direct NumPy
and pandas lower
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
lower-bound dependency checks, the direct ObsPy oracle, Ruff, mypy public typing, and clean
installation were actually observed. Workflow configuration alone is not a
verification result.
