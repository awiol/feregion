# feregion testing and verification

## Purpose

The test system provides evidence for public behavior, generated data,
structured-input preservation, failure semantics, packaging, and
performance-sensitive lookup paths. Coverage is an omission signal; it is not
proof of correctness or suitability.

## Local commands

Prepare the development environment and run the normal lock-preserving checks:

```bash
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked mypy
uv run --locked pytest -q
uv run --locked pytest -q --cov=feregion --cov-branch --cov-report=term-missing
```

After the locked synchronization above, build distributions with:

```bash
uv build
```

`uv build` has no lock flag. The preceding `uv sync --locked` establishes lock
freshness for the build evidence.

Verify a wheel in a dependency-isolated environment when registry access is
available:

```bash
uv run --locked python -m tools.verify_wheel dist/feregion-*.whl --python 3.11
```

The wheel verifier inspects package contents, metadata, extras, console entry
points, and license/provenance notices before installation. It then creates a
new uv virtual environment without system site packages and installs wheel
dependencies into that environment.

## Test layers

1. Core tests use synthetic tables and names to isolate coordinate behavior. Exhaustive grid-index tests use separate quadrant, latitude-index, and longitude-index probe tables so the expected index does not depend on real FE region equality.
2. Package-resource tests verify geographical and seismic asset structure,
   hierarchy coverage, packaged names, provenance metadata, and known FE results.
3. Source-reproduction tests compare geographical assets with hash-verified
   pinned ObsPy source tables and deterministically recreate seismic assets from
   the normalized ISC hierarchy representation.
4. Optional ObsPy oracle tests compare package behavior with the reference
   implementation when ObsPy is installed.
5. pandas and CSV tests verify selector identity, source-dtype validation
   parity, structured-input preservation, UTF-8/CSV parser failures, additive
   output, and publication behavior.
6. GeoJSON tests verify geographical/seismic area-cell coverage, compact and
   explicit property selections, collection metadata, and the boundary limitation.
7. Repository metadata tests detect version, dependency, contract-file, CI
   matrix, and traceability drift.
8. Benchmark harnesses measure geographical and seismic scalar/batch paths,
   hierarchy conversion, name conversion, and pandas interfaces. Routine
   benchmarks exclude CLI and GeoJSON.

## Exhaustive coordinate-grid indexing

The FE lookup is discontinuous only at integer-degree longitude and latitude
boundaries. The test suite therefore verifies the finite discontinuity structure
directly instead of attempting to sample the continuous coordinate domain.

For every one of the 64,800 one-degree area cells, tests construct a 3x3 set of
strictly interior coordinates: the cell center plus the nearest representable
values immediately inside each edge and corner. A second corpus constructs the
valid previous, exact, and next representable value around every integer
longitude and latitude boundary and takes their Cartesian product, which covers
every grid intersection and its neighboring sides.

Expected ownership is generated from the enumerated integer cell or boundary
identity before floating-point coordinates are constructed. Three valid synthetic
lookup tables expose quadrant, absolute-latitude index, and absolute-longitude
index independently. This avoids using the production conversion algorithm as
the oracle and prevents adjacent cells with the same real FE region number from
hiding an index-selection defect.

The deterministic corpus runs for `float16`, `float32`, and `float64`. It also
runs for `longdouble` when the platform provides more precision than `float64`.
The retained named regression corpus remains separate because it demonstrates
predecessor sensitivity for the `0.2.0a1` narrowing defect.

## Upstream source-data checks

Fetch both upstream source forms before complete source-reproduction and asset
regeneration checks:

```bash
uv run --locked python -m tools.fetch_obspy_fe_data
uv run --locked python -m tools.fetch_isc_fe_regions
```

The ObsPy fetcher resolves the required files at immutable commit
`a629e8c021052904b6b8d62699d03f2a3721ae63` for tag `1.4.2` and verifies each
file SHA-256. The ISC fetcher parses the declared FE standards page, validates
50 seismic regions and 754 active geographical memberships, then verifies the
normalized semantic SHA-256 before atomic local publication.

Ordinary tests exercise the ISC parser and normalized publisher with controlled
HTML and do not require live network access. Tests requiring the ObsPy source
cache skip with an acquisition instruction when it is absent. Release evidence
must distinguish an unavailable live source check from deterministic source-tool
verification.

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

## Local compatibility matrix

Use tox with the uv-backed runner for compatibility checks that need isolated
Python and dependency environments:

```bash
uv sync --locked --group dev
uv run --locked --group matrix tox run
```

The default matrix runs `py311`, `py312`, `py313`, and `py314` plus `minimum`. tox-uv
uses uv for environment creation and package installation and can obtain a
managed interpreter when the requested Python is not installed locally. The
`minimum` environment uses Python 3.11 with `uv_resolution = "lowest-direct"` and
installs the project plus its `test` extra in one uv transaction. This makes both
NumPy and pandas direct requirements of the same lower-bound resolution and avoids
old-pandas/new-NumPy ABI combinations caused by split installation. Project and
test lower bounds are therefore taken from `pyproject.toml` instead of a separate
list of exact pins. It prints the resolved Python, NumPy, pandas, Shapely, and
pytest versions before running the suite. The minimum environment is recreated
for every run so a previous tox installer cache cannot contaminate lower-bound
resolution after configuration changes. Run only that check with:

```bash
uv run --locked --group matrix tox run -e minimum
```

If testing an older repository revision that does not yet enforce recreation, use
`tox run --recreate -e minimum` once after changing its runner or install policy.

This matrix is intended as a pre-push compatibility check. It does not replace
locked normal-environment verification or hosted CI evidence.

## Locked CI environment

CI accepts `uv>=0.10,<1`; `setup-uv` resolves a compatible release from that
range. Normal matrix, oracle, and quality jobs use the committed
`uv.lock` with `uv sync --locked` and `uv run --locked`. The minimum-dependency
job intentionally invokes the tox-uv `minimum` environment, which creates a
separate Python 3.11 environment at the declared direct lower bounds.
Workflow jobs have explicit timeouts, and workflow concurrency cancels obsolete
runs for the same pull request or branch.

## CI authority

`.github/workflows/ci.yml` is the intended automated authority for:

- Python 3.11, 3.12, 3.13, and 3.14 test execution;
- branch coverage;
- source-reproduction checks;
- a direct installed-ObsPy oracle job;
- a Python 3.11 lower-bound dependency job that reuses `tox.toml`;
- Ruff;
- mypy public-package/downstream-consumer typing;
- a scheduled/manual live ISC semantic comparison;
- distribution builds; and
- dependency-isolated wheel verification.

A local result must not be reported as a CI result. A configured check that
could not run must remain an explicit verification limitation.

## Performance evidence

### Current `0.3` implementation

`0.3.0b1` uses the standalone benchmark runner, `pytest-benchmark`, the Tox
supported-Python benchmark matrix, and the custom release comparator. These are
the executable benchmark path for the current beta line. The accepted `0.4`
benchmark target does not make them invalid before migration.

Before timing the geographical coordinate candidate, current benchmark code
compares its output with the source-table scanner. Direct batch comparisons use
identical deterministic coordinates for candidate and baseline. Seismic paths
verify coordinate-to-seismic results against geographical lookup followed by the
crosswalk before timing; the hierarchy-only crosswalk is measured separately.

Current reports retain workload, environment, repetitions, median duration,
throughput, speedup, CPU model when discoverable, machine architecture, and
logical CPU count. Generated benchmark JSON and reports are delivery artifacts
and are not committed to source. CPU power/frequency policy is not measured by
the current harness and must be controlled externally for a release ratio used as
a gate.

Run the current supported-Python benchmark matrix after generating the local lock
and fetching verified FE source tables:

```bash
uv lock
uv run --locked python -m tools.fetch_obspy_fe_data
uv run --locked --group matrix --group benchmark tox run \
  -e benchmark-py311,benchmark-py312,benchmark-py313,benchmark-py314,benchmark-report
```

The current release comparator remains the `0.3` gate path:

```bash
uv run --locked --group benchmark python -m benchmarks.compare_releases \
  --baseline baseline.json --candidate candidate.json --fail-on-trigger
```

It rejects recorded environment/workload drift and returns status 3 when the
>25 percent slowdown trigger is crossed at two adjacent batch sizes of at least
10,000 points. Without a comparable accepted baseline, `QG-PERF` is incomplete.

### Accepted `0.4` ASV-driven target

The `0.4.0` target uses ASV for historical revision checkout, isolated benchmark
environments, package build/install, timing, raw-sample retention, result history,
comparison/exploration support, and static public reporting. Project code owns
benchmark-case semantics, deterministic workloads, correctness oracles,
historical-version adapters, campaign configuration, benchmark case/version
identity, evidence normalization, and the release gate.

The initial implementation is reviewed against ASV 0.6.6. The repository may
use a compatible reviewed 0.6.x dependency range, but authoritative results must
record exact ASV and asv-runner versions. ASV 0.6.6 documents an optional `uv`
environment backend; the vertical slice must verify the chosen backend on this
repository before the backend is treated as established project behavior.

A benchmark case is valid only when its untimed setup verifies the installed
revision against the declared oracle or invariant. The timed callable excludes
oracle work. Each case has a project `case_id` and semantic `case_version`; ASV
benchmark version identity or compatible aliases are mapped deliberately to that
contract so source refactoring alone does not decide comparability. An unsupported
historical capability becomes an explicit not-applicable state with a reason.
Keep capability absence separate from environment/build unavailability,
correctness failure, execution failure, and valid measurement; benchmark code
must not emulate the feature and report the emulation as historical package
performance.

The ASV process boundary uses subcommand-local `--config` and a temporary config in the repository root because ASV changes its working directory to the config directory. ASV discovery is limited to `benchmarks/asv_suite/`; retained predecessor pytest-benchmark modules are outside that package. Repository tests cover argv order, config location/lifetime, suite isolation, and exact partial-load filtering.

