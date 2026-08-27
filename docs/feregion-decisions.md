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
  local hooks that run Ruff format, Ruff check, and pytest through `uv --no-sync`.
- **Alternatives considered:** hook-managed Ruff environments; a custom shell
  script; no commit-time checks.
- **Compatibility consequence:** Developers must run `uv sync --group dev` before
  installing hooks. Package runtime dependencies do not change.
- **Review trigger:** Commit-time full pytest becomes materially too expensive or
  repository tooling moves away from `uv`/pre-commit.

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
  `sync --locked`, `run --locked`, `build --locked`, and `python install`, not on
  behavior unique to one uv release.
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
