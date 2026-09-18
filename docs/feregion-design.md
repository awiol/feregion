# feregion design

| Field | Value |
|---|---|
| Behavioral contract series | `0.2` |
| Status | Current alpha design |
| Implemented target | `0.4` benchmark-system source implemented; external ASV execution evidence pending |

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

The engine also derives a read-only Boolean active-geographical mask from the
identifiers that occur in its lookup table. Direct geographical name and
hierarchy operations validate against this mask. Therefore a historical name
slot or custom crosswalk entry does not make an identifier active when the
engine's table never returns that identifier.

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

Plural region-number conversion APIs accept NumPy-compatible `ArrayLike`
inputs and always return NumPy arrays. This includes scalar array-like values:
a scalar input has shape `()` and produces a zero-dimensional result rather
than a NumPy scalar. This keeps the runtime result consistent with the published
`NDArray` return type while preserving the accepted input surface.

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
destination unchanged and does not publish a new partial destination. The CLI
diagnostic states this preserved filesystem condition so an operator does not
need to infer recovery state from implementation details. The contract does not
claim crash durability, directory fsync, ACL preservation, owner preservation,
or cross-filesystem atomicity.

stdout is a streaming sink. A later failure can leave earlier bytes visible.
The command returns its failure status and states that partial stdout may exist
and should be discarded before retrying.

## 8. GeoJSON derivation

GeoJSON is a derived area representation. The utility samples the centers of
the `360 * 180` one-degree cells and resolves the geographical ownership grid.
For seismic output, it maps that integer grid through the hierarchy before the
shared horizontal-run and dissolve algorithm. It does not first create 754
polygons and union them into 50 parents.

Geometry selection and annotation selection are separate controls:

- with the packaged lookup, `level="geographic"` produces 754 geographical
  features and `level="seismic"` produces 50 seismic features;
- with an explicit lookup, feature populations follow that engine's active
  geographical ownership grid and hierarchy;
- `properties=()` permits geometry-only machine output;
- a controlled property vocabulary permits generic level-relative
  `number`/`name` fields and explicit cross-level relationships; geographical
  features can expose one seismic parent, while seismic features can expose an
  ordered `geographic_regions` list of `{number, name}` child objects;
- `label` optionally adds a small human-facing number, name, or combined label;
  and
- `include_metadata=False` removes collection metadata when payload size matters.

The API intentionally does not implement an arbitrary title/template language
or every property permutation. The selected property names remain stable
semantic fields that machines can consume. Parallel child-number and child-name
arrays are avoided because their relationship is positional and easy to misuse.
Expensive cross-level child lists are computed only when requested. The CLI
accepts several names after one `--properties` option and expands
`--properties all` using the same level-specific vocabulary; the older
repeatable `--property` form remains a compatibility surface.

Dataset-wide scheme, revision, selected level, boundary model, and exact-point
boundary semantics live once in a collection-level `feregion` foreign member
by default. FE-1995 scheme/revision metadata is emitted only when the selected
engine is the packaged default instance. Other explicit engines retain
engine-independent coordinate/boundary metadata but use null scheme/revision
values because the engine constructor does not carry an
independent provenance declaration. Feature properties contain only values that
vary per feature.

Seismic cross-level child enumeration uses the engine's active geographical
membership together with its hierarchy. GeoJSON does not infer active membership
from all nonzero crosswalk slots, because unused slots may contain retained or
custom values without becoming active identifiers.

The geometry is **area-equivalent one-degree GeoJSON**. It is not an exact
encoding of FE ownership for every coordinate on an integer boundary line.
Numeric lookup remains authoritative for an exact boundary coordinate. Retired
geographical IDs 172, 299, and 550 receive no fabricated geometry.

## 9. Performance and benchmark-system design

### 9.1 Current implementation and 0.4 target boundary

The `0.3` beta source is the migration baseline. It uses the
standalone timer, `pytest-benchmark`, Tox benchmark-Python environments, a
custom cross-Python reducer, and the custom release comparator documented in
`benchmarks/README.md`. Those tools remain temporarily executable in `0.4 alpha implementation` as migration evidence until `REQ-PERF-017` is verified.

