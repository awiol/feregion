# Benchmark harness planned enhancements

## Status

This document records **planned or investigatory work**, not implemented requirements.
The current `0.4` beta line preserves the a10 evidence-semantic repairs and restored
predecessor case/metric roles. b2 adds environment-integrity verification and a
machine-readable evidence-handoff command. ASV remains a secondary migration candidate
until `REQ-PERF-017` is closed; the predecessor benchmark harness remains authoritative
in that interval.

## Migration closure

1. **Closed for measurement collection:** the corrected b2 `reference-comparison`
   profile produced a finite direct ObsPy result under a passing retained environment-
   integrity record.
2. **Evidence collected; review remains:** fresh b2 standalone, pytest-benchmark, and
   Python 3.11–3.14 Tox evidence is retained alongside ASV comparator/diagnostic cases.
   Complete the final like-for-like parity review after the corrected release check.
3. **Contract clarification implemented in b3:** rare failure states need not be induced
   destructively in real benchmark environments. `REQ-PERF-009` requires distinct
   classification; controlled integration fixtures verify correctness/build/execution/
   incompatible paths, while genuine historical `not_applicable` and real environment-
   integrity failures provide observed operational examples.
4. **Post-b3 rerun required:** rerun `release-compare` and `campaign check`. b3 rejects
   the earlier normalized file because its b2 candidate rows came from the ObsPy
   reference profile rather than the fixed release-history environment.
5. **Post-b3 report replay required:** rebuild the static report so b3 retains a
   `.asv/feregion-reports` record tied to the exact source-evidence digest. After the
   release gate, parity review, and report record are accepted, decide whether ASV
   becomes the primary benchmark authority and which predecessor paths may be retired.

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
