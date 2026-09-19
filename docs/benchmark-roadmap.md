# Benchmark harness planned enhancements

## Status

This document records **planned or investigatory work**, not implemented requirements.
The `0.4` ASV migration is complete: the reviewed post-b3 evidence satisfies
`REQ-PERF-017`, and ASV plus the project-owned semantic/evidence/gate layers are now the
primary benchmark-evidence path. The predecessor harness remains runnable as
compatibility/reference tooling and retained provenance.

The following items are enhancements or investigations. They do not block the completed
`0.4` benchmark migration unless a later decision explicitly promotes one into a release
requirement.

## Reporting and interpretation

1. Evaluate richer native graph interaction without taking ownership of a full plotting
   engine: hover text with series/environment identity, tag/revision, load, value,
   operations-per-second, and relative reference value; legend-hover highlighting; and
   non-color cues for dense comparisons.
2. Add report-freshness detection so an operator cannot silently view HTML older than
   retained measurement evidence.
3. Add coverage/completeness summaries that distinguish all project evidence states and
   stored benchmark-version incompatibility.
4. Evaluate a compact throughput/scaling summary on the feregion OutputPublisher page,
   while leaving ASV's native graph/regression implementation intact.

## Evidence and provenance

5. Extend campaign-run records with ASV/asv-runner version, start/end timestamps, and
   references/hashes for result files updated by the run.
6. Improve multi-machine evidence handling without combining incomparable hosts into a
   release decision.
7. Define the durable retention/location policy for evidence handoff archives and the
   preservation-set source directories. The handoff command exports results, state, run,
   environment, report, normalized, predecessor, and configuration evidence; repository
   policy still needs to define where long-lived archives are stored and pruned.

## Benchmark coverage and investigation

8. Investigate the pandas 3.0.5 divergence between numbers-only and
   numbers-plus-names paths. Profile construction, assignment, and string/name handling
   before proposing runtime changes.
9. Add bounded memory/resource evidence for the 10M, 20M, and 50M loads so missing
   high-load results can be classified rather than left unexplained.
10. Add confidence intervals or another reviewable uncertainty summary after retained
    sample history is sufficiently dense.
11. Evaluate whether the scalar direct-ObsPy comparison should also retain the
    predecessor 10,000-call loop form as a distinct ASV case rather than relying on
    per-call timing plus retained predecessor historical evidence.

## Maintenance trigger

Review this roadmap during later beta/release-candidate work and when materially new
benchmark evidence is acquired. Moving an item into implementation requires an explicit
requirement/design decision rather than editing this roadmap alone.