The implemented target core is `0.4.0`, dedicated to benchmark-system work. `0.4 alpha implementation` introduces the source implementation. The `0.4` target does not authorize unrelated runtime lookup features or
performance optimizations. Measurements may identify such work, but adoption of
that work requires its own compatibility/scope decision. Implementation status and verification status remain separate; external ASV execution and site-build evidence are still pending in this environment.

Routine benchmark semantics continue to cover in-process scalar, batch,
name-conversion, hierarchy, and pandas interfaces. CLI and GeoJSON timing remain
excluded because their dominant costs belong to process/I/O and geometry
subsystems rather than the core lookup path.

The `0.4` benchmark system has two jobs:

1. produce controlled evidence for package-performance decisions; and
2. maintain a public historical view across selected package revisions and
   Python/NumPy/pandas environments.

The selected target architecture is a **thin hybrid**. `feregion` owns benchmark
meaning, workload generation, historical-interface compatibility, correctness
checks, campaign intent, normalized evidence, and project-specific release
decisions. ASV owns generic benchmark mechanics: revision checkout, isolated
environments, package build and installation, timing, raw-sample retention,
result history, historical exploration, and static website generation.

The target must not reproduce ASV's generic infrastructure in a parallel custom
runner. A custom component is justified only when it expresses `feregion`-
specific semantics or closes a documented ASV capability gap.

### 9.2 Project-owned benchmark contract

The benchmark contract defines stable case identities and their semantics. Each
case declares:

- stable `case_id`;
- project-owned semantic `case_version`;
- the operation being measured;
- required package capability;
- workload generator and parameters;
- load-size parameter where applicable;
- operation count used for throughput;
- correctness oracle or invariant;
- whether a historical adapter is required;
- result applicability rules; and
- benchmark-specific setup that must remain outside the timed operation.

`case_version` changes when the timed operation, workload semantics, or result
interpretation changes so that prior measurements are no longer comparable. A
refactor or an added historical adapter does not by itself require a case-version
change when contract tests show that the measured semantics are unchanged.

ASV also versions benchmark definitions and normally derives its benchmark
version from benchmark source. The integration therefore maps ASV benchmark
version identity or explicit compatible-version aliases to the project case
contract. Default ASV source hashing alone is not the authority for whether two
`feregion` measurements are semantically comparable. The vertical slice verifies
this mapping because ASV/asv-runner version-identity behavior is tooling behavior,
not a package contract.

This contract must not depend on ASV result-file internals. Benchmark bindings may
use ASV's function/class conventions, but ASV does not define the semantic
meaning of a case.

For geographical lookup, the pinned source-table scanner remains the independent
same-workload semantic baseline. For scalar lookup, ObsPy remains an additional
comparison when installed. For seismic coordinate lookup, correctness is checked
against geographical lookup followed by the packaged crosswalk. Internal
optimization diagnostics must identify themselves as internal and must not become
public API contracts merely because they are benchmarked.

### 9.3 Historical compatibility adapters

A compatibility adapter maps one benchmark case onto a selected historical
`feregion` revision. The adapter targets supported public behavior of that
revision rather than private implementation details unless the case is explicitly
an internal diagnostic.

The evidence model distinguishes at least:

- **measured**: the revision supports the case, passes correctness, and produced
  valid measurement evidence;
- **not applicable**: the historical revision lacks the required capability;
- **environment unavailable**: the requested interpreter/dependency environment
  cannot be created for that revision;
- **build failed**: the selected revision cannot be built or installed in the
  resolved environment;
- **correctness failed**: the adapter ran but did not satisfy the declared oracle
  or invariant; and
- **execution failed**: benchmark execution failed after a valid build for a
  reason other than a declared not-applicable capability.

An adapter must not emulate a missing feature in benchmark code and then report
that emulation as historical package performance. Infrastructure/build failure
must not be relabeled as capability absence. Modern benchmark code may run
against older installed revisions; old revisions do not need to contain the
current benchmark harness.

### 9.4 Campaign control

