# feregion decision record

| Field | Value |
|---|---|
| Status | Current decision record |

This document records consequential current decisions. Requirements remain in
the requirements documents. Verification results remain in release evidence.
A later iteration must record a superseding decision instead of rewriting a
changed rationale as historical fact.

## `DEC-001` — Use a dense generated lookup table

- **Context:** FE lookup reduces coordinates to quadrant and integer absolute
  longitude/latitude bins.
- **Decision:** Use a generated `uint16[4, 91, 181]` dense table for runtime
  numeric lookup.
- **Alternatives considered:** direct source breakpoint scan; polygon/GIS
  lookup; Rust extension.
- **Rationale/evidence:** The dense table represents the fixed discrete mapping
  directly and batch benchmarks substantially outperform the Python
  source-table scanner.
- **Compatibility consequence:** Numeric results must remain reference-equivalent.
- **Review trigger:** Revisit only if FE source semantics change or measured
  workloads show a material unmet performance/resource requirement.

## `DEC-002` — Keep names outside the numeric hot path

- **Context:** Many callers need only numeric region IDs.
- **Decision:** Batch lookup returns only `uint16` IDs; name conversion is a
  separate operation. Packaged names follow ObsPy 1.4.2 `names.asc`.
- **Alternatives considered:** return structured ID/name values from every
  lookup; use ObsPy's separate `Flinn-Engdahl.csv` naming table.
- **Compatibility consequence:** The package does not claim one universally
  canonical FE designation where upstream name sources differ.
- **Review trigger:** A new authoritative naming requirement or source revision.

## `DEC-003` — Keep retrieved FE source tables outside version control

- **Context:** Runtime users need generated compact assets, while maintainers
  need reproducible source-table acquisition for regeneration and comparison.
- **Decision:** Track generated runtime `.npy` assets and metadata. Fetch the
  six upstream `*.asc` files into ignored cache storage from ObsPy 1.4.2 commit
  `a629e8c021052904b6b8d62699d03f2a3721ae63`, then verify SHA-256 before use.
- **Alternatives considered:** commit downloaded tables; require ObsPy at
  runtime; generate assets during package installation.
- **Compatibility consequence:** Runtime lookup stays offline. Source-reference
  tests require the fetch step.
- **Review trigger:** Upstream source revision, package-data policy, or license
  disposition changes.

## `DEC-004` — Use `uv` as the repository workflow frontend

- **Context:** Earlier iterations duplicated short package operations in a
  Makefile.
- **Decision:** Use explicit `uv` commands for environment management,
  dependency groups, checks, benchmarks, and builds. Do not maintain a Makefile
  that only aliases those commands.
- **Compatibility consequence:** Previously published optional extras remain for
  package consumers, while dependency groups are authoritative for repository
  work.
- **Review trigger:** A future workflow needs a reproducible multi-step build
  abstraction that `uv`/project configuration cannot express clearly.

## `DEC-005` — Own explicit-engine data defensively

- **Context:** A frozen engine that retained views into caller-owned arrays was
  externally mutable.
- **Decision:** Explicit `FlinnEngdahlLookup` construction copies table and name
  arrays once and marks its copies read-only.
- **Alternative considered:** borrowed-data semantics documented as caller
  responsibility.
- **Compatibility consequence:** Construction performs a small fixed copy;
  subsequent behavior is stable against caller mutation.
- **Review trigger:** A justified large alternate-data use case makes copying a
  material cost.

## `DEC-006` — Treat GeoJSON as area-equivalent derived output

- **Context:** Ordinary closed polygons cannot reproduce every directional FE
  ownership rule on exact integer boundary lines.
- **Decision:** GeoJSON represents unions of one-degree cell areas. Numeric
  lookup remains authoritative for exact boundary points.
- **Compatibility consequence:** GeoJSON is suitable for visualization and
  area-cell analysis, not as an independent high-resolution FE boundary source.
- **Review trigger:** The project adopts an authoritative vector boundary source
  with explicit point-boundary semantics.

## `DEC-007` — Use atomic filesystem publication for CSV output

- **Context:** Direct destination writing could destroy input/existing output or
  expose partial files after a later failure.
- **Decision:** File output is written to a sibling temporary file and replaced
  only after successful processing. Existing destination permission bits are
  preserved. stdout remains a non-atomic stream.
- **Compatibility consequence:** Invalid input returns failure without
  publishing a partial file; already-written stdout bytes cannot be rolled back.
- **Review trigger:** Crash durability, fsync, ownership, ACL, or cross-filesystem
  publication becomes a product requirement.

## `DEC-008` — Keep alpha maturity until promotion gates pass

