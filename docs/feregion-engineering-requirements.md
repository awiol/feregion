# feregion engineering requirements

| Field | Value |
|---|---|
| Status | Current alpha engineering contract |
| Planned target | `0.4.0` benchmark-system additions accepted; not implemented |

This document uses the normative profile defined by `feregion-requirements.md`.

## Governing guidance for the 0.4 benchmark target

The user-approved release-core decision dedicates `0.4.0` to benchmark-system
work. The current `0.3` beta line remains the implementation baseline until an
authorized `0.4` candidate is produced. The following method sources govern the
benchmark-target design and its review. They guide engineering work; they do not
create runtime package requirements unless a requirement below adopts them.

| Source | Exact version / date | Role in this target |
|---|---|---|
| User-approved project decision | 2026-09-17 | Select `0.4.0` as the benchmark-focused next minor target and keep the current `0.3` beta line for stabilization. |
| *Working with complex problems and systems* | `0.5.0-alpha.1`, 2026-09-07 | Scope control, architecture selection, evidence roles, bounded investigation, and stop conditions. |
| *Software Quality Guidelines — Integrated Operating Guide* | `0.4.0-alpha.4`, 2026-09-12 | Performance decision contracts, test oracles, compatibility, documentation consistency, review, and release evidence. |
| *Versioned Source-Bundle Delivery Guidelines* | `0.4.0-alpha.1`, 2026-09-11 | Target/candidate separation, post-beta scope control, cohesion, patch-baseline identity, one-off handoff, and verification claims. |
| *Controlled Technical Language and Terminology Control for Software and Science* | `0.3.0-alpha.1`, 2026-08-21 | Normative vocabulary, information-role separation, requirement wording, and semantic preservation. |

ASV `0.6.6` official documentation is specialist tool evidence for the selected
benchmark infrastructure. It is not a project-governance source and does not
override the requirements or decisions in this repository.

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

**REQ-DATA-012** — Provenance metadata must represent independently identified
source roles for geographical boundaries/names, the normative FE structural
revision, seismic membership, and seismic names. A source license must not be
inferred from the package software license or another source's license.

**REQ-DATA-013** — Runtime use must be fully offline. Repository tooling may
retrieve authoritative source data from online packages, APIs, or web
resources, but it must normalize and validate those sources into processed
runtime assets that are distributed with the package. Normal lookup, name
resolution, hierarchy conversion, pandas/CLI adaptation, and GeoJSON generation
must not require source retrieval or network access.

**REQ-DATA-014** — Repository tooling must provide an explicit ISC FE hierarchy
acquisition path. It must normalize the 50 seismic names and 754 active
geographical memberships, validate complete coverage, and protect the
normalized semantic content with SHA-256 independently of incidental HTML
layout.

**REQ-DATA-015** — The packaged seismic hierarchy must use a one-based
`uint8` geographical-to-seismic crosswalk with 758 entries and a one-based
Unicode seismic-name array with 51 entries. Index 0 and retired geographical
identifiers must use the hierarchy sentinel value zero.

**REQ-DATA-016** — The expected ISC hierarchy semantic SHA-256 must be a
literal reviewed value, not a value recomputed automatically from the Python
hierarchy declarations it protects. A name or membership change must fail
ordinary verification until an explicit source-review decision updates the
literal semantic identity.

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

**REQ-TEST-014** — A regression test for a corrected defect must demonstrate
sensitivity to the targeted incorrect behavior before the correction, or the
release evidence must record another credible sensitivity demonstration when
direct pre-fix execution is unavailable or unsafe.

**REQ-TEST-015** — Tests must verify that the tracked runtime asset bytes match
the SHA-256 values recorded for those generated assets in packaged provenance
metadata. Structural shape and dtype checks alone are not sufficient evidence
for asset identity.

**REQ-TEST-016** — Local compatibility verification must provide isolated test
environments for every explicitly supported CPython version and a Python 3.11
lower-bound environment. The lower-bound environment must derive the lowest
declared direct dependency versions from project metadata rather than maintain a
second hand-written list of version pins.

**REQ-TEST-017** — Tests must exhaustively verify, over every global
one-degree cell center, that seismic coordinate lookup equals geographical
lookup followed by the crosswalk. Tests must also verify all 754 active
geographical memberships and all 50 seismic identifiers.