A campaign is the operator-facing unit of work. A small human-editable TOML file
selects benchmark intent without embedding timing or environment implementation.
The campaign schema contains, at minimum:

```text
campaign identity and purpose
revision/release selectors
benchmark-case selectors
load sizes
repetitions
optional ASV round controls
environment profile
raw-sample retention policy
machine/comparability policy
report-generation requests
```

The target repository CLI has four responsibilities:

```text
plan      resolve exact revisions, cases, parameters, and environments
run       execute the resolved selection through ASV
compare   apply project-specific comparisons to retained ASV evidence
report    build the static benchmark report from retained results
```

These are responsibility names, not a promise that the final CLI subcommands use
these exact spellings. `plan` is read-only and exposes the exact execution set
before measurement begins. The campaign layer may produce a bounded ASV
configuration from maintained project profiles, but it must not become a second
benchmark runner. External GitHub Pages or other hosting publication is separate
from `report`; publication requires separate authorization and post-action state
verification.

The ASV subprocess boundary is treated as an external tool contract. The
configuration option is passed on the selected ASV subcommand, for example
`asv run ... --config PATH`. ASV changes its working directory to the directory
that contains an explicitly supplied configuration file. Generated campaign
configuration therefore lives temporarily in the repository root so the
repository-relative benchmark, environment, result, and HTML paths retain their
intended meaning. The temporary file is removed after the synchronous ASV
process returns.

Campaign revision values are **revision identities**, not ASV/Git revision-range
syntax. The operator may name `HEAD`, a tag, branch/ref, or commit identity. The
campaign preflight resolves each value with Git to one immutable 40-character
commit SHA and retains both the requested value and resolved SHA in the plan.
`run` passes `<resolved-sha>^!` to ASV so Git's first-parent traversal selects
exactly one commit. `compare` receives the two resolved commit identities. Range
expressions such as `HEAD^!`, `main..HEAD`, and `HEAD~1` are rejected as campaign
inputs; explicit history/range exploration remains an ASV investigation workflow
outside authoritative campaign revision identity.

### 9.5 ASV execution and history substrate

The initial implementation target is ASV `0.6.6`, the latest released version
verified during this design review. The repository dependency may use a reviewed
`0.6.x` compatibility range, but authoritative campaign evidence records the
exact ASV and asv-runner versions that executed the run. A future ASV minor line
requires compatibility review before it becomes an authoritative benchmark
backend.

ASV 0.6.6 provides or documents the required generic capabilities: project-
lifetime revision benchmarking, isolated environments including a `uv` backend,
dependency matrices, parameterized benchmarks, timing controls, optional raw-
sample retention, machine/result history, comparison/regression exploration, and
static publication including `gh-pages`. The implementation must verify the
selected ASV configuration and backend on the actual `feregion` repository rather
than treating documentation availability as product verification.

ASV discovers Python files throughout its configured benchmark package. The ASV
runner package is therefore isolated at `benchmarks/asv_suite/` and contains only
the semantic contracts, workloads, historical adapters, and ASV bindings needed
inside ASV-created environments. The retained predecessor pytest benchmark and
operator/report tooling remain outside this directory so ASV discovery does not
import their development-only dependencies or mistake them for runner content.

The ASV environment matrix owns benchmark runtime dependencies such as NumPy and
pandas. The project-build step is explicitly configured as
`python -m pip wheel --no-deps -w {build_cache_dir} {build_dir}` so the ASV build
cache contains one `feregion` wheel rather than project and dependency wheels.
Project installation uses `pip install --no-deps --force-reinstall {wheel_file}`
inside the selected ASV environment. This preserves the matrix-selected dependency
versions and satisfies ASV's `{wheel_file}` contract, which requires an unambiguous
single wheel. Both the persistent `asv.conf.json` and campaign-generated config
carry these commands; relying on ASV's 0.6.6 default build is prohibited because
that default may place dependency wheels in the same cache.

### 9.6 Workloads, load sizes, and correctness

Workloads are deterministic. The coordinate generator has a stable algorithm or
version identifier and seed. A campaign record retains canonical workload
parameters and, when practical, a fingerprint of the materialized input or its
canonical generator specification.

