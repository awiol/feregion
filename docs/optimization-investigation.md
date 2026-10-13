# Runtime optimization investigation

## Status and scope

This document records the measurement-first `0.5.0a1` investigation. It is an
**investigation record**, not authorization to change runtime behavior or public APIs.
`DEC-066` controls the transition from measurement to implementation.

Target baseline for the first measurements:

- package: `feregion 0.4.0b6`;
- supplied handoff SHA-256:
  `3efe41b91feb64b5d1fcc45afc335d128962fc26bac5143fa8452c1fb6012588`;
- Python: CPython 3.13.5;
- NumPy: 2.3.5;
- pandas: 2.2.3;
- workload seed: `20260917`;
- loads: 100,000 and 1,000,000 elements;
- repetitions: three per mechanism stage;
- evidence role: single-host mechanism diagnosis, not a release-performance gate.

The pre-change measurements were collected before any `0.5` runtime modification.
`0.5.0a1` intentionally keeps runtime behavior unchanged.

## Questions

The investigation asks these decision-relevant questions:

1. Which validation stage makes public geographical-ID-to-seismic conversion much
   slower than direct hierarchy gathering?
2. How much of geographical/seismic name conversion is identifier validation versus
   unavoidable Unicode result materialization?
3. How much pandas name-output cost belongs to lookup/name production versus DataFrame
   copy and column assignment?
4. Does the existing split-vector coordinate path retain a material advantage over
   caller stacking and the public `(n, 2)` matrix route?
5. Is there enough evidence to optimize the current public contract, or should a later
   alpha prototype an additive public interface or alternate result representation?

## Pre-change observations

Representative medians from the exact `0.4.0b6` baseline are:

| Mechanism | 100k | 1M | 1M ns/element |
| --- | ---: | ---: | ---: |
| geographical matrix lookup | 2.14 ms | 25.43 ms | 25.43 |
| caller `column_stack` + geographical lookup | 2.45 ms | 27.24 ms | 27.24 |
| internal split geographical lookup | 1.62 ms | 18.11 ms | 18.11 |
| seismic matrix lookup | 2.55 ms | 27.65 ms | 27.65 |
| internal split seismic lookup | 1.93 ms | 21.37 ms | 21.37 |
| public geographical IDs → seismic IDs | 2.97 ms | 58.35 ms | 58.35 |
| complete geographical-ID validation | 2.48 ms | 56.10 ms | 56.10 |
| historical-name-slot validation only | 2.11 ms | 51.64 ms | 51.64 |
| active-geographical-mask validation only | 0.38 ms | 3.40 ms | 3.40 |
| direct hierarchy crosswalk gather | 0.34 ms | 3.38 ms | 3.38 |
| public geographical IDs → names | 5.36 ms | 98.24 ms | 98.24 |
| direct geographical name-table gather | 2.66 ms | 39.76 ms | 39.76 |
| public seismic IDs → names | 7.48 ms | 122.72 ms | 122.72 |
| complete seismic-ID validation | 3.00 ms | 60.62 ms | 60.62 |
| direct seismic name-table gather | 3.86 ms | 60.13 ms | 60.13 |
| pandas DataFrame copy | 0.41 ms | 2.92 ms | 2.92 |
| pandas split geographical core | 1.58 ms | 18.9 ms | 18.9 |
| pandas geographical-name materialization | 5.49 ms | 94.83 ms | 94.83 |
| pandas copy + name-column assignment | 30.97 ms | 444.20 ms | 444.20 |

The stage measurements were run independently. Their durations must not be added as if
all stages were mutually exclusive or as if cache/allocator state were identical.

### Observation O1 — geographical-ID validation dominates public hierarchy conversion

At 1M identifiers, the public geographical-ID-to-seismic operation measured about
58.35 ms. Complete ID validation measured about 56.10 ms, while direct `uint8`
crosswalk gathering measured about 3.38 ms.

The historical-name-slot check (`names[array] == ""`) measured about 51.64 ms by itself.
The active-geographical Boolean-mask check measured about 3.40 ms.

### Inference I1 — the Unicode name-slot validity check is the leading `a2` candidate

`FlinnEngdahlLookup.__post_init__()` already establishes that every geographical ID used
by the lookup table has a non-empty name, and `_active_geographic` identifies exactly
those active IDs. Therefore the measured Unicode name-table gather in the public numeric
conversion may be redundant when active-mask validation is also applied.

This is a candidate mechanism, not an implemented decision. `0.5.0a2` must demonstrate
predecessor sensitivity and preserve custom-engine invalid-ID behavior before removing or
replacing that check.

