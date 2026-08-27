# feregion repository and delivery requirements

| Field | Value |
|---|---|
| Status | Implemented alpha repository/delivery contract |

This document uses the normative profile defined by `feregion-requirements.md`.

## Repository boundary

**REQ-REPO-001** — The source archive must use one stable internal
`feregion/` repository root. Project version and delivery date must appear in
outer delivery filenames, not in that root name.

**REQ-REPO-002** — Maintained requirements, design, quality-assurance, decision,
and verification-traceability documents must use stable repository filenames.
Git history records their revisions. The maintained files are:

- `docs/feregion-requirements.md`;
- `docs/feregion-engineering-requirements.md`;
- `docs/feregion-repository-delivery-requirements.md`;
- `docs/feregion-design.md`;
- `docs/feregion-quality-assurance.md`;
- `docs/feregion-decisions.md`; and
- `docs/feregion-verification-traceability.md`.

A repository change that affects one of these contracts must update the stable
file in the same change. Release version and date belong in Git history,
`CHANGELOG.md`, package metadata, and exported delivery artifacts instead of the
maintained document filename or banner.

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
generated runtime assets, tests, project metadata, or the committed `uv.lock`.

**REQ-REPO-007** — The repository must contain one active maintained contract
set at the stable paths defined in this document. Superseded versions must remain
recoverable through Git history instead of being copied into new version-named
repository files. Historical delivery-side artifacts remain outside the source
tree.

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

**REQ-REPO-010** — The repository must provide a maintainer command that exports a
clean handoff ZIP from Git-tracked working-tree files. The exporter must preserve
current tracked file bytes and executable state, exclude `uv.lock` even when it
is tracked, exclude ignored and untracked local state by default, warn when
non-ignored untracked files are omitted, and provide a strict mode that fails on
such untracked files. The archive must be deterministic for an unchanged working
tree and must use the stable `feregion/` internal root.

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

**REQ-DEL-005** — `uv.lock` is local repository state for dependency resolution
and must be excluded from delivered source archives and incremental patches. If
a supplied baseline patch contains `uv.lock` changes, delivery reconstruction
must ignore those hunks. The maintainer regenerates or updates `uv.lock` locally
after applying source changes.