- **Context:** Core behavior is mature relative to earlier iterations, but
  release evidence is incomplete across static checks, dependency locking,
  hosted compatibility jobs, and source-data license disposition.
- **Decision:** Keep alpha maturity until the documented beta-promotion gates pass on one candidate state.
- **Alternatives considered:** beta promotion; a new development line; final release.
- **Compatibility consequence:** The public API remains backward-compatible;
  this iteration fixes boundary failures and strengthens assurance.
- **Review trigger:** Apply the beta conditions in the current quality-assurance
  document to one exact candidate source state.

## `DEC-009` — Keep maintained documents at stable Git paths

- **Context:** Version/date-stamped filenames duplicated revision identity that Git
  already provides and forced broad documentation churn for every release.
- **Decision:** Keep maintained requirements, design, quality-assurance, decision,
  and traceability documents at stable filenames. Keep release identity in Git,
  `CHANGELOG.md`, package metadata, and delivery-side artifacts.
- **Alternatives considered:** rename all maintained documents on every release;
  keep both stable aliases and versioned copies.
- **Compatibility consequence:** Repository links remain stable across releases.
- **Review trigger:** The repository stops using revision-controlled history or a
  downstream publication system requires immutable document filenames.

## `DEC-010` — Use pre-commit as the commit-time quality entry point

- **Context:** Maintainers need the same formatter, linter, and tests before a
  commit without maintaining another dependency environment.
- **Decision:** Declare `pre-commit` in the `uv` development toolchain and use
  local hooks that run Ruff format and Ruff check through `uv --no-sync`, then
  delegate behavioral tests to tox's `local` environment.
- **Alternatives considered:** hook-managed Ruff environments; a custom shell
  script; no commit-time checks.
- **Compatibility consequence:** Developers must run `uv sync --group dev` before
  installing hooks. Package runtime dependencies do not change.
- **Review trigger:** Commit-time tox-backed tests become materially too expensive
  or repository tooling moves away from `uv`/pre-commit.

## `DEC-011` — Support CPython 3.11 through 3.14 and harden hosted CI

- **Context:** Python 3.14 is used successfully by maintainers, but the declared
  hosted compatibility matrix stopped at 3.13. CI also allowed uv and the lock
  state to change implicitly during normal jobs.
- **Decision:** Keep Python 3.11 as the minimum supported version and verify
  CPython 3.11, 3.12, 3.13, and 3.14. Originally pin uv to `0.12.6`, require locked sync for
  normal jobs, bound job runtimes, and cancel obsolete workflow runs.
- **Alternatives considered:** raise the minimum Python version; treat 3.14 as
  unverified; install latest uv on each run; allow normal CI to refresh the lock.
- **Compatibility consequence:** Python 3.11 remains supported. Python 3.14 becomes
  an explicit compatibility target. The lower-bound dependency job remains on
  Python 3.11.
- **Supersession:** The exact uv pin is superseded by `DEC-012`; the Python matrix,
  locked-environment, timeout, and concurrency decisions remain active.
- **Review trigger:** a supported Python version reaches end of project support,
  or hosted CI shows a dependency/packaging incompatibility.

## `DEC-012` — Constrain uv by compatibility range, not exact release

- **Context:** Exact `uv` pinning caused otherwise compatible local tooling, tests,
  and builds to fail solely because the installed uv executable had a different
  patch/minor release. The repository relies on stable command contracts such as
  `sync --locked`, `run --locked`, `uv build`, and `python install`, not on
  behavior unique to one uv release. The earlier draft incorrectly described
  `uv build --locked`; `DEC-019` records the correction.
- **Decision:** Require `uv>=0.10,<1`. Let `setup-uv` resolve the highest compatible
  release from the repository constraint. Keep the GitHub Action itself pinned by
  commit SHA for supply-chain stability. Tests verify the compatibility-range and
  locked-workflow contracts, not one literal uv executable version.
- **Alternatives considered:** no uv version constraint; exact executable pin;
  per-workflow uv pins independent of repository metadata.
- **Compatibility consequence:** Existing uv 0.10+ developer environments can run
  repository commands without artificial failure, while uv 1.x requires an explicit
  future review before becoming part of the tooling contract.
- **Review trigger:** required commands become unavailable or materially change
  semantics within the accepted range, or uv 1.x is evaluated for adoption.
## `DEC-013` — Use Ruff as the sole project static-analysis authority

- **Context:** The project previously carried a second static type checker in the
  development dependency set and hosted quality job. Maintainers prefer Ruff as
  the authoritative static-analysis, linting, and formatting tool for this
  repository.