The target campaign layer uses a small TOML configuration and a thin CLI with
planning, running, comparing, and report-building responsibilities. Planning
resolves exact package revisions, benchmark parameters, load sizes, environment
profile, and timing controls before execution. Running delegates measurement to
ASV. Comparison consumes normalized ASV-derived evidence. Reporting rebuilds the
static history from retained results. External publication is a separate
authorized workflow and verifies publication state after the action.

Authoritative campaigns retain raw samples. The evidence adapter preserves
traceability from normalized release/comparison records back to retained ASV
results and samples. ASV's incidental result-file layout is not the project
release-gate schema.

### Initial environment profiles

```text
release-history:
  CPython 3.12 + NumPy 1.26.4
  pandas cases additionally use pandas 2.1.4

python-supported:
  CPython 3.11
  CPython 3.12
  CPython 3.13
  CPython 3.14

numpy-sensitivity:
  CPython 3.12 + NumPy 1.26.4
  CPython 3.12 + NumPy 2.0.2
  CPython 3.12 + NumPy 2.2.6
  CPython 3.12 + NumPy 2.5.2

pandas-sensitivity:
  CPython 3.12 + NumPy 1.26.4 + pandas 2.1.4
  CPython 3.12 + NumPy 1.26.4 + pandas 2.2.3
  CPython 3.12 + NumPy 1.26.4 + pandas 2.3.3
  CPython 3.12 + NumPy 1.26.4 + pandas 3.0.5
```

These profiles answer different questions and are not combined into a full
Cartesian product. Timed measurement is serial by default.

### `0.4` migration acceptance

The first implementation slice must cover `lookup_numbers` at `1`, `100`,
`1_000`, `10_000`, `100_000`, and `1_000_000`; `0.3.0b1` plus at least one older
revision that materially exercises the compatibility-adapter boundary; at least
one dependency-sensitivity profile; raw-sample retention; normalized project
evidence; the existing release-regression decision; and a static ASV site build
from retained results.

Run the predecessor and ASV slice under one controlled environment and compare:

- semantic outputs and applicability decisions;
- benchmark/load-size identity;
- environment, workload, and tool metadata;
- representative timing behavior without requiring identical samples; and
- release-gate outcome for controlled synthetic and real comparison records.

After the vertical slice passes, migrate remaining cases incrementally. Remove
predecessor timing/reporting paths only when their required evidence is covered.
`pytest` continues to test benchmark semantics, adapters, campaign resolution,
evidence normalization, and gate behavior; it is not the target timing engine.

## Clean repository handoff

Create a source handoff from the current tracked working tree with:

```bash
uv run --locked python -m tools.export_repository
```

The default output is
`dist/feregion-v<version>-<YYYY-MM-DD>-handoff.zip`, using the package version
from `pyproject.toml` and the current UTC date. Tracked working-tree edits are
included even when they are not committed. `uv.lock`, ignored paths, and all
untracked paths are excluded. The command warns about non-ignored untracked
paths because a new source file must be staged or committed before the default
exporter can distinguish it from local configuration or run output. Pass
`--output PATH` to override the destination. Use strict mode before an important
handoff:

```bash
uv run --locked python -m tools.export_repository --fail-on-untracked
```

## Commit-time checks

Install the development environment and hooks once:

```bash
uv sync --locked --group dev
uv run --locked pre-commit install
```

Run the complete commit-time pipeline manually with:

```bash
uv run --locked pre-commit run --all-files
```

The hooks use the synchronized project environment. Ruff formatting can modify
Python files; review and re-stage those changes before committing. Behavioral
tests run through `tox run -e local`, so pre-commit and the compatibility matrix
share one tox test definition instead of duplicating a direct pytest command.

### ASV campaign integration preflight

Before a timed campaign, run the read-only plan and inspect its `resolved_revisions`:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign plan benchmarks/campaigns/release-history.toml
```

Campaign revisions must be single identities such as `HEAD` or `v0.3.0b1`; range
syntax is rejected. The resolved plan must contain one immutable commit SHA for each
requested identity. The maintained and generated ASV configuration must use the
project-only wheel build/install commands with `--no-deps`. The real-ASV smoke for
a candidate should run one exact revision before a broader historical campaign and
should retain stderr if discovery/build/install fails.


## Benchmark operator workflow

The maintained benchmark runbook is `docs/benchmark-operations.md`. Benchmark
verification should use the predefined campaigns rather than reconstructing ad hoc
commands when an equivalent maintained campaign exists. The normal integration
sequence is:

```bash
uv run --locked --group benchmark asv check --config asv.conf.json
uv run --locked --group benchmark python -m benchmarks.campaign plan benchmarks/campaigns/smoke.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/smoke.toml
uv run --locked --group benchmark python -m benchmarks.campaign plan benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign check benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign report benchmarks/campaigns/release-history.toml
```

`campaign check` consumes retained ASV result JSON and does not rerun measurements.
The full `head-full` campaign spans the complete 1-2-5 grid through 50,000,000 and
requires a host with sufficient memory; resource failure at those sizes is not a valid
performance result. External GitHub Pages publication is intentionally separate from
these verification commands and is documented in the benchmark runbook.