The standard batch-load series is the 1-2-5 engineering grid from 1 through
50,000,000 points:

```text
1, 2, 5,
10, 20, 50,
100, 200, 500,
1_000, 2_000, 5_000,
10_000, 20_000, 50_000,
100_000, 200_000, 500_000,
1_000_000, 2_000_000, 5_000_000,
10_000_000, 20_000_000, 50_000_000
```

A campaign may select a subset. Adjacency for the project release gate is defined
by this maintained order, not merely by whichever measurements happen to exist.
A release-gate campaign selects all sizes it requires for its decision and treats
missing required measurements as incomplete evidence. The complete grid is
intentionally available for scaling work but can require substantial memory;
resource exhaustion is an infrastructure result, not a valid timing result.

Correctness verification occurs before accepted timing. ASV `setup` or an
equivalent untimed phase builds the workload and calls the selected adapter once
against the case oracle or invariant. The timed function contains only the
operation whose performance is being measured. A failed correctness check
invalidates the timing result.

### 9.7 Measurement and comparability controls

The campaign layer exposes operator **repetitions** as the project term for ASV's
timing repeat control. ASV rounds, calibration, and warmup remain separate timing
concepts and are exposed only when the campaign contract needs them.

Authoritative release, dependency-sensitivity, and public-history campaigns use
raw-sample retention. Summary-only and quick runs are exploratory evidence and
are labelled accordingly.

Timed measurement is serial by default. `feregion` does not add concurrent timed
benchmark execution because the suite is small and interpretable timing has more
value than measurement throughput. Environment preparation or report generation
may be optimized later if it does not overlap timed processes.

Machine identity and environment metadata are retained for every authoritative
result. Release-gate ratios require the same recorded machine, interpreter,
direct benchmark dependencies, workload contract, benchmark case/parameters, and
timing contract. CPU frequency/power policy remains an external operator control
unless future tooling measures it reliably enough to become part of the contract.

### 9.8 Environment profiles

The target deliberately avoids a full Cartesian product of every Python, NumPy,
and pandas version. Named profiles answer different questions.

#### `release-history`

Purpose: compare `feregion` revisions while holding the main interpreter and
third-party dependency versions fixed.

```text
CPython 3.12 + NumPy 1.26.4
pandas cases additionally use pandas 2.1.4
```

This profile is the default for package-history and release-gate measurements
while the selected historical revisions can build and satisfy their case
contracts in it. If an older revision cannot build in this environment, record
that state explicitly; do not silently change dependencies and compare the new
measurement as though it belonged to the same release-history profile.

#### `python-supported`

Purpose: detect interpreter-sensitive performance over the supported Python
range.

```text
CPython 3.11
CPython 3.12
CPython 3.13
CPython 3.14
```

This profile uses one reviewed benchmark dependency baseline and records exact
resolved NumPy/pandas versions. It is performance evidence, not a substitute for
compatibility testing.

#### `numpy-sensitivity`

Purpose: identify material performance changes associated with selected NumPy
minor/major transitions without confounding them with Python-version changes.

```text
CPython 3.12 + NumPy 1.26.4
CPython 3.12 + NumPy 2.0.2
CPython 3.12 + NumPy 2.2.6
CPython 3.12 + NumPy 2.5.2
```

Pandas-dependent cases are excluded unless the selected campaign explicitly
provides a compatible pandas environment.

#### `pandas-sensitivity`

Purpose: detect material changes in the optional pandas adapter while holding the
primary numerical dependency stable.

```text
CPython 3.12 + NumPy 1.26.4 + pandas 2.1.4
CPython 3.12 + NumPy 1.26.4 + pandas 2.2.3
CPython 3.12 + NumPy 1.26.4 + pandas 2.3.3
CPython 3.12 + NumPy 1.26.4 + pandas 3.0.5
```

These versions preserve the previously accepted benchmark matrix. They are
methodology points, not a claim that they are always the latest patch releases. A
profile change requires a recorded methodology decision and must preserve enough
old results to interpret historical comparisons.

#### `dependency-matrix`