- **Decision:** Remove the second static type checker from project dependencies,
  configuration, documented verification commands, and hosted CI. Keep Ruff
  formatting and Ruff linting as the `QG-STATIC` evidence. Keep pytest as the
  behavioral verification authority.
- **Alternatives considered:** retain both static tools; run the second checker
  only locally; keep it as an optional non-gating dependency.
- **Compatibility consequence:** Runtime package behavior and Python support do
  not change. Development environments no longer install or run the removed
  checker.
- **Review trigger:** A future requirement needs static guarantees that the
  configured Ruff rule set cannot provide and evidence supports adding another
  analysis tool.

## `DEC-014` — Use tox-uv for local Python and dependency compatibility matrices

- **Context:** Hosted lower-bound CI exposed behavior that was not reproduced by
  the maintainer's current Python 3.14/current-dependency environment. The
  repository needs a fast local way to exercise multiple interpreters and the
  declared dependency floor without hand-maintaining a second dependency list.
- **Decision:** Add a native `tox.toml` matrix for CPython 3.11 through 3.14 and a
  Python 3.11 `minimum` environment. Use tox for orchestration and tox-uv for
  environment creation and installation. Normal compatibility environments use
  the repository lock. The minimum environment resolves with `lowest-direct`, and
  hosted lower-bound CI invokes the same named environment.
- **Alternatives considered:** retain only hosted CI; maintain a custom shell
  loop around `uv venv`/`uv pip`; use plain tox with virtualenv/pip; use Nox with
  custom uv subprocess commands.
- **Compatibility consequence:** Local compatibility checks may download missing
  managed Python interpreters and dependency versions. Runtime package
  dependencies do not change. The normal lock remains separate from the
  intentionally unlocked lower-bound resolution. `DEC-018` refines the minimum
  installation shape after hosted CI exposed a split-resolution ABI mismatch.
- **Review trigger:** uv gains an equally declarative native multi-environment
  matrix, tox-uv no longer tracks supported uv/tox behavior, or matrix runtime
  becomes disproportionate to the defects it catches.

## `DEC-015` — Exclude `uv.lock` from iterative source handoffs

- **Context:** The repository uses `uv.lock` for local and hosted locked
  environments, but delivery-side reconstruction cannot reliably preserve the
  maintainer's locally generated lock and should not block source/patch delivery
  on it.
- **Decision:** Keep `uv.lock` as maintainer-generated repository state. Exclude
  it from AI-produced source archives and incremental patches, and ignore lock
  hunks when a supplied patch is used only to reconstruct the source baseline.
  The maintainer regenerates the lock locally after applying source changes.
- **Alternatives considered:** require exact lock bytes in every source handoff;
  fabricate/update partial lock content; omit locked repository workflows.
- **Compatibility consequence:** Source handoffs remain reproducible for tracked
  project source while the maintainer remains responsible for lock regeneration.
  Hosted jobs that use `--locked` require the locally regenerated lock to be
  committed before push.
- **Review trigger:** Delivery tooling gains reliable repository-native lock
  synchronization or the project stops using a committed lock.

## `DEC-016` — Export maintainer handoffs from Git-tracked working-tree files

- **Context:** Maintainer repositories accumulate virtual environments, caches,
  benchmark runs, IDE/user configuration, and locally generated `uv.lock`, while
  local format/check steps can legitimately modify tracked source before the next
  handoff. Broad filesystem archiving either leaks local state or requires a
  fragile exclusion list.
- **Decision:** Provide `tools.export_repository`. Discover source paths from
  `git ls-files`, read current working-tree bytes, preserve executable state,
  explicitly exclude `uv.lock`, and omit all untracked files by default. Warn on
  non-ignored untracked files and provide a strict mode that rejects them. Build
  deterministic ZIP bytes for an unchanged tree.
- **Alternatives considered:** `git archive HEAD` only; archive the filesystem and
  maintain a large deny list; require every local edit to be committed before
  handoff.
- **Compatibility consequence:** Tracked local edits are preserved without
  collecting local-only state. A genuinely new source file must be staged or
  committed before default export.
- **Review trigger:** The project adopts another source-control system or requires
  deliberate handoff of untracked generated source.

## `DEC-017` — Benchmark supported Python versions with one locked environment model

- **Context:** Compatibility tests answer whether the project works across Python
  versions but do not show interpreter-sensitive performance. Independent
  benchmark environments can also drift in dependency resolution and make the
  comparison hard to interpret.
- **Decision:** Add lock-backed tox-uv benchmark environments for Python 3.11,
  3.12, 3.13, and 3.14. Run the same deterministic standalone harness in each
  environment and aggregate eight representative throughput metrics into one
  Markdown report normalized to Python 3.11. Record exact interpreter, NumPy,
  pandas, and package versions in the report.