**REQ-TEST-018** — ISC source-acquisition tests must exercise parsing, semantic
hashing, validation, and atomic normalized-data publication without depending
on a live network service during the ordinary test suite. Live source retrieval
may be a separate integration check.

**REQ-TEST-019** — On platforms where `longdouble` has more precision than
`float64`, regression tests must compare scalar and batch geographical and
seismic lookup immediately on both sides of FE integer-degree boundaries,
including antimeridian interiors, zero/quadrant transitions, and poles. The
regression evidence must demonstrate sensitivity to the predecessor narrowing
defect.

**REQ-TEST-020** — Thin routing tests must cover every top-level convenience
function exported by the package, the `python -m feregion` entry point, both
pandas hierarchy levels, both GeoJSON generation/write routes, and explicit
geographical-only engine failures for seismic operations. Deep engine behavior
need not be duplicated at the wrapper layer.

**REQ-TEST-021** — GeoJSON verification must check that every one-degree global
cell center is covered by the generated feature whose identifier is returned by
numeric lookup at both geographical and seismic levels. This does not establish
exact polygon-edge equivalence, which remains outside the GeoJSON contract.

**REQ-TEST-022** — Coordinate-indexing tests must exhaustively verify every
one-degree area cell with representable interior points at its center and
immediately inside each edge/corner. They must also verify previous, exact, and
next representable values around every integer longitude/latitude grid
intersection. Expected quadrant and absolute indices must derive from enumerated
cell or boundary identity rather than from the production floating-point-to-index
algorithm. Independent probe tables must expose quadrant, latitude index, and
longitude index so equal neighboring FE region numbers cannot mask an indexing
defect. The corpus must cover `float16`, `float32`, and `float64`, plus
`longdouble` when it provides greater precision than `float64`.

**REQ-PERF-001** — The repository must contain automated benchmark cases for the
implemented in-process lookup interfaces: scalar geographical and seismic number
lookup, scalar region lookup, scalar number-to-name conversion, geographical and
seismic batch number lookup, geographical-to-seismic batch conversion, batch
number-to-name conversion, and the optional pandas adapter with and without
names. CLI and GeoJSON operations are excluded from the routine lookup benchmark
suite because their dominant costs belong to other subsystems.

**REQ-PERF-002** — A performance claim must record the benchmark-case identity,
workload definition, load size, package revision, environment, machine identity,
benchmark-tool versions, resolved campaign configuration, repeated measurements,
correctness checks, and the aggregate/statistic used by the claim. Authoritative
release, dependency-sensitivity, and public-history claims must retain raw timing
samples. For batch comparison with the source-table scanner, the candidate and
scanner must use the same deterministic coordinate workload. Observed
measurements must remain separate from project-specific regression decisions.

**REQ-PERF-003** — Benchmark tooling must remain repository-side development
tooling rather than public runtime API. The project must provide a compatible
`benchmark` optional dependency and an authoritative `uv` benchmark dependency
group. The source distribution and source bundle must include benchmark cases,
campaign definitions, compatibility adapters, ASV configuration, and project
benchmark-analysis tooling. Generated ASV result history, raw run output, and
published HTML must remain outside the normal source tree.

**REQ-PERF-004** — Scalar lookup performance must be compared with the ObsPy
reference implementation when ObsPy is available and with the source-table
scanner otherwise. Scalar performance is a review signal, not a throughput SLA.
A material scalar regression must not justify changes that complicate the batch
hot path without corresponding evidence.

**REQ-PERF-005** — The benchmark system must provide named environment profiles
rather than an uncontrolled dependency Cartesian product. The initial profiles
must include:

- `release-history`: CPython 3.12 with NumPy 1.26.4; pandas-dependent cases add
  pandas 2.1.4. This fixed profile is the default cross-release comparison
  environment while those versions remain build-compatible with the selected
  historical revisions;
- `python-supported`: CPython 3.11, 3.12, 3.13, and 3.14 with one reviewed
  benchmark dependency baseline;
- `numpy-sensitivity`: CPython 3.12 with NumPy 1.26.4, 2.0.2, 2.2.6, and 2.5.2;
- `pandas-sensitivity`: CPython 3.12 with NumPy 1.26.4 and pandas 2.1.4, 2.2.3,
  2.3.3, and 3.0.5.

