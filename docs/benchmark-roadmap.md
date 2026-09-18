# Benchmark harness planned enhancements

## Status

This document records **planned or investigatory work**, not implemented
requirements for the `0.4.0` line. The implemented contract remains in the
requirements/design documents and the operator procedure remains
`benchmark-operations.md`.

## Reporting and interpretation

1. Evaluate richer native graph interaction without taking ownership of a full
   plotting engine: hover text that includes series/environment identity,
   tag/revision, benchmark parameter/load, value, and relative reference value;
   legend-hover highlighting; and non-color visual cues for dense comparisons.
2. Evaluate whether these improvements can remain a bounded post-publish overlay
   against a pinned ASV 0.6.x frontend. If the necessary changes require a large
   or fragile fork of ASV JavaScript, prefer a small project-owned summary layer
   over a frontend fork.
3. Add explicit report-freshness detection so an operator cannot silently view
   HTML older than retained measurement evidence.
4. Add coverage/completeness summaries that distinguish measured,
   not-applicable, build unavailable, execution failed, and missing values.

## Evidence and provenance

5. Add a durable campaign-run record containing the campaign definition,
   resolved commits, machine/environment selection, ASV/asv-runner versions,
   start/end timestamps, and references to result files updated by that run.
6. Improve multi-machine evidence handling without combining measurements from
   incomparable hosts into one release decision.
7. Retain report-regeneration metadata so a published report can identify the
   exact retained evidence state from which it was produced.

## Benchmark coverage

8. Add an ASV-native direct ObsPy comparison for the scalar geographical lookup
   case, with an explicit semantic contract and dependency profile, so user
   guidance can include current like-for-like relative timing instead of relying
   only on feregion batch measurements.
9. Investigate the pandas 3.0.5 divergence observed between numbers-only and
   numbers-plus-names adapter paths. Profile the relevant pandas construction,
   assignment, and string/name handling before proposing package changes.
10. Add bounded memory/resource evidence for the 10M, 20M, and 50M loads so
    missing high-load results can be classified as resource limits rather than
    left as unexplained absence.
11. Evaluate confidence intervals or another reviewable uncertainty summary for
    repeated release/dependency comparisons after the retained sample history is
    sufficiently dense.

## Maintenance trigger

Review this roadmap after external review of the final `0.4` alpha and again
before a later benchmark-focused minor release. Moving an item into
implementation requires an explicit requirement/design decision rather than
editing this roadmap alone.