- **Alternatives considered:** benchmark only the maintainer interpreter; publish
  the full raw metric set without reduction; resolve each interpreter environment
  independently without a lock.
- **Compatibility consequence:** Benchmark execution is heavier than the routine
  test matrix and requires a locally generated `uv.lock`, but the resulting
  comparison is substantially easier to interpret.
- **Review trigger:** The supported Python matrix changes, dependency markers make
  locked comparisons materially asymmetric, or evidence shows a different metric
  subset better represents user-visible performance.
## `DEC-018` — Share tox test definitions and co-resolve minimum dependencies

- **Context:** The first tox lower-bound environment selected pandas 2.1 while a
  separate installation step retained a NumPy 2.x release. That pair can fail at
  pandas import because older pandas wheels were built against the NumPy 1.x ABI.
  Pre-commit also duplicated the behavioral test command by invoking pytest
  directly instead of using the tox test definition.
- **Decision:** Name normal compatibility environments `py311` through `py314` and
  run them with tox-uv's lock runner. Add a lock-backed `local` tox environment
  for commit-time behavioral tests. Configure the Python 3.11 `minimum`
  environment as an unlocked `uv-venv-runner` with `package = "uv-editable"`,
  `extras = ["test"]`, and `uv_resolution = "lowest-direct"`. This causes the
  project requirement on NumPy and the test-extra requirement on pandas to be
  resolved in one uv installation transaction. Set `recreate = true` for this
  special lower-bound environment so tox never reuses installer metadata or
  packages from a previous minimum-environment strategy. Pre-commit invokes
  `tox run -e local` instead of invoking pytest directly.
- **Alternatives considered:** pin NumPy below 2 globally; raise the pandas floor
  solely to avoid the old ABI boundary; duplicate exact minimum versions in CI;
  keep direct pytest in pre-commit; run the complete four-Python matrix on every
  commit.
- **Compatibility consequence:** The declared runtime dependency bounds do not
  change. Minimum-dependency testing now exercises a coherent lower-bound vector
  instead of an accidental old-pandas/new-NumPy combination. Commit-time testing
  incurs tox environment orchestration but reuses a cached lock-backed local
  environment after initial creation.
- **Review trigger:** tox-uv changes package/extras resolution semantics, the
  lower-bound vector still produces an ABI-incompatible environment, or local
  tox-backed commit checks become disproportionate to their defect-detection
  value.

## `DEC-019` — Keep lock enforcement out of the `uv build` command line

- **Context:** Hosted CI exposed that `uv build --locked` is not a supported uv
  command form. The repository had conflated lock-preserving project environment
  operations (`uv sync --locked` and `uv run --locked`) with distribution building.
- **Decision:** Build distributions with plain `uv build`. Keep lock freshness and
  reproducible project-environment enforcement in the preceding `uv sync --locked`
  and subsequent `uv run --locked` verification steps. Repository contract tests
  must reject reintroduction of `uv build --locked`.
- **Alternatives considered:** pass `--locked` through to a build backend; weaken
  locked synchronization; remove lock checks from the quality job.
- **Compatibility consequence:** The quality job works across the accepted uv
  compatibility range while preserving locked dependency setup for tests and wheel
  verification. Build-system requirements remain governed by the build frontend and
  `build-system` metadata rather than by an unsupported project-lock flag.
- **Review trigger:** uv adds documented build-lock semantics that materially improve
  reproducibility, or the project adopts explicit build constraints/hashes.

## `DEC-020` — Model seismic regions as a parent crosswalk

- **Context:** The 1995 FE revision defines 50 seismic regions as coarser groups
  of 754 active geographical regions. A second coordinate table would duplicate
  ownership information and could diverge from the geographical result.
- **Decision:** Keep the existing dense geographical table authoritative for
  coordinate ownership. Store a one-based `uint8[758]` geographical-to-seismic
  crosswalk and one-based seismic name array. Derive coordinate-to-seismic
  results through the crosswalk.
- **Compatibility consequence:** Existing geographical results are unchanged.
  New explicit seismic APIs are additive.
- **Review trigger:** A future FE revision changes the hierarchy or measured
  evidence shows that the crosswalk path cannot satisfy an accepted performance
  requirement.

## `DEC-021` — Preserve geographical-only explicit engines

- **Context:** `FlinnEngdahlLookup(table, names)` is an existing public
  construction contract. Silently attaching packaged seismic data to an
  arbitrary custom table could produce invalid classifications.
- **Decision:** Preserve the two-array constructor. Optional seismic arrays add
  seismic capability. A geographical-only engine raises
  `SeismicDataUnavailableError` for seismic operations.