Purpose: execute the maintained union of NumPy and pandas sensitivity points in one
campaign without creating the full Cartesian product. The baseline is CPython 3.12 +
NumPy 1.26.4 + pandas 2.1.4; ASV `include` entries add the remaining NumPy points at
pandas 2.1.4 and the remaining pandas points at NumPy 1.26.4.

This profile is broader than either single-dependency sweep but remains bounded and
reviewable. It is not an exhaustive compatibility matrix.

### 9.9 Historical revision selection

Authoritative campaigns select exact package revisions deliberately. They do not
infer authority from Git recency or benchmark every reachable commit by default.
A campaign may name release tags, `HEAD`, branch/ref names, or commit identities;
preflight resolves each identity to one immutable commit before measurement. Git
range syntax is reserved for explicit investigation-history workflows and is not a
valid authoritative campaign revision identity.

Two modes are supported conceptually:

- **release history**: a bounded maintained set of package releases representing
  meaningful implementation generations; and
- **investigation history**: an explicit Git range or ASV history search used to
  locate when a measured change appeared.

Release-history membership is project configuration. Investigation-history output
is exploratory unless promoted into retained evidence under an authoritative
campaign contract.

### 9.10 Result and evidence model

ASV result files are measurement evidence, but ASV's incidental file layout is
not the stable `feregion` release-gate schema. A small evidence adapter emits a
normalized project record containing at least:

```text
benchmark semantic identity
package revision/version
benchmark parameters and load size
applicability/correctness state
machine identity
environment and direct dependency identity
ASV/asv-runner identity
sample/statistic linkage
median duration and derived throughput where defined
resolved campaign identity
```

The normalized record preserves traceability back to the retained ASV result and
samples. It does not discard failed, skipped, or not-applicable states to make a
comparison table rectangular. Parsing of any version-specific ASV result format
is isolated behind this adapter and covered by fixtures.

The release-regression rule remains project-owned: review is triggered when
candidate median batch throughput is more than 25 percent slower than the
accepted baseline at two adjacent maintained 1-2-5 load sizes of at least 10,000
points. `campaign check` reconstructs normalized evidence from retained ASV v2
result JSON without rerunning measurements, writes the normalized evidence to
`dist/benchmarks/`, and applies this rule. It requires exactly two revisions, the
fixed release-history profile, and one unambiguous common machine/environment
context. ASV's generic comparison/regression facilities may aid exploration but
do not replace this project gate. Missing required loads, an absent comparable
baseline, or ambiguous contexts make the performance gate incomplete, not passed.

### 9.11 Public benchmark history

ASV generates the target public benchmark site from retained result history. The
initial publication route is a static site suitable for GitHub Pages. Source
history, raw benchmark history, and generated HTML are separate artifact roles.
The source branch does not contain generated HTML or raw ASV result history.

Raw ASV history is retained in a durable location that can rebuild the static
site without rerunning measurements. A dedicated results/history branch or an
equivalent external store is permitted. The maintained operator runbook is
`docs/benchmark-operations.md`; it defines report regeneration, local preview, and
GitHub Pages publication. Publication is a separate state change: `asv publish`
builds derived HTML, while `asv gh-pages --no-push` prepares a local publication
branch and the final push is an explicit authorized external action. A successful
benchmark run does not prove that the public site was rebuilt or published. The
publication workflow verifies the resulting branch and public site before
reporting success.

Predefined campaigns are maintained operator interfaces: `smoke`, `head-full`,
`release-compare`, `release-history`, `python-supported`, `numpy-sensitivity`,
`pandas-sensitivity`, and `dependency-matrix`. `release-compare` names the accepted
prior benchmark candidate explicitly and is advanced as part of the next candidate
source so reruns do not depend on Git recency or memory.

### 9.12 Migration from the 0.3 benchmark implementation

Migration uses a vertical slice before broad conversion:

1. implement `lookup_numbers` over the maintained load contract and verify at least the original 1, 100, 1,000, 10,000, 100,000, and 1,000,000 migration points;
2. run the slice against the current `0.3` beta baseline and at least one older revision whose public
   interface materially exercises the compatibility-adapter boundary;