### Observation O2 — name conversion has two material costs

At 1M identifiers, geographical name conversion measured about 98.24 ms. Direct Unicode
name-table gathering measured about 39.76 ms, while the current complete geographical-ID
validator measured about 56.10 ms. Seismic name conversion measured about 122.72 ms;
seismic validation and direct seismic-name gathering were both about 60 ms.

The 1M geographical name result is approximately 128 MB and the seismic name result is
approximately 184 MB under the baseline fixed-width Unicode dtypes. Result
materialization is therefore intrinsically material even if validation is optimized.

### Inference I2 — optimize validation before considering a name representation change

The measurements support investigating a cheaper validity representation (for example, a
Boolean validity mask established at engine construction) before considering a new name
result representation. A compact/categorical/lazy representation would change a public
contract and is not justified by `a1` alone.

### Observation O3 — pandas name assignment is a separate hotspot

At 1M rows, DataFrame copy was about 2.92 ms, split numeric lookup about 18.9 ms, and
geographical name materialization about 94.83 ms. Copy plus assignment of an already
materialized fixed-width Unicode name array measured about 444 ms.

### Inference I3 — core lookup optimization cannot explain most pandas name-output cost

The pandas name-output path needs dependency-specific investigation of column
construction/assignment and resulting dtype before changing the core coordinate kernel.
Existing pandas-sensitivity evidence should be combined with this stage decomposition.

### Observation O4 — split vectors retain a material advantage

At 1M points, caller stacking plus public geographical lookup measured about 27.24 ms,
while direct split-vector lookup measured about 18.11 ms, approximately 1.5x faster.
The public pre-stacked matrix path measured about 25.43 ms.

### Decision state

No new public split interface is authorized. The evidence supports preserving the
internal split path and measuring candidate public forms later if internal optimization
alone cannot provide an acceptable performance envelope.

## Decision after the measurement checkpoint

`DEC-067` selects the geographical active-mask validation optimization for the first implementation alpha. The decision does not authorize a public API change. A fixed-CPU alternating comparison at 1M IDs observed median predecessor/candidate values of approximately 58.0/7.6 ms for geographical-ID-to-seismic conversion, 93.5/43.4 ms for geographical names, 24.8/24.6 ms for the unchanged geographical matrix control, and 137.3/137.7 ms for untouched seismic names.

The remaining name cost is now dominated by actual Unicode result gathering for the geographical path. Seismic-name conversion still shows a roughly even split between validity checking and Unicode gathering, so a separate validity-mask design may be investigated later. pandas fixed-width Unicode column assignment remains a distinct hotspot and is not changed by `DEC-067`.

## `0.5.0a2` decision gate

An `a2` runtime optimization may proceed only when all of these conditions hold:

1. the targeted mechanism is materially represented in the complete public operation;
2. the proposed implementation preserves active/inactive ID semantics, custom-engine
   invariants, shape/dtype/error behavior, and extended-precision coordinate semantics;
3. a predecessor-sensitivity test or equivalent discriminating check fails on the exact
   baseline for the intended mechanism;
4. candidate measurements use the same workload/environment contract as baseline;
5. a measured speedup is larger than run-to-run control noise without a material memory
   regression; and
6. any public API or result-representation change is reviewed separately for
   compatibility and migration cost.

The leading bounded candidate for `a2` is optimization of region-ID validation so numeric
hierarchy conversion does not gather Unicode names merely to establish validity. Name
conversion can reuse the same validity mechanism if its semantics remain equivalent.
Pandas name assignment is a separate investigation and must not be conflated with that
core change.

## `0.5.0a3` seismic-name validity investigation and decision

On exact `0.5.0a2` in the restored CPython 3.13.5 / NumPy 2.3.5 / pandas 2.2.3 environment, a fixed-CPU 1M-ID probe reproduced the remaining seismic validation hotspot. Public seismic-name conversion measured about 56.5–71.2 ms in the diagnostic runs; complete validation about 31.5–38.5 ms; the Unicode empty-slot check about 30.8–38.6 ms; a candidate Boolean mask check about 1.4 ms; and direct Unicode result gathering about 22.8–26.5 ms. The exact values vary with run state, but the mechanism separation is stable: repeated Unicode validity gathering is material and a compact Boolean relation is not.

The semantic oracle is the seismic name table, not hierarchy membership. A custom engine may contain a named seismic ID that no geographical region references. A dedicated regression covers both that valid unreferenced case and an empty unreferenced slot. A deliberate mutation that derived validity only from crosswalk membership made the valid-unreferenced regression fail, demonstrating sensitivity to the leading incorrect implementation.