- **Compatibility consequence:** Existing explicit construction remains valid;
  seismic capability is explicit and cannot be inferred from unrelated data.
- **Review trigger:** The project adopts a versioned custom-dataset contract that
  can prove hierarchy compatibility independently.

## `DEC-022` — Separate GeoJSON geometry level from presentation properties

- **Context:** Machine consumers may need the smallest practical GeoJSON, while
  human-facing output benefits from names, cross-level identifiers, or a label.
  `level` alone cannot control those payload choices.
- **Decision:** `level` selects geographical or seismic geometry. A controlled
  `properties` list selects semantic feature fields, `label` supplies one small
  convenience annotation, and collection metadata can be omitted. Dataset-wide
  boundary metadata is stored once at collection level by default.
- **Compatibility consequence:** Default geographical features still expose
  `number` and `name`. Boundary metadata moves from each feature to the
  collection-level `feregion` member.
- **Review trigger:** A concrete renderer or exchange contract requires a field
  that cannot be represented by the controlled semantic-property vocabulary.

## `DEC-023` — Retrieve source data for regeneration; ship processed assets for offline use

- **Context:** Authoritative source material is available through online
  repositories or web services, but runtime network access would weaken
  reproducibility, latency, availability, and offline use.
- **Decision:** Keep explicit source-retrieval tools for pinned ObsPy and declared
  ISC inputs. Validate retrieved inputs, transform them into runtime-optimized
  assets, version those assets with the package, and require no network for
  normal lookup, hierarchy, names, adapters, or GeoJSON generation.
- **Compatibility consequence:** Installation contains all runtime FE data.
  Network access is a maintainer regeneration concern, not a user lookup
  dependency.
- **Review trigger:** Package-size constraints, source redistribution terms, or a
  new authoritative FE revision require another distribution model.

## `DEC-024` — Defer split longitude/latitude batch optimization pending evidence

- **Context:** Some callers already hold longitude and latitude in separate
  arrays. The current `(n, 2)` batch interface can require stacking or copying
  before lookup.
- **Decision:** Record `PERF-INV-001` as a bounded future investigation. Measure
  allocation, peak memory, throughput, validation complexity, and API cost for
  already-split inputs before adding a new public surface or replacing the
  current batch contract.
- **Compatibility consequence:** No current API change follows from this
  investigation record.
- **Review trigger:** Representative workloads show stacking/copy cost is
  material, or a downstream integration supplies separate arrays at scale.

## `DEC-025` — Preserve coordinate dtype through FE cell ownership

- **Context:** Review of `0.2.0a1` reproduced scalar/batch disagreement for
  supported `longdouble` coordinates immediately beside integer-degree
  boundaries. Validation occurred in source precision, but batch lookup then
  narrowed the coordinate matrix to `float64` before selecting the FE cell.
- **Decision:** Keep validated batch coordinates in their source numeric dtype
  until absolute integer longitude/latitude indices and quadrant ownership are
  established. Handle exact longitude `-180` through quadrant selection rather
  than by rewriting the longitude array. Do not narrow valid extended-precision
  coordinates before FE cell ownership is determined.
- **Alternatives considered:** retain `float64` internal normalization; reject
  wider floating dtypes; round scalar lookup to match batch behavior.
- **Compatibility consequence:** Ordinary `float64`/integer behavior remains
  unchanged. Supported wider floating inputs now preserve scalar/batch
  equivalence at FE discontinuities. The change also removes one full-size
  normalized-longitude temporary from the batch kernel.
- **Review trigger:** NumPy casting/index behavior changes materially, a future
  coordinate model introduces another discontinuity rule, or cross-version tests
  find scalar/batch divergence for a supported dtype.

## `DEC-026` — Keep the ISC semantic source identity independent from hierarchy code

- **Context:** In `0.2.0a1`, the expected ISC semantic hash and ordinary source
  fixture were generated from the same hard-coded Python hierarchy that they
  were intended to protect. A coherent hierarchy edit could therefore update
  expected content without an independent source identity.
- **Decision:** Keep the expected ISC semantic SHA-256 as a literal reviewed
  value that is not recomputed from the Python hierarchy declarations. Ordinary
  tests verify that the declared hierarchy still matches that literal identity,
  and live ISC retrieval remains a scheduled/manual external comparison. An
  update to names or memberships therefore requires an explicit source-review
  change to the literal identity as well as any regenerated assets.
- **Alternatives considered:** retain a self-derived expected hash; track a full
  normalized ISC snapshot despite unresolved redistribution status; pin raw ISC
  HTML byte-for-byte; make live network retrieval part of ordinary tests.
