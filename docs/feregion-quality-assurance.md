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
| Product | Installable Python package for Flinn-Engdahl region-number lookup, optional names, pandas annotation, CSV processing, and derived GeoJSON |
| Users | Python callers, data-processing users, CLI users, and project maintainers |
| Runtime context | Offline lookup from packaged generated assets; no runtime network dependency |
| Development context | `uv`-managed Python project; upstream FE source tables are fetched only for regeneration/reference verification |
| Declared Python environment | Python 3.11 or newer; hosted verification is required for 3.11, 3.12, 3.13, and 3.14 |
| Public contracts | Python API, exception semantics, pandas adapter, CLI behavior and exit status, generated GeoJSON semantics, package metadata and extras |
| Specialist concerns | Upstream-data provenance and redistribution status; general review does not provide legal advice or specialist license approval |
| Release evidence | Contract-linked tests, reference-oracle comparisons, branch coverage as an omission signal, static checks, dependency compatibility, package inspection/install, benchmarks, documentation consistency, and source-delivery replay |

## Selected quality scenarios

| Quality | Scenario | Acceptance condition | Primary evidence |
|---|---|---|---|
| Functional suitability | Valid scalar and batch coordinates are mapped | Results match the pinned source-table scanner over the complete integer grid and deterministic fractional samples; direct ObsPy sample agrees when the oracle is installed | source-reproduction tests and ObsPy oracle job |
| Failure semantics | Invalid input reaches a public boundary | The documented package exception or CLI status is produced without silent coercion, semantic reclassification, destructive file publication, or unbounded traceback | exact-exception tests, CLI subprocess/boundary tests |
| Performance efficiency | Batch lookup handles representative arrays | Benchmark results are recorded with environment, repeated timings, same-workload source-table baseline, and correctness checks; an unexplained slowdown greater than 25% at two adjacent sizes of at least 10,000 points triggers review | standalone benchmark and comparison table |
| Compatibility | Supported API, CLI, Python, dependency, and packaging surfaces change | No unapproved incompatibility is introduced; current-dependency CI, lower-bound CI, package metadata inspection, and installed-wheel smoke checks pass | CI matrix, lower-bound job, wheel verifier |
| Reliability | Concurrent initialization or CSV file publication fails or races | Single-flight initialization remains deterministic; failed filesystem CSV processing does not replace the destination; documented stdout partial-result behavior remains visible | concurrency and CSV failure tests |
| Public usability | A caller invokes or diagnoses a supported interface | README and public docstrings state inputs, outputs, important invariants, failure behavior, and recovery constraints needed by the caller | documentation review and executable examples/tests |
| Maintainability | A future maintainer changes a public behavior or release rule | The governing requirement, design decision, relevant tests, traceability, and release gate can be located without relying on historical chat context | repository knowledge-consistency tests and decision ledger |
| Provenance/integrity | Generated FE assets or source identity change | Source files and generated assets match pinned identities/hashes; wheel and source delivery hashes are verified; unresolved source-data license status remains explicit | source hash checks, asset metadata checks, wheel/source-delivery verification |

## Release gates

| Gate | Claim controlled | Required evidence | Acceptance condition | Exception authority | Retained evidence |
|---|---|---|---|---|---|
| `QG-FUNC` | Specified FE behavior is implemented | Full runtime suite plus source-table reproduction; direct ObsPy oracle in hosted CI | Required tests pass on the exact target source; skips are separately identified | Project decision owner | verification record and CI result |
| `QG-COMP` | Declared compatibility has evidence | Python 3.11–3.14 matrix, lower-bound dependency job, public-boundary regressions | All configured compatibility jobs pass or an exception records the lost guarantee | Project decision owner | CI result and release review |
| `QG-STATIC` | Configured static checks are clean | Ruff formatting and linting on the exact target source | Both Ruff checks pass | Project decision owner; exception must identify unchecked Ruff rule/scope | CI/static-check log |
| `QG-CI` | CI executes a reproducible declared tool/dependency state | Pinned uv, committed `uv.lock`, `uv sync --locked`, bounded job timeouts, and concurrency cancellation | Workflow syntax is valid; lock-preserving jobs pass on the exact candidate state | Project decision owner | workflow, lock, and CI run |
| `QG-PKG` | Built distributions contain and install the intended product | `uv build`, wheel archive inspection, dependency-isolated wheel installation and smoke checks | Build succeeds; wheel contents/metadata meet the package contract; installed smoke checks pass | Project decision owner | verification record and package hashes |
| `QG-PERF` | Performance claims remain bounded by evidence | Repeated benchmark table and source-table comparison | Report exists and correctness checks pass; review trigger above is not crossed without disposition | Project decision owner | benchmark JSON and report |
| `QG-PROV` | Upstream and generated-data identity is known to the stated level | Pinned ObsPy commit and source SHA-256 checks; generated-asset SHA-256 checks; third-party notice review | Identity checks pass and unresolved license/provenance limitations remain explicit | Source-data license disposition requires qualified/human decision | metadata, notices, verification record |
| `QG-DOC` | Maintained knowledge matches the target behavior | Contract/document synchronization tests plus semantic review | Current requirements/design/quality/decision/traceability set matches the changed public and repository behavior | Project decision owner | source documents and review record |
| `QG-DELIVERY` | The exported source handoff is replayable | Full source archive, exact-baseline patch, manifest, checksums, patch application and tree comparison | Patch reconstructs target byte-for-byte; archive safety and checksums pass | Project decision owner | delivery manifest, checksums, patch, verification record |

## Maturity decision

The project remains **alpha** until the beta-promotion gates pass. The core lookup design is stable, but the
project does not yet have enough observed release evidence to call the intended
functionality substantially stabilized across its declared development and
compatibility surfaces.

Promotion to beta requires all of these conditions on one exact candidate
source state:

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

## Evidence recording rule

Release-specific unavailable checks, local environment limits, skips, and
dependency-resolution failures belong in delivery or CI evidence. This
maintained document defines the required gates; it must not claim that a gate
passed merely because the repository contains its configuration.