A profile revision must be reviewed as a benchmark-methodology change. Exact
resolved dependency versions must be retained with each result. Cross-environment
ratios are diagnostic unless the comparison contract explicitly makes them an
acceptance criterion.

**REQ-PERF-006** — A release-to-release performance regression gate must compare
a named accepted baseline result with the candidate result from the same recorded
machine, interpreter, dependency, benchmark-case, workload, load-size, and timing
contract. The gate must use median batch throughput and must trigger review when
slowdown exceeds 25 percent at two adjacent recorded batch sizes of at least
10,000 points. If comparable baseline evidence is unavailable, the release-
specific performance gate is incomplete rather than passed. Baseline/candidate
measurement evidence and the comparison result must be retained as delivery
evidence.

**REQ-PERF-007** — For the `0.4.0` benchmark target, Airspeed Velocity (ASV) must
be the generic infrastructure for revision selection, isolated benchmark
environments, project build/install, benchmark timing, raw-sample collection,
result history, historical comparison/exploration, and static public benchmark
reporting. The project must not maintain a second authoritative generic timing
engine, environment manager, result-history database, or benchmark website
generator unless a documented ASV capability gap requires one.

**REQ-PERF-008** — Benchmark meaning must remain project-owned and independent of
ASV storage internals. Each benchmark case must have a stable `case_id` and
project-owned semantic `case_version`, a deterministic workload definition, an
independent correctness oracle or invariant, a declared operation count when
throughput is reported, and a compatibility-adapter boundary when historical
package interfaces differ. The ASV benchmark-version identity or compatible
version aliases must be mapped explicitly to the project case version; ASV's
default source-code hash alone must not decide project comparability. A case
version must change when the timed operation, workload semantics, or result
interpretation changes incompatibly. ASV benchmark functions must remain thin
bindings to this project-owned contract.

**REQ-PERF-009** — Historical comparison must use explicit package revisions or
release identities selected by the campaign. Compatibility adapters must map a
stable benchmark case onto the supported public interface of each selected
historical package revision without requiring that revision to contain the modern
benchmark harness. If a revision cannot implement a benchmark case without
changing its semantics, the result must be recorded as not applicable with an
explicit reason. Capability absence must remain distinguishable from environment
or build unavailability, correctness failure, benchmark execution failure, and a
valid measured result. The campaign must not silently substitute another
operation or classify infrastructure failure as capability absence.

**REQ-PERF-010** — The repository must provide human-editable benchmark campaign
configuration and a thin operator CLI. A resolved campaign must identify its
purpose, selected package revisions, benchmark cases, load sizes, repetition and
round controls, environment profile, raw-sample policy, machine/comparability
policy, and requested report-generation steps. The resolved campaign plan must
be inspectable before execution and retained with authoritative result evidence.
External publication is a separate authorized workflow and is not implied by a
campaign report request.

**REQ-PERF-011** — The campaign CLI must translate operator intent into ASV
configuration and commands. It must not independently implement benchmark timing,
environment creation, package builds, result persistence, or HTML generation.
The initial command responsibilities must cover planning, running, comparing, and
building reports for a campaign. Final command spellings may change during
implementation when the responsibilities and compatibility contract remain
explicit. External publication must remain a separate action whose resulting
state is verified independently.

**REQ-PERF-012** — Correctness must be checked before a timing result is accepted.
An untimed benchmark setup step must construct the deterministic workload and
verify the selected package adapter against the declared oracle or invariant. The
timed callable must exclude oracle work. A correctness failure must prevent the
affected timing result from being treated as valid performance evidence.

**REQ-PERF-013** — Authoritative release, dependency-sensitivity, and public-
history campaigns must retain raw ASV measurement samples in addition to summary
statistics. The project evidence adapter must preserve enough result and
benchmark metadata to identify which samples support each reported aggregate. A
summary-only exploratory run must not be substituted for an authoritative run.

**REQ-PERF-014** — Benchmark measurement on one machine must be serial by
default. The campaign layer must not add parallel timed benchmark execution
unless controlled evidence shows that concurrency is needed and does not
invalidate the comparison contract. Parallel preparation that does not overlap
timed benchmark execution may be introduced separately when it has a clear
maintenance benefit.