- **Compatibility consequence:** Runtime assets and public APIs do not change.
  A hierarchy source update now requires an explicit reviewed semantic-pin update
  before verification and asset regeneration can pass.
- **Review trigger:** ISC publishes a new FE structural revision, the normalized
  source schema changes, or source-retention/licensing policy requires a
  different provenance mechanism.

## `DEC-027` — Define release performance regression against a named prior record

- **Context:** The existing `>25%` slowdown review trigger had no historical
  package baseline. Source-scanner and cross-Python comparisons answer different
  questions and cannot establish release-to-release regression by themselves.
- **Decision:** Compare a candidate with a named accepted prior-package benchmark
  record produced by the same harness in the same recorded host, interpreter,
  dependency, and workload context. Trigger review when median batch throughput
  slows by more than 25 percent at two adjacent sizes of at least 10,000 points.
  If a comparable baseline is unavailable, report the release performance gate
  as incomplete. Retain both raw records and the comparison output as delivery
  evidence.
- **Alternatives considered:** remove the regression trigger; use source-scanner
  speedup as the regression baseline; use the cross-Python aggregate score.
- **Compatibility consequence:** No runtime behavior changes. Benchmark reports
  gain host-context fields and release comparison tooling.
- **Review trigger:** Representative workloads or measurement evidence show that
  the selected batch sizes/statistic/threshold no longer support the release
  decision.

## `DEC-028` — Treat WGS84 as a package input convention, not an FE source claim

- **Context:** Project wording described FE inputs as WGS84 coordinates, while
  the supporting FE evidence establishes a longitude/latitude degree grid but
  does not establish a historical WGS84 datum requirement. The package performs
  no CRS transformation.
- **Decision:** Interpret input longitude/latitude values as WGS84 geographic
  degrees by package convention. State explicitly that this convention is
  separate from the historical FE definition and that `feregion` does not
  transform coordinates between CRSs.
- **Alternatives considered:** remove all datum-specific wording; implement CRS
  transformation; imply WGS84 is normative FE provenance.
- **Compatibility consequence:** Numeric behavior does not change. Public
  documentation and GeoJSON metadata distinguish the package convention from
  the FE scientific source definition.
- **Review trigger:** The package adds CRS transformation or evidence establishes
  a more appropriate normative coordinate-reference contract.

## `DEC-029` — Add a public typing gate alongside Ruff

- **Context:** `feregion` ships `py.typed`, which asks downstream type checkers to
  rely on inline annotations. Review identified that Ruff-only static checks do
  not verify that advertised typing surface. This satisfies the review trigger
  recorded by `DEC-013`.
- **Decision:** Keep Ruff as the lint/format authority and add mypy as a separate
  static check over public package modules plus a small downstream consumer
  fixture. Run mypy in pre-commit and hosted quality verification. Target the
  newest supported Python, currently 3.14, for mypy so current NumPy typing
  syntax is supported; Ruff remains targeted at Python 3.11 and the runtime/tox
  matrix enforces Python 3.11-3.14 compatibility. This decision supersedes the
  "sole static-analysis authority" part of `DEC-013`; its Ruff
  formatting/linting choice remains.
- **Alternatives considered:** remove `py.typed`; keep typing unchecked; add a
  type checker only as non-gating local tooling.
- **Compatibility consequence:** Runtime dependencies do not change. The
  development/quality dependency set gains mypy and locked CI must be refreshed
  by the maintainer before hosted verification.
- **Review trigger:** The package stops shipping `py.typed`, mypy no longer
  supports the project environment adequately, or another checker provides
  materially better evidence at acceptable maintenance cost.

## `DEC-030` — Verify the finite FE grid discontinuity structure exhaustively

- **Context:** The extended-precision defect showed that representative boundary
  samples can miss a dtype-specific table-index error. The FE lookup is piecewise
  constant inside one-degree cells and changes only at known integer-degree
  boundaries, so the complete discontinuity structure is small enough to test.
- **Decision:** Generate exhaustive coordinate-index corpora from integer world-cell
  and grid-boundary identities. Test every area cell at center and
  nearest-representable interior edge/corner values, and test previous/exact/next
  representable values around every integer grid intersection. Use independent
  synthetic probe tables for quadrant, latitude index, and longitude index rather
  than derive expected FE region numbers through the production conversion path.
  Run the corpus for float16, float32, float64, and wider longdouble where
  available.
- **Alternatives considered:** add more hand-picked decimal epsilon cases; use the
  real FE table as the only oracle; reproduce `int(abs(value))` in test code;
  exhaustively enumerate all floating-point bit patterns.
- **Compatibility consequence:** Runtime behavior and public APIs do not change.
  Test cost increases by a bounded vectorized corpus of roughly one million
  coordinates per dtype across the two complementary generators.