3. run at least one selected dependency-sensitivity profile;
4. retain raw ASV samples and normalize them into the project evidence schema;
5. apply the release-regression rule to comparable ASV-derived records;
6. build the ASV static site from retained results; and
7. compare semantic outputs, applicability, metadata identity, and release-gate
   outcome with the predecessor harness under one controlled environment.

Only after the slice passes should remaining benchmark cases and profiles migrate.
The predecessor path may then be removed case by case. `pytest` remains the
verification framework for benchmark-contract code, campaign resolution,
adapters, evidence normalization, and regression-gate logic; it is not the target
timing engine.

### 9.13 Existing optimization decisions

**Resolved internal optimization `PERF-INV-001`:** controlled measurements on the
accepted beta baseline show material stacking, hierarchy-revalidation, and
peak-memory cost. The engine therefore has package-internal split-vector paths
that accept equal-length one-dimensional longitude and latitude arrays without
broadcasting. pandas uses those paths directly. Public matrix lookup and the
internal split path converge on the same validated indexing kernel so the
source-dtype boundary semantics remain identical. Coordinate-to-seismic lookup
may apply the hierarchy crosswalk directly only to geographical numbers produced
by that same engine. A public split-array API remains deferred.

The longitude/quadrant kernel uses mask-only antimeridian handling as part of the
extended-precision correctness repair. This removes the prior full-size
normalized-longitude temporary without changing the public batch shape contract.
Further public split-array API changes remain deferred until an external consumer
need or new benchmark evidence justifies the additional compatibility surface.

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
`py314` environments plus a Python 3.11 `minimum` environment that uses uv
`lowest-direct` resolution. tox provides environment orchestration; tox-uv
delegates interpreter/environment creation and dependency installation to uv.
The minimum environment installs the project and
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
before it can be mistaken for project source. The default archive is written to
`dist/feregion-v<version>-<YYYY-MM-DD>-handoff.zip`, where the canonical project
name and version come from `pyproject.toml` and the date is the current UTC date. An explicit
`--output` path remains available for workflows that need another destination.
The archive's internal repository root remains the stable `feregion/` path.

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

### 9.8 ASV information and project summary page

The native ASV site remains the detailed benchmark explorer. Benchmark bindings
provide `pretty_name` and `pretty_source` metadata so ASV can show a human label
and the timed-operation contract without changing benchmark semantics or case
version identity.

A repository-local ASV plugin defines `FeregionSummary(OutputPublisher)`. During
`asv publish`, the publisher writes a small `feregion.json` summary and installs
project-owned JavaScript/CSS into the freshly generated site. ASV 0.6.6 copies a
fixed packaged HTML frontend and calls publisher subclasses, but the fixed HTML
does not automatically create navigation and DOM insertion points for arbitrary
custom pages. The publisher therefore applies one idempotent, marker-checked
addition to that copied HTML. It does not edit ASV's installed files and does not
replace ASV graph/regression code.

The summary page exposes coverage counts, measured tags/revisions, relevant
environment dimensions, ASV regression-signal count, project-gate interpretation,
and curated links that open parameterized benchmarks with `size` on the x-axis.
The native Grid, List, Graph, and Regressions pages remain accessible.

### 9.9 Release benchmark refresh

`benchmarks.release_workflow` is a thin orchestration layer over maintained
campaigns and ASV commands. It does not time code itself. The normal `refresh`
path covers the current-candidate integration smoke, routine release comparison,
full `HEAD` suite, sparse dependency matrix, and supported-Python profile; history
is opt-in because it is more expensive. It then runs the project release check
and rebuilds the complete ASV report from all retained results.

Campaign `run` accepts optional repetition/round overrides and `--append-samples`.
Append mode uses ASV's own retained-result sample combination behavior; the
project evidence adapter reads the resulting v2 parameter-list without combining
samples from different load values.

Publication state remains separate. `report` rebuilds local derived HTML,
`preview` serves it locally, and `publish` stages the GitHub Pages branch without
pushing unless the operator explicitly supplies `--push`.