`DEC-068` therefore authorizes a cached read-only Boolean relation derived from non-empty seismic-name slots. Five fixed-CPU alternating predecessor/candidate pairs at 1M IDs observed medians of approximately 56.6/26.2 ms for seismic-name conversion (~2.16x predecessor/candidate), while geographical matrix lookup, geographical hierarchy conversion, and geographical-name conversion controls remained approximately flat. This is mechanism-specific single-host evidence, not release `QG-PERF` closure.

After this change, the remaining seismic-name cost is dominated by actual result gathering/materialization under the current fixed-width Unicode return contract. Further core name-result representation changes remain outside this bounded decision. pandas name-column construction remains the next separate investigation.

## `0.5.0a4` pandas name-output investigation and decision

On frozen `0.5.0a3`, the 1M-row pandas copy-return path measured about 118 ms with geographical names and about 143 ms with seismic names, while numbers-only controls were about 13 ms. Both existing name columns materialized as pandas `object` dtype. Assigning the core fixed-width Unicode result therefore performs an additional large conversion before reaching the representation pandas already exposes.

A discriminating probe compared the current route with direct gathering from an object view of the selected engine's small name table. The small table itself is only thousands of pointer bytes; the 1M-row object gather measured about 5 ms in the diagnostic run. The complete alternative preserved DataFrame equality, observed `object` name-column dtype, and deep-memory size. Converting the already materialized 1M-element Unicode output to object first was much less useful because that merely moved most of the conversion cost.

`DEC-069` therefore authorizes the pandas-only trusted-name route for identifiers produced by the same engine in the current operation. A custom-engine regression verifies that both geographical and seismic name output comes from the explicitly selected engine assets. Five fixed-CPU alternating `0.5.0a3`/candidate pairs at 1M rows observed about 4.92x improvement for geographical copy name output, 6.20x for seismic copy name output, 5.23x and 5.88x for corresponding in-place-with-fresh-copy diagnostics, and approximately flat numbers-only controls.

This is not a pandas representation redesign: the core vector name APIs still return fixed-width Unicode arrays, and pandas continues to expose the same object name columns. Alternate categorical/string/lazy representations remain a later compatibility decision.

## `0.5` alpha closeout: coordinate API-shape decision

Exact `0.5.0a4` was measured in fresh fixed-CPU processes to avoid the high-water allocation contamination observed when the full mechanism probe attempted to carry the 1M pandas case into a 5M coordinate case. The API-only retry measured 100k, 1M, and 5M points independently.

| Load | Geographic matrix | Geographic split | Caller stack + matrix | Matrix/split | Stack/split |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100k | 1.150 ms | 0.755 ms | 1.272 ms | 1.52x | 1.68x |
| 1M | 12.580 ms | 9.323 ms | 13.700 ms | 1.35x | 1.47x |
| 5M | 86.557 ms | 60.744 ms | 96.117 ms | 1.42x | 1.58x |

The corresponding seismic matrix/split ratios were about 1.35–1.39x at 1M–5M, and caller-stack/split about 1.52–1.54x. A stage probe attributes much of the gap to strided C-order matrix columns: at 5M, value validation measured about 27.6 ms on matrix-column views versus 16.0 ms on contiguous vectors, while the validated lookup kernel measured about 66.3 versus 60.4 ms. Copying or transposing to contiguous vectors recovers only part of the difference and introduces a full coordinate-sized temporary, about 80 MB for 5M float64 pairs.

`DEC-070` therefore closes `0.5` current-contract optimization without a public interface change. The matrix API remains supported and is not deprecated. An additive public split-vector interface is deferred to `0.6`, where the demonstrated performance/resource trade-off can be evaluated together with its public typing, shape, error, and compatibility contract.

With this decision, intended `0.5` functionality is substantially complete and the line may enter beta stabilization. This maturity decision does not close `QG-PERF`, supported-environment, static-analysis, hosted-CI, independent-oracle, or provenance gates.

## Limitations

- These measurements are from one host/environment and three repetitions.
- The mechanism probe is not ASV release evidence and does not replace the maintained
  `QG-PERF` release comparison.
- `ru_maxrss` high-water deltas in the probe are advisory only; repeated operations in
  one process can hide per-case allocation peaks. Use fresh-process resource evidence
  before making a memory-improvement claim.
- The observations do not establish a public API deprecation decision.