- **Review trigger:** The coordinate model, one-degree indexing rule, supported
  numeric dtype contract, or dense-table representation changes materially.

## `DEC-031` — Define geographical identifier validity from active table membership

- **Context:** Review of `0.2.0a3` found that the packaged names array retains
  historical names at retired identifiers 172, 299, and 550. Name lookup used
  non-empty name slots as its validity test, while hierarchy conversion treated
  those same identifiers as inactive. Custom engines could exhibit the same
  inconsistency for any named identifier not used by their lookup table.
- **Decision:** A geographical identifier is active for an engine only when the
  engine's geographical lookup table uses that identifier. Derive a read-only
  active-ID mask at engine construction. Scalar/vector geographical name lookup
  and geographical-to-seismic conversion must validate against that mask.
  Historical or otherwise unused name/crosswalk entries may be retained as data,
  but they do not create active public identifiers.
- **Alternatives considered:** allow historical-name lookup for retired IDs;
  remove historical name slots from the packaged names array; require every
  unused custom crosswalk entry to be zero.
- **Compatibility consequence:** Calls that previously resolved retained names
  for retired or unused geographical identifiers now raise `RegionNumberError`.
  Coordinate lookup behavior and active-ID results do not change.
- **Review trigger:** The package adds an explicit historical-region lookup API
  or adopts a source model where inactive identifiers are intentionally queryable.

## `DEC-032` — Align scalar coordinate typing with supported NumPy scalar behavior

- **Context:** Runtime scalar lookup intentionally accepts Python integer/float
  values and NumPy integer/floating scalars, but the distributed `py.typed`
  signatures used built-in `float` only. Downstream static checking could reject
  a value that runtime tests intentionally support.
- **Decision:** Publish `ScalarCoordinate` as the scalar coordinate input type and
  include Python `int`/`float` plus NumPy integer/floating scalar families.
  Runtime validation continues to reject Boolean values even though Python's
  static numeric subtype relationships cannot express that exclusion precisely.
  The downstream typing fixture must exercise representative NumPy scalar calls.
- **Alternatives considered:** narrow runtime support to built-in floats; remove
  `py.typed`; leave the mismatch documented only.
- **Compatibility consequence:** Static typing becomes less restrictive and
  matches supported runtime behavior more closely. Runtime behavior does not
  broaden.
- **Review trigger:** NumPy's public scalar typing model changes or the package
  changes its accepted scalar numeric families.

## `DEC-033` — Separate beta maturity from release-validation status

- **Context:** The project-specific alpha policy required all promotion gates to
  pass before using a beta identifier. The project decision owner explicitly
  selected a beta prerelease for the review-closure iteration while external scientific,
  hosted-CI, lock, performance, and source-license evidence can remain incomplete.
  The delivery guideline treats prerelease maturity and verification as separate
  dimensions.
- **Decision:** Beta identifies product maturity: intended `0.2`
  functionality is substantially complete and stabilization/broader validation
  can remain. Release-validation status remains independent. A beta source
  handoff may be issued with partial verification only when missing required
  evidence is explicit; it must not be described as promotion-gate complete or
  ready for unqualified external publication until the quality gates pass.
  This decision supersedes `DEC-008`.
- **Alternatives considered:** remain on the alpha line until all external gates
  can be observed; weaken or remove the external gates; treat beta as equivalent
  to complete validation.
- **Compatibility consequence:** Version maturity changes to beta without
  weakening any functional, compatibility, provenance, or release-validation
  acceptance condition.
- **Review trigger:** The project adopts a different prerelease policy or the
  release-validation gates become inappropriate for the intended distribution.


## `DEC-034` — Adopt split-vector lookup internally and keep the public matrix contract

- **Context:** `PERF-INV-001` measured material stacking and contiguity cost for
  callers that already own separate longitude and latitude arrays. The accepted
  beta baseline preserves source-dtype boundary correctness, and pandas is a
  concrete package consumer of separate vectors.
- **Decision:** Add package-internal equal-length one-dimensional longitude/latitude
  lookup paths and route pandas through them. Do not broadcast. Preserve the
  public `(n, 2)` NumPy batch API unchanged. Do not expose the split path publicly
  in this iteration.
- **Rationale/evidence:** Same-process controlled measurements show roughly
  1.5–1.8x improvement for already-split geographical workloads at 10k–1M points,
  with lower temporary memory. Internal adoption captures the demonstrated value
  without another public compatibility surface.
- **Compatibility consequence:** Public API behavior is unchanged. Private method
  names are not supported extension points.
- **Review trigger:** A real external consumer requires split vectors at scale, or
  measurements show material value unavailable through existing adapters.