**REQ-PERF-015** — The project must be able to build a static public benchmark
history from retained ASV results and must define a publication route suitable
for GitHub Pages or an equivalent static host. Generated HTML and raw result
history must remain outside the normal source branch. A successful benchmark run
must not be reported as successful publication; the publication workflow must
verify the resulting published branch or artifact state separately.

**REQ-PERF-016** — Project-specific release and comparison logic must consume a
normalized `feregion` benchmark-evidence record rather than depend directly on
incidental ASV JSON layout. The normalized record must preserve benchmark
`case_id` and `case_version`, package revision, parameters/load size, explicit
result state, applicability/correctness state, machine, environment, exact
ASV/asv-runner identity when available, sample/statistic linkage, and resolved
campaign identity. The ASV integration must use documented
interfaces where practical; any unavoidable parsing of version-specific ASV
result files must be isolated behind the evidence adapter and covered by fixtures
for the supported ASV version.

**REQ-PERF-017** — Migration to the `0.4` benchmark system must use a verified
vertical slice before predecessor timing/reporting paths are retired. The first
slice must cover `lookup_numbers` at load sizes 1, 100, 1,000, 10,000, 100,000,
and 1,000,000; the current `0.3` beta baseline plus at least one older revision that materially
exercises the historical-adapter boundary; at least one dependency-sensitivity
profile; raw-sample retention; normalized project evidence; the existing
release-regression decision; and a static ASV site build. The predecessor and
ASV paths must be compared for semantic outputs, applicability decisions,
benchmark/load identity, relevant metadata, and release-gate outcome.
`pytest-benchmark`, the standalone timer, the Tox benchmark matrix, and custom
cross-Python reporting must be removed when their required evidence has been
replaced. Permanent dual benchmark authority is not permitted.

**REQ-PERF-018** — The ASV process boundary must be verified against the supported
ASV command/configuration contract. Campaign execution must pass configuration
through the documented subcommand option, and generated configuration must be
located so ASV's configuration-directory working-directory behavior preserves
the intended repository-relative benchmark, environment, result, and HTML paths.
ASV discovery must use a dedicated benchmark package that excludes predecessor
pytest benchmark modules and unrelated repository tooling. Regression coverage
must exercise command construction, configuration lifetime/location, and exact
load-parameter filtering. When ASV is installed in the verification environment,
its own command parser or an equivalent direct-tool check should be used as an
additional oracle.

**REQ-PERF-019** — Authoritative campaign revisions must be single revision
identities, not Git/ASV range expressions. Before ASV execution, each selected
revision must resolve through Git to one immutable commit SHA; unresolved
identities must fail preflight, `run` must select exactly that commit, and the
requested identity plus resolved SHA must remain inspectable evidence. Project
build/install configuration must also keep dependency ownership explicit: the
ASV environment matrix owns NumPy/pandas selection, the project build must place
exactly one installable `feregion` wheel in the ASV build cache, and project
installation must not re-resolve runtime dependencies. Regression coverage must
exercise real Git history semantics and the effective persistent and
campaign-generated ASV build/install commands.

## Packaging, development environment, and license

**REQ-PKG-001** — The package must require Python 3.11 or newer. Automated
repository verification must cover Python 3.11, 3.12, 3.13, and 3.14. Python
3.11 remains the minimum supported interpreter. Newer Python versions are
permitted by package metadata but are not verified by this matrix until the
matrix is extended.

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
coverage on Python 3.11, 3.12, 3.13, and 3.14. A separate quality job must check
Ruff formatting, run Ruff linting, run the configured public typing check, build
distributions, and run dependency-isolated wheel verification.

**REQ-PKG-009** — The repository must contain automated synchronization checks
for the package version and duplicated compatibility dependency declarations.

**REQ-PKG-010** — `uv.lock` must be committed and must not be ignored. Normal
repository and CI environments must treat the committed lock as the resolved
dependency authority. A dependency or project-metadata change that makes the
lock stale must update the lock before locked verification can pass.

**REQ-PKG-011** — Hosted CI must execute the independently installed ObsPy
reference oracle in a job where ObsPy is actually installed. A skip in another
job must not be reported as direct-oracle verification.

