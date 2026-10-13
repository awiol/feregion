# feregion quality assurance and release gates

| Field | Value |
|---|---|
| Status | Current beta quality contract |
| Current target | `0.5` evidence-backed optimization implementation; public contract unchanged |

The ASV-derived path is the primary benchmark authority; the 0.4 migration is closed.

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
| Performance efficiency | Batch lookup handles representative arrays, historical package revisions, and selected Python/NumPy/pandas environments | The applicable benchmark system records workload/case identity, environment, repeated measurements, and correctness evidence; release regression compares a named accepted prior-package record under the same comparison contract; an unexplained slowdown greater than 25% at two adjacent sizes of at least 10,000 points triggers review; absent comparable baseline means the release gate is incomplete | `0.3`: predecessor standalone/release comparison evidence; `0.4` target: project benchmark contract, retained ASV raw samples/history, normalized evidence, and public-history report |
| Compatibility | Supported API, CLI, Python, dependency, and packaging surfaces change | No unapproved incompatibility is introduced; local tox-uv matrix, current-dependency CI, lower-bound CI, package metadata inspection, and installed-wheel smoke checks pass | tox-uv matrix, CI matrix, lower-bound job, wheel verifier |
| Reliability | Concurrent initialization or CSV file publication fails or races | Single-flight initialization remains deterministic; failed filesystem CSV processing does not replace the destination; documented stdout partial-result behavior remains visible | concurrency and CSV failure tests |
| Public usability | A caller invokes, diagnoses, or evaluates an upgrade to a supported interface | README, public docstrings, and the maintained cumulative `docs/whats-new.md` guide state the applicable inputs, outputs, important invariants, practical release impact, compatibility/migration context, and recovery constraints needed by the caller | documentation review, release-history synchronization tests, and executable examples/tests |
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
| `QG-BENCH` | The `0.4` ASV benchmark system preserves its declared semantic, environment, evidence, and operator contract | Source-oracle sensitivity tests; stored benchmark-version mapping fixtures; state/run/environment/report sidecars; campaign/Git/build-install boundary tests; requested-versus-observed dependency preflight; campaign-profile evidence-binding tests; comparator/diagnostic parity tests; evidence-bundle tests; raw/nested-sample normalization; throughput-gate parity tests; OutputPublisher and release-workflow tests; real ASV vertical slice | Wrong-but-in-range output is rejected before timing; requested dependency versions/imports and `pip check` pass; unknown stored benchmark versions are incompatible; not-applicable/build/correctness/execution/measured states remain distinguishable; operations-per-second is retained; throughput gate matches the predecessor decision; handoff preserves machine-readable evidence without derived HTML; normalized evidence cannot cross environment-profile boundaries; report rebuild retains its source-evidence identity; corrected real ASV reference/diagnostic evidence succeeds | Project decision owner | predecessor benchmark evidence plus ASV result/state/run/environment/report preservation set, normalized evidence, evidence handoff, parity review, project check output, generated site |
| `QG-PERF` | Performance claims remain bounded by evidence | After accepted `REQ-PERF-017` migration evidence, ASV plus the project-owned campaign/evidence/regression layers are the primary performance-evidence path; predecessor tooling remains compatibility/reference evidence and provenance. | Correctness-sensitive evidence exists on one comparable context; median throughput slowdown exceeds 25% at no two adjacent maintained loads without disposition; direct ObsPy/source comparisons are cited only when actually run; otherwise the gate is incomplete. | Project decision owner | retained ASV result/state/run/environment/report evidence, normalized release comparison, and parity review; predecessor evidence when relevant |
| `QG-OPT` | A `0.5` runtime optimization is selected from mechanism-level evidence rather than intuition | Exact-baseline mechanism probes plus maintained ASV aggregate diagnostics; semantic equivalence checks; implementation-specific predecessor/candidate comparisons; direct interface measurements before any public-shape decision | Each implemented optimization has a measured material mechanism, a semantic oracle, and predecessor/candidate evidence; public interfaces or representations change only under a separate compatibility decision | Project decision owner | retained optimization evidence, `DEC-066..070`, semantic regressions, and predecessor/candidate comparisons |
| `QG-PROV` | Upstream and generated-data identity is known to the stated level | Pinned ObsPy source hashes; literal reviewed ISC semantic hash independent from hierarchy declarations; generated-asset SHA-256 checks; multi-source metadata and third-party notice review | Identity checks pass and unresolved license/provenance limitations remain explicit; live ISC comparison is scheduled/manual integration evidence | Source-data license disposition requires qualified/human decision | semantic-pin record, metadata, notices, verification record |
| `QG-DOC` | Maintained knowledge and user-facing release history match the target behavior | Contract/document synchronization tests, cumulative What’s New coverage checks, plus semantic review | Current requirements/design/quality/decision/traceability set matches the changed public and repository behavior; `docs/whats-new.md` covers every changelog minor line and exact release/candidate and accurately explains user-relevant changes without overstating evidence | Project decision owner | source documents, `docs/whats-new.md`, synchronization-test result, and review record |
| `QG-CLOSE-DOC` | Final `0.4` user/maintainer documentation is fit for migration and use | Documentation review against public interfaces plus retained performance evidence | Purpose, usage, nuances, limitations, optional integrations, compatibility guidance, and bounded measured performance are documented | Project decision owner | final documentation review and cited measurement evidence |
| `QG-CLOSE-DEPRECATION` | Final `0.4` warns for adopted `0.5` incompatibilities without breaking early | Adopted `0.5` decision inventory plus warning emission/suppression tests | Every applicable adopted incompatibility has a suppressible warning and replacement guidance where available; proposed-only changes are excluded | Project decision owner | adopted decision inventory and deprecation regressions |
| `QG-DELIVERY` | The exported source handoff is replayable | Full source archive, exact-baseline patch, manifest, checksums, patch application and tree comparison | Patch reconstructs target byte-for-byte; archive safety and checksums pass | Project decision owner | delivery manifest, checksums, patch, verification record |