## `DEC-035` — Trust only engine-produced geographical results in seismic composition

- **Context:** Coordinate-to-seismic batch lookup passed geographical numbers just
  produced by the engine back through the public geographical-number validator.
  That path validates arbitrary caller data and materializes large name-table
  selections that are redundant for engine-produced results.
- **Decision:** Coordinate lookup may index the already validated hierarchy
  crosswalk directly with geographical numbers produced by the same engine. Keep
  `geographic_numbers_to_seismic_numbers()` fully validating for arbitrary caller
  input.
- **Rationale/evidence:** Engine construction guarantees a nonzero seismic mapping
  for every geographical identifier used by its table. Exhaustive global-cell
  tests verify equivalence with the public conversion route. Controlled timings
  show about 2.0–3.0x improvement in public seismic batch lookup across 10k–1M
  points, and a 2M-point memory probe reduces additional RSS from about 264 MiB to
  about 20 MiB on the measured host.
- **Compatibility consequence:** Public results and error behavior for caller data
  remain unchanged; coordinate-to-seismic lookup avoids redundant validation.
- **Review trigger:** Engine construction invariants, table ownership, active-ID
  semantics, or hierarchy mutability changes.

## `DEC-036` — Classify the optimization as a new `0.3` minor line

- **Context:** The change is not a defect correction and does not add a public API,
  but controlled measurements show a material backward-compatible performance and
  memory change in supported batch and pandas behavior.
- **Decision:** Start minor line `0.3` and issue its first prerelease candidate as alpha.
  The MINOR increment communicates substantial backward-compatible behavior; alpha
  maturity reflects that the new optimized implementation still requires broader
  supported-environment stabilization.
- **Alternatives considered:** `0.2.0b2` as an internal-only stabilization change;
  a patch-style version because no public symbol changed; `0.3.0b1` while retaining
  beta maturity.
- **Compatibility consequence:** No intended public API or scientific-result
  incompatibility. Version consumers can identify the performance-focused minor
  line separately from the `0.2` beta baseline.
- **Review trigger:** Benchmark comparison does not reproduce a material gain on
  supported environments, or a later review identifies an unintended public
  compatibility change.


## `DEC-037` — Keep explicit-engine GeoJSON and make provenance claims conditional

- **Context:** `regions_geojson(..., lookup=...)` already accepts valid explicit
  engines, but `0.3.0a1` always emitted packaged FE-1995 scheme/revision metadata.
  Seismic child properties also enumerated every matching crosswalk slot instead
  of the engine's active geographical membership.
- **Decision:** Keep explicit-engine GeoJSON support. Geometry, names, hierarchy
  membership, and cross-level properties must follow the selected engine. Use an
  engine-owned active-membership helper for seismic child enumeration. Emit
  FE-1995 scheme/revision metadata only when the selected engine is the
  packaged default instance. Otherwise, emit null scheme/revision values while
  retaining engine-independent coordinate and boundary semantics.
- **Alternatives considered:** reject every explicit engine that is not the
  packaged singleton; add provenance fields to the public engine constructor;
  continue hard-coding packaged metadata.
- **Compatibility consequence:** Default packaged GeoJSON metadata and geometry
  remain unchanged. Explicit custom engines no longer receive unsupported
  FE-1995 provenance claims, and inactive crosswalk slots no longer leak into
  seismic child properties.
- **Review trigger:** The engine gains an explicit provenance contract, or GeoJSON
  metadata needs to distinguish additional named source datasets.


## `DEC-038` — Represent seismic geographical children as region objects

- **Context:** Seismic GeoJSON previously exposed child membership through two
  parallel properties, `geographic_numbers` and `geographic_names`. The
  positional relationship was easy to misuse, and the names looked like ordinary
  geographical feature properties even though the feature level was seismic.
  The CLI also required one `--property` option per requested field.
- **Decision:** Replace the parallel seismic child properties with one
  `geographic_regions` property containing ordered `{number, name}` objects.
  Reject scalar geographical properties and the legacy parallel child-list
  property names at seismic level. Add `--properties NAME [NAME ...]` and the
  level-aware `--properties all` shorthand while retaining repeatable
  `--property NAME` for CLI compatibility.
- **Alternatives rejected:** Keep parallel number/name arrays; permit arbitrary
  cross-level property permutations; remove the compatibility `--property` form.
- **Compatibility consequence:** The alpha GeoJSON property vocabulary changes
  for callers that explicitly requested `geographic_numbers` or
  `geographic_names`. Default GeoJSON properties and geometry are unchanged.
- **Review trigger:** A concrete downstream GeoJSON schema requires a different
  representation of parent/child region relationships.
