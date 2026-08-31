# feregion quality assurance and release gates

| Field | Value |
|---|---|
| Status | Current alpha quality contract |

## Purpose

This document defines the quality properties and evidence gates used to decide
whether a `feregion` source state is acceptable for delivery and whether its
maturity can advance. A process result supports only the claim named by its
gate. A passing test, CI job, linter, build, or checksum does not establish a
stronger product claim by itself.

## Quality contract

| Field | Project interpretation |
|---|---|
| Product | Installable Python package for FE geographical and seismic lookup, hierarchy conversion, packaged names, pandas annotation, CSV processing, and derived GeoJSON |
| Users | Python callers, data-processing users, CLI users, and project maintainers |
| Runtime context | Offline lookup from packaged generated assets; no runtime network dependency |
| Development context | `uv`-managed Python project; upstream ObsPy and ISC FE sources are fetched only for regeneration/reference verification |
| Declared Python environment | Python 3.11 or newer; hosted verification is required for 3.11, 3.12, 3.13, and 3.14 |
| Public contracts | Python API, exception semantics, pandas adapter, CLI behavior and exit status, generated GeoJSON semantics, package metadata and extras |
| Specialist concerns | Upstream-data provenance and redistribution status; general review does not provide legal advice or specialist license approval |
| Release evidence | Contract-linked tests, reference-oracle comparisons, branch coverage as an omission signal, static checks, dependency compatibility, package inspection/install, benchmarks, documentation consistency, and source-delivery replay |

## Selected quality scenarios

| Quality | Scenario | Acceptance condition | Primary evidence |
|---|---|---|---|
| Functional suitability | Valid scalar and batch coordinates are mapped | Results match the pinned source-table scanner over the complete integer grid and deterministic fractional samples; direct ObsPy sample agrees when the oracle is installed | source-reproduction tests and ObsPy oracle job |
| Coordinate-index fidelity | A supported floating coordinate is at, or as close as representable to, an FE integer-degree discontinuity | Every area cell and every integer grid-vertex neighborhood selects the independently constructed quadrant, absolute-latitude index, and absolute-longitude index for float16/32/64 and wider longdouble where available | exhaustive synthetic grid-index probe tests |
| Hierarchy consistency | A geographical result is converted to its seismic parent | Every active geographical ID maps exactly once; all 50 seismic IDs occur; exhaustive global-cell seismic lookup equals geographical lookup plus crosswalk | packaged-asset and seismic exhaustive tests |
| Offline operation | An installed user performs lookup, names, hierarchy conversion, adapters, or GeoJSON without source access | Runtime package contains processed geographical and seismic assets and makes no network request | wheel contents/install smoke plus runtime tests |
| Failure semantics | Invalid input reaches a public boundary | The documented package exception or CLI status is produced without silent coercion, semantic reclassification, destructive file publication, or unbounded traceback | exact-exception tests, CLI subprocess/boundary tests |
| Performance efficiency | Batch lookup handles representative arrays and supported Python versions | Benchmark results are recorded with environment, repeated timings, same-workload source-table baseline, and correctness checks; release regression compares a named accepted prior-package record in the same recorded environment; an unexplained slowdown greater than 25% at two adjacent sizes of at least 10,000 points triggers review; absent comparable baseline means the release gate is incomplete | standalone benchmark, release comparison, cross-Python comparison, and retained raw records |
| Compatibility | Supported API, CLI, Python, dependency, and packaging surfaces change | No unapproved incompatibility is introduced; local tox-uv matrix, current-dependency CI, lower-bound CI, package metadata inspection, and installed-wheel smoke checks pass | tox-uv matrix, CI matrix, lower-bound job, wheel verifier |
| Reliability | Concurrent initialization or CSV file publication fails or races | Single-flight initialization remains deterministic; failed filesystem CSV processing does not replace the destination; documented stdout partial-result behavior remains visible | concurrency and CSV failure tests |
| Public usability | A caller invokes or diagnoses a supported interface | README and public docstrings state inputs, outputs, important invariants, failure behavior, and recovery constraints needed by the caller | documentation review and executable examples/tests |
| Maintainability | A future maintainer changes a public behavior or release rule | The governing requirement, design decision, relevant tests, traceability, and release gate can be located without relying on historical chat context | repository knowledge-consistency tests and decision ledger |
| Provenance/integrity | Generated FE assets or source identity change | Declared source inputs and normalized hierarchy semantics match their pinned identities/hashes; all four runtime arrays match recorded hashes; unresolved source-data license status remains explicit | source acquisition/reproduction tests, asset metadata checks, wheel/source-delivery verification |

## Release gates

