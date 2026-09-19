# Benchmark harness planned enhancements

## Status

This document records **planned or investigatory work**, not implemented requirements.
The current `0.4` beta line preserves the a10 evidence-semantic repairs and restored
predecessor case/metric roles. b2 adds environment-integrity verification and a
machine-readable evidence-handoff command. ASV remains a secondary migration candidate
until `REQ-PERF-017` is closed; the predecessor benchmark harness remains authoritative
in that interval.

## Migration closure

1. Rerun the corrected b2 `reference-comparison` profile and require a finite direct
   ObsPy result plus a passing retained environment-integrity record. b1 reference and
   diagnostic execution is observed, but the b1 ObsPy environment was invalid.
2. Reconcile predecessor and ASV case/metric parity using
   `benchmark-migration-parity.md`, including operations-per-second, direct ObsPy/source
   comparators, pandas in-place, and internal diagnostics.
3. Complete real failure-state evidence. `correctness_passed` and genuine historical
   `not_applicable` are observed; b2 can now retain environment/build failure directly.
   Controlled `correctness_failed`, `execution_failed`, and incompatible-version evidence
   remains useful migration-closure material.
4. Verify the corrected throughput gate against the predecessor release comparator on
   the same retained baseline/candidate evidence.
5. Only after reviewed parity closure, decide whether ASV becomes the primary benchmark
   authority and which predecessor paths may be retired. Do not remove them merely
   because equivalent source code exists.

## Reporting and interpretation

6. Evaluate richer native graph interaction without taking ownership of a full plotting
   engine: hover text with series/environment identity, tag/revision, load, value,
   operations-per-second, and relative reference value; legend-hover highlighting; and
   non-color cues for dense comparisons.
7. Add report-freshness detection so an operator cannot silently view HTML older than
   retained measurement evidence.
8. Add coverage/completeness summaries that distinguish all project evidence states and
   stored benchmark-version incompatibility.
9. Evaluate a compact throughput/scaling summary on the feregion OutputPublisher page,
   while leaving ASV's native graph/regression implementation intact.

## Evidence and provenance

10. Extend campaign-run records with ASV/asv-runner version, start/end timestamps, and
    references/hashes for result files updated by the run.
11. Improve multi-machine evidence handling without combining incomparable hosts into a
    release decision.
12. Retain report-regeneration metadata so a published report identifies the exact
    retained result/state/run evidence from which it was produced.
13. Define the durable retention/location policy for evidence handoff archives and the
    preservation-set source directories. The b2 handoff command now exports results,
    state, run, and environment evidence, but repository policy still needs to define
    where long-lived archives are stored and pruned.

## Benchmark coverage and investigation

14. Reconcile the corrected b2 direct ObsPy/source comparison with the predecessor
    comparator after environment integrity passes. b1 source-reference timings exist but
    came from an invalid requested-versus-observed dependency environment.
15. Investigate the pandas 3.0.5 divergence between numbers-only and
    numbers-plus-names paths. Profile construction, assignment, and string/name handling
    before proposing runtime changes.
16. Add bounded memory/resource evidence for the 10M, 20M, and 50M loads so missing
    high-load results can be classified rather than left unexplained.
17. Add confidence intervals or another reviewable uncertainty summary after retained
    sample history is sufficiently dense.
18. Evaluate whether the scalar direct-ObsPy comparison should also retain the
    predecessor 10,000-call loop form as a distinct ASV case, rather than relying only on
    per-call timing plus the still-authoritative predecessor loop benchmark.

## Maintenance trigger


Review this roadmap during beta stabilization and before any benchmark-authority
migration or release-candidate decision. Moving an
item into implementation requires an explicit requirement/design decision rather than
editing this roadmap alone.
