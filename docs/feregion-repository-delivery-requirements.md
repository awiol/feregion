# feregion repository and delivery requirements

| Field | Value |
|---|---|
| Status | Implemented beta repository/delivery contract |

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
such untracked files. By default, the exporter must write the archive under the
repository `dist/` directory with package version and UTC date in the outer
filename (`feregion-v<version>-<YYYY-MM-DD>-handoff.zip`). An explicit output
path may override that default. The archive must be deterministic for unchanged
working-tree bytes and a fixed output identity, and must use the stable
`feregion/` internal root.

**REQ-REPO-011** — Repository handoff and retained-evidence export must not
silently cross a filesystem or archive containment boundary. Tracked symbolic links,
including broken symbolic links, and retained-evidence symbolic links or special files
must fail explicitly instead of being dereferenced or omitted as if absent. Project and
version values used as archive identity components must be safe single path components,
and every final ZIP member path must be relative, contain no parent traversal, and remain
under the intended internal archive root. Retained-evidence collection must validate
every directory component between the repository boundary and each selected evidence
root without following symbolic links; specialized evidence families must use the same
containment mechanism as generic recursive evidence discovery.

**REQ-REPO-012** — The repository must maintain one stable cumulative user-facing
release guide at `docs/whats-new.md`. The guide must contain exactly one chapter
for every minor release line represented in `CHANGELOG.md`, and it must contain
an exact-version subsection for every release candidate or release recorded in
that changelog. Every newly issued candidate must update the guide in the same
source change; a new minor line must add its chapter when that line is first
issued. Each minor chapter must explain the line's purpose and practical impact,
state material compatibility or migration implications, and include representative
usage examples when a supported user or maintainer interface changed. Individual
release subsections may be concise when a candidate is documentation-only or
otherwise has no additional user-facing behavior, but they must still identify
its role. Behavioral and performance claims in the guide must remain derived from
the maintained contract and retained evidence, and measured results must preserve
their stated limitations. The guide is explanatory user documentation: it must
not override requirements, decisions, verification status, or `CHANGELOG.md`.
`README.md` must link to the stable guide.

**REQ-REPO-013** — The repository must maintain one stable task-oriented user guide at
`docs/user-guide.md`. The guide must help a caller choose the public interface that
matches the input representation and requested FE result; explain coordinate ordering,
range/reference-frame conventions, matrix versus split-vector semantics, output dtypes,
important validation/error behavior, name and hierarchy conversion, pandas/CSV/GeoJSON
nuances, explicit-engine behavior, and material limitations; and distinguish compatibility
aliases from the preferred explicit geographical/seismic interfaces. Performance guidance
must identify the measured revision, workload, environment, method, and interpretation
limits for quantitative claims, and must separate scalar, batch, interface-shape, and
release-regression evidence rather than presenting them as one universal speed claim.
`README.md` must remain a usable quick start and link to the task-oriented guide. When a
public interface, nuance, limitation, or decision-relevant performance observation changes,
the affected user guide section must be reviewed in the same source change.

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

For the maintained `feregion-delivery/v1` schema, `schema` must equal
`feregion-delivery/v1` and `project` must equal `feregion`. `baseline` must be a
non-empty object containing one valid project version (`version` or
`declared_version`) plus at least one immutable SHA-256, Git commit, or Git tree
identity. `target_version` must use the project's `MAJOR.MINOR.PATCH` form with an
optional `aN`, `bN`, or `rcN` suffix. Each patch/review/approval/verification field
must be an object with a non-empty lowercase hyphenated `state` token. `artifacts`
must be a non-empty object whose records each contain a non-empty `role` and a valid
lowercase SHA-256; at least one record must identify a source archive/handoff, and a
non-omitted patch state must have a patch/replay artifact. `generation_provenance`
must record non-empty `source` and `scope` values plus at least one generator/tool,
command, exporter, or candidate-tree identity. `exclusions` and `limitations` must be
JSON arrays containing only non-empty strings; an empty array is permitted.

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