## Maturity and release-validation decision

Prerelease identifiers describe maturity for one target line and remain separate
from release-validation status. The rebased `0.5` line is the active beta target,
now inheriting exact committed `0.4.0b10`. `DEC-062` retains the ASV-derived path
as primary benchmark authority, while the later 0.4 provenance, containment, evidence-
integrity, review-closure, documentation, and formatting corrections remain inherited
repository behavior. Runtime optimization is not authorized by maturity alone; `QG-OPT`
and `REQ-OPT-005` control each implementation decision. The geographical validation,
seismic validation, and pandas name-output implementations are selected by `DEC-067`,
`DEC-068`, and `DEC-069`; `DEC-070` keeps the matrix API unchanged in `0.5` and
defers an additive public split-vector interface to `0.6`. `DEC-073` records the
rebase and identifier reconciliation. Release-validation remains partial.

The completed `0.4` benchmark migration and final-0.4 closure controls remain applicable
as inherited contract/evidence. `QG-BENCH` passed for the accepted migration under
`DEC-062`; `QG-CLOSE-DOC` and `QG-CLOSE-DEPRECATION` remain records of the final 0.4
closure obligations. No deprecation is introduced merely by rebasing 0.5. Exact
candidate benchmark, static, packaging, source-oracle, and hosted-CI outcomes remain
release evidence rather than assumptions.

Alpha or beta maturity does not mean that all applicable release gates passed,
that scientific validation is complete, or that public distribution is approved.

A beta candidate must not be described as **release-validated**,
**promotion-gate complete**, or ready for unqualified external publication
unless all of these conditions hold on one exact candidate source state:

1. `QG-FUNC`, `QG-COMP`, `QG-STATIC`, `QG-PKG`, `QG-PERF`, `QG-DOC`, and
   `QG-DELIVERY` pass with no undisclosed skip or unavailable required check.
   `QG-BENCH` is additionally required for a `0.4` candidate whose benchmark
   implementation is in scope.
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