| Gate | Claim controlled | Required evidence | Acceptance condition | Exception authority | Retained evidence |
|---|---|---|---|---|---|
| `QG-FUNC` | Specified FE behavior is implemented | Full runtime suite plus source-table reproduction; direct ObsPy oracle in hosted CI | Required tests pass on the exact target source; skips are separately identified | Project decision owner | verification record and CI result |
| `QG-COMP` | Declared compatibility has evidence | Local tox-uv Python 3.11–3.14 matrix, shared lower-bound environment, hosted matrix, public-boundary regressions | All configured compatibility checks pass or an exception records the lost guarantee | Project decision owner | local matrix record, CI result, and release review |
| `QG-STATIC` | Configured static checks are clean | Ruff formatting/lint plus mypy public-package and downstream-consumer typing on the exact target source | Configured Ruff and mypy checks pass | Project decision owner; exception must identify unchecked rule/scope | CI/static-check log |
| `QG-CI` | CI executes a reproducible declared tool/dependency state | Compatible constrained uv, committed `uv.lock`, `uv sync --locked`, bounded job timeouts, and concurrency cancellation | Workflow syntax is valid; lock-preserving jobs pass on the exact candidate state | Project decision owner | workflow, lock, and CI run |
| `QG-PKG` | Built distributions contain and install the intended product | `uv build`, wheel archive inspection, dependency-isolated wheel installation and smoke checks | Build succeeds; wheel contents/metadata meet the package contract; installed smoke checks pass | Project decision owner | verification record and package hashes |
| `QG-PERF` | Performance claims remain bounded by evidence | Candidate and named accepted prior-package raw benchmark JSON from the same recorded host/interpreter/dependency/workload context; release comparison; source-table comparison; lock-backed Python 3.11–3.14 comparison | Correctness checks pass; comparable baseline/candidate records exist; the >25% two-adjacent-size trigger is not crossed without disposition; otherwise the gate is incomplete | Project decision owner | baseline and candidate raw JSON, release comparison, per-Python JSON and comparison report |
| `QG-PROV` | Upstream and generated-data identity is known to the stated level | Pinned ObsPy source hashes; literal reviewed ISC semantic hash independent from hierarchy declarations; generated-asset SHA-256 checks; multi-source metadata and third-party notice review | Identity checks pass and unresolved license/provenance limitations remain explicit; live ISC comparison is scheduled/manual integration evidence | Source-data license disposition requires qualified/human decision | semantic-pin record, metadata, notices, verification record |
| `QG-DOC` | Maintained knowledge matches the target behavior | Contract/document synchronization tests plus semantic review | Current requirements/design/quality/decision/traceability set matches the changed public and repository behavior | Project decision owner | source documents and review record |
| `QG-DELIVERY` | The exported source handoff is replayable | Full source archive, exact-baseline patch, manifest, checksums, patch application and tree comparison | Patch reconstructs target byte-for-byte; archive safety and checksums pass | Project decision owner | delivery manifest, checksums, patch, verification record |

## Maturity and release-validation decision

Prerelease identifiers describe maturity for the current minor line and remain
separate from release-validation status. `0.2.0b1` marked the substantially
complete `0.2` functionality as beta. the first `0.3` prerelease starts a new minor line because
the batch optimization produces a material backward-compatible performance
change; that new implementation starts at alpha while stabilization and broader
validation continue. Alpha or beta maturity does not mean that all release gates
passed, that scientific validation is complete, or that public distribution is
approved.

A beta candidate must not be described as **release-validated**,
**promotion-gate complete**, or ready for unqualified external publication
unless all of these conditions hold on one exact candidate source state:

1. `QG-FUNC`, `QG-COMP`, `QG-STATIC`, `QG-PKG`, `QG-PERF`, `QG-DOC`, and
   `QG-DELIVERY` pass with no undisclosed skip or unavailable required check.
2. The direct installed-ObsPy oracle runs successfully rather than being
   represented only by an optional skip.
3. The committed `uv.lock` is current for the exact candidate source and locked
   CI verification passes.
4. The unresolved historical FE source-data license/provenance question has an
   explicit human or qualified disposition appropriate to the intended
   distribution. This document does not provide that legal determination.
5. No open major behavioral or data-loss defect remains.

An explicitly authorized beta source handoff may have partial verification.
Every unavailable or failed required gate must remain visible in its delivery
evidence and retains its normal blocking effect on stronger release claims.

## Evidence recording rule

Release-specific unavailable checks, local environment limits, skips, and
dependency-resolution failures belong in delivery or CI evidence. This
maintained document defines the required gates; it must not claim that a gate
passed merely because the repository contains its configuration.
