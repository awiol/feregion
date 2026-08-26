# feregion repository and delivery requirements

| Field | Value |
|---|---|
| Requirements document version | `0.1.1a3` |
| Implementation target | `0.1.1a3` |
| Document date | `2026-08-26` |
| Current filename | `feregion-repository-delivery-requirements-v0.1.1a3-2026-08-26.md` |
| Status | Implemented alpha repository/delivery contract |

This document uses the normative profile defined by `feregion-requirements-v0.1.1a3-2026-08-26.md`.

## Repository boundary

**REQ-REPO-001** — The source archive must use one stable internal
`feregion/` repository root. Project version and delivery date must appear in
outer delivery filenames, not in that root name.

**REQ-REPO-002** — Requirements and design documents are versioned project
artifacts. Their filenames must contain project version and UTC date. For this
iteration they are:

- `docs/feregion-requirements-v0.1.1a3-2026-08-26.md`;
- `docs/feregion-engineering-requirements-v0.1.1a3-2026-08-26.md`;
- `docs/feregion-repository-delivery-requirements-v0.1.1a3-2026-08-26.md`;
- `docs/feregion-design-v0.1.1a3-2026-08-26.md`;
- `docs/feregion-quality-assurance-v0.1.1a3-2026-08-26.md`;
- `docs/feregion-decisions-v0.1.1a3-2026-08-26.md`; and
- `docs/feregion-verification-traceability-v0.1.1a3-2026-08-26.md`.

A new iteration must intentionally rename the versioned contract set and update
repository references in the same change. This is an explicit project naming
policy for these documents.

**REQ-REPO-003** — Benchmark harnesses must remain source-controlled developer
tooling. Generated benchmark reports, raw benchmark result files, coverage
reports, and per-iteration review reports must remain outside the repository
source tree unless a later project policy explicitly makes one of those
artifacts product source.

**REQ-REPO-004** — A delivered full-source archive must exclude
version-control internals, caches, bytecode, local coverage state, build
products, and prior delivery containers.

**REQ-REPO-005** — Repository verification commands must not hard-code a
pre-release-specific distribution filename when project metadata or `uv build`
can determine it.

**REQ-REPO-006** — `.gitignore` must cover local environments, Python/tool
caches, coverage output, benchmark output, build products, and retrieved
upstream source data. It must not ignore requirements, design documents,
generated runtime assets, tests, project metadata, or a future `uv.lock`.

**REQ-REPO-007** — The repository must contain only the current versioned
requirements, design, quality-assurance, decision, and verification-traceability
iteration. A new delivery must rename those files, update their version/date
metadata, remove superseded filenames, and update all internal references in
the same change.

**REQ-REPO-008** — Consequential architecture, compatibility, provenance, and
release-maturity decisions must be recorded in the current decision document
with context, selected option, relevant alternatives, evidence or assumptions,
compatibility consequences, and a review trigger. A later change must preserve
supersession rather than rewriting the prior rationale as if the new decision
had always applied.

**REQ-REPO-009** — Verification traceability must distinguish the intended
assessment method from the observed release result. Environment-dependent or
delivery-dependent requirements must identify their required environment or
release evidence instead of being marked verified solely because a related
test or workflow exists.

## Iterative delivery contract

**REQ-DEL-001** — Each iterative source delivery must provide a complete
versioned source archive, a versioned delivery manifest, and a versioned SHA-256
checksum list. When the exact prior delivered source is available, it must also
provide an incremental Git patch from that exact baseline.

**REQ-DEL-002** — The delivery manifest must record baseline identity, target
version, patch status, source/archive hashes, generation provenance, review
state, approval state, verification state, exclusions, and material
limitations. Review, approval, and verification must remain separate from the
alpha/beta/rc maturity identifier.

**REQ-DEL-003** — Generated benchmark results, verification logs, and
per-iteration review evidence must be delivery-side artifacts, not repository
source. When four or more related evidence files are delivered, they must be
bundled with an index.

**REQ-DEL-004** — Final delivery hashes must be calculated after the artifacts
are complete. The patch must be checked against the exact baseline and must
reconstruct the target source tree byte-for-byte except for explicitly recorded
metadata exclusions.
