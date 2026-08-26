# feregion decision record

| Field | Value |
|---|---|
| Document version | `0.1.1a3` |
| Implementation target | `0.1.1a3` |
| Document date | `2026-08-26` |
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

## `DEC-008` — Keep `0.1.1a3` at alpha maturity

- **Context:** Core behavior is mature relative to earlier iterations, but
  release evidence is incomplete across static checks, dependency locking,
  hosted compatibility jobs, and source-data license disposition.
- **Decision:** Deliver the next correction as `0.1.1a3`; do not promote to beta.
- **Alternatives considered:** `0.1.1b1`; a new minor line; final `0.1.1`.
- **Compatibility consequence:** The public API remains backward-compatible;
  this iteration fixes boundary failures and strengthens assurance.
- **Review trigger:** Apply the beta conditions in the current quality-assurance
  document to one exact candidate source state.