**REQ-PKG-012** — Hosted CI must test the package on Python 3.11 against the
declared lower bounds of NumPy, pandas, Shapely, pytest, and pytest-cov. This
lower-bound job is compatibility evidence for the declared ranges; it does not
replace the normal current-dependency matrix.

**REQ-PKG-013** — Wheel verification must inspect the built archive for required
runtime modules, generated assets, metadata, optional-extra declarations, the
`fe-region` entry point, and license/provenance notices before installing the
wheel in a clean dependency-isolated environment. Repository-only tests, tools,
and benchmark harnesses must not appear in the runtime wheel.

**REQ-PKG-014** — The project must maintain an explicit software-quality and
release-gate document. Each material gate must state the claim it controls, the
required evidence, its acceptance condition, exception authority, and retained
evidence. A passing process check must not be promoted into a stronger product
claim.

**REQ-PKG-015** — A beta candidate must not be described as release-validated
or promotion-gate complete without an observed hosted-CI run for the exact
candidate source state, including the supported-Python matrix, static checks,
direct ObsPy oracle, lower-bound dependency compatibility, build, and clean
wheel verification. That stronger claim also requires a committed `uv.lock` or
an explicitly approved alternative resolved-dependency record. A beta source
handoff with partial verification must disclose the missing evidence instead of
converting it into a pass.

**REQ-PKG-016** — Repository development must include `pre-commit` in the `uv`
development toolchain. The repository pre-commit configuration must run Ruff
formatting and Ruff linting, then execute behavioral tests through a named tox
environment that reuses the repository test definition. The hooks must use the
project `uv` environment rather than maintaining independent hook-managed Python
tool environments, and they must reject a stale project lock instead of
refreshing it implicitly.

**REQ-PKG-017** — Repository tooling must declare a compatible uv version range
that is broad enough for supported developer environments and narrow enough to
exclude an unreviewed major-version contract change. CI must let `setup-uv`
resolve a compatible release from that range instead of pinning one exact uv
build. Normal test, oracle, and quality environments must use `uv sync --locked`,
and commands executed in those environments must use a lock-preserving
`uv run --locked` path. Distribution building must use the supported `uv build`
command without inventing a lock flag that the build command does not accept;
lock freshness is enforced by the preceding locked synchronization. The lower-bound
compatibility job may intentionally bypass the project lock because its purpose is
to exercise the declared minimum direct dependencies.

**REQ-PKG-018** — CI must bound job runtime and cancel obsolete runs for the same
workflow and pull request or branch. Push-triggered CI must run on the default
branch; pull-request CI must run before integration. These controls are resource
and feedback protections, not substitutes for test or compatibility evidence.
Checkout steps must not persist the workflow token when later steps do not need Git credentials.

**REQ-PKG-019** — The repository must provide a tox configuration backed by uv
for local compatibility orchestration. The default matrix must cover CPython
3.11, 3.12, 3.13, and 3.14 through explicit Python-factor environment names,
plus a Python 3.11 `minimum` environment that uses uv `lowest-direct`
resolution. Normal compatibility environments must use the repository lock.
The minimum environment must resolve the project
and its test requirements together in one dependency transaction so declared
NumPy and pandas lower bounds cannot be split into an ABI-incompatible pair.
The minimum environment must be recreated for each run so stale tox installer
metadata or packages cannot influence a lower-bound resolution after its runner
or installation strategy changes. Hosted lower-bound CI must execute that same
named minimum environment so local and hosted dependency-range checks do not
maintain separate test definitions.


**REQ-PKG-020** — Because the distributed package ships `py.typed`, local
pre-commit verification and hosted quality verification must run a supported
static type checker over the public package modules and a small
downstream-consumer typing fixture. Ruff remains the lint/format authority; type
checking is a separate evidence class. The downstream fixture must include
representative built-in and NumPy scalar coordinate forms that the runtime
scalar API intentionally supports.

**REQ-PKG-021** — Repository CI must provide a scheduled or manually triggered
live ISC semantic comparison that fetches the declared standards page and
verifies it against the independently retained reviewed semantic identity.
Ordinary pull-request tests must remain network-independent.
