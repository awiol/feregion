# Observed benchmark results

## Purpose and evidence status

This document records benchmark observations accepted for the `0.4` benchmark-migration
closeout on 2026-09-19. It is an **observational snapshot**, not a universal performance
guarantee and not a substitute for retained machine-readable evidence.

The principal accepted checkpoint is the post-b3 machine-readable benchmark handoff,
SHA-256 `087990a7aff4e7c2efaaba4a7bbd0445f4a1edcd2fb4fae8c3776341209848a3`. It
identifies b3 commit `bc38d96441de9ffb4c7744e34f4aaf78640b7238` and includes raw ASV
results, state/run/environment/report records, normalized release evidence, fresh
predecessor standalone/pytest-benchmark evidence, and Python 3.11–3.14 predecessor Tox
results. Earlier b1/b2 and 2026-09-18 archives remain historical/provenance evidence.

Principal host:

- machine: `awiol-ryzen3600`;
- CPU: AMD Ryzen 5 3600 6-Core Processor, 12 logical CPUs;
- RAM: 32 GB;
- OS: Linux 6.8.0-138-generic.

The b1 evidence predates the b2 environment-integrity preflight. ASV result metadata
records requested dependency profiles, but it did not prove that the interpreter used
those exact distributions. The b1 ObsPy investigation demonstrated one concrete profile
drift, so dependency-profile measurements below are labeled as ASV-recorded profiles
until rerun under b2 preflight.

## Verified b2 reference and predecessor evidence acquired after the b2 source handoff

A later b2 machine-readable benchmark handoff supplied on 2026-09-19 has SHA-256
`1493d084d1253a5f3dacaaf45b2a4c7962aae9cc378f0e319498ef0157aa1640` and identifies
commit `796b00b4c7fe91b03d74a38245a2a27a2cdd7d78` (`0.4.0b2`). It contains ASV
results/state/run/environment evidence, normalized evidence, fresh predecessor standalone
and pytest-benchmark JSON, and Python 3.11–3.14 Tox benchmark results.

The corrected b2 `reference-comparison` environment passed integrity checks with CPython
3.12, NumPy 1.26.4, pandas 2.1.4, ObsPy 1.4.2, and Setuptools 81.0.0. `pip check` passed
and `obspy.geodetics.FlinnEngdahl` imported successfully. Representative scalar medians
were 4.680 µs for feregion, 3.000 µs for ObsPy, and 1.620 µs for the pinned source
scanner. On this host and exact profile, ObsPy was about 1.56× faster than feregion for
the scalar call. This is a scalar comparison, not a batch-performance ordering.

For the same verified profile, feregion batch medians were about 53.981 µs, 68.811 µs,
178.163 µs, and 1.269 ms at 100, 1k, 10k, and 100k points; the pinned source scanner
measured about 176.273 µs, 1.667 ms, 16.429 ms, and 166.447 ms. The corresponding
feregion/source speedups are approximately 3.27×, 24.2×, 92.2×, and 131×.

The fresh predecessor evidence is now current to b2 rather than historical `0.3.0a1`
only. The standalone report identifies `feregion 0.4.0b2` on CPython 3.14.6 / NumPy
2.5.2, pytest-benchmark identifies commit `796b00b4...`, and the Tox preservation set
contains Python 3.11, 3.12, 3.13, and 3.14 result files plus the cross-Python report.

The first normalized `release-compare` evidence generated after the b2 runs was not
accepted because its candidate rows came from the ObsPy reference environment. b3 made
normalized evidence environment-profile-aware. The post-b3 rerun closes that defect: the
accepted normalized artifact contains exactly seven measured loads for a9 and seven for
b3, all on `awiol-ryzen3600` under
`uv-py3.12-numpy1.26.4-pandas2.1.4`.

## Accepted post-b3 release comparison

| Load | a9 throughput | b3 throughput | b3 change |
|---:|---:|---:|---:|
| 10k | 55.14 M points/s | 55.03 M points/s | -0.21% |
| 20k | 64.34 M points/s | 65.29 M points/s | +1.47% |
| 50k | 74.60 M points/s | 74.56 M points/s | -0.06% |
| 100k | 76.54 M points/s | 78.67 M points/s | +2.78% |
| 200k | 77.77 M points/s | 79.07 M points/s | +1.67% |
| 500k | 72.01 M points/s | 74.66 M points/s | +3.68% |
| 1M | 56.32 M points/s | 59.75 M points/s | +6.10% |

The project release gate is complete and does not trigger. The small 10k and 50k
slowdowns are far below the >25% threshold and do not form a triggering adjacent pair.
These figures are single-host evidence, not a general performance guarantee.

## Accepted report reconstruction and preservation set

The latest retained report record shows
`asv publish --no-pull --config asv.conf.json` returned 0, produced an HTML index and
127 HTML files, and bound the rebuild to a 1,020-file source-evidence set with SHA-256
`0191a194284511b1271c8d1f376cf954e20ea2ffbe142edccc59e1b8cdeb5d9b`.
The final evidence handoff contains 41 ASV result files, 951 state records, 25 run
records, three environment-integrity records, three report-rebuild records, normalized
release evidence, two predecessor JSON reports, and five predecessor Tox/report files.
Derived HTML is intentionally excluded from the handoff because it can be regenerated.

## Campaign coverage observed for b1

Retained run records show successful b1 execution for:

- `smoke`;
- `release-compare`;
- `release-history`;
- `reference-comparison`;
- `diagnostics`;
- `dependency-matrix`; and
- `python-supported`.

The b1 `head-full` run retained many finite measurements but returned status `2`; it is
therefore incomplete and must not be represented as a fully successful campaign.

## Current b1 batch scale

Under the ASV-recorded CPython 3.12 / NumPy 1.26.4 / pandas 2.1.4 profile,
representative b1 medians are:

| Load | Geographic lookup | Seismic lookup |
|---:|---:|---:|
| 100k | 1.279 ms | 1.424 ms |
| 500k | 6.458 ms | 7.445 ms |
| 1M | 16.576 ms | 17.982 ms |
| 5M | 98.720 ms | 104.300 ms |
| 10M | 192.770 ms | 203.330 ms |
| 20M | 386.660 ms | 416.180 ms |
| 50M | 966.008 ms | 1.079 s |

The large numeric cases remain close to linear scaling on this host. Finite upper-load
measurements survive even though `head-full` as a whole was incomplete. Name and
pandas-with-name cases have missing upper-load cells; the retained run record does not
identify the failure mechanism, so those cells are not classified as memory exhaustion
without separate resource evidence.

## Throughput remains the project decision metric

The predecessor harness records `median_operations_per_second`. Normalized ASV evidence
derives `operations_per_second` from declared operation count and measured duration. A
timing of `t` seconds for `n` operations corresponds to `n / t` operations per second.
Elapsed duration remains useful raw evidence but does not replace throughput in the
project release-regression rule.

## Python-version sensitivity

The b1 `python-supported` campaign completed for CPython 3.11, 3.12, 3.13, and 3.14
under the ASV-recorded NumPy 2.3.5 / pandas 2.3.3 profile. Across geographic and seismic
batch cases at 10k, 100k, and 1M points, the geometric timing ratios relative to Python
3.11 are:

| Python | Timing ratio vs 3.11 |
|---|---:|
| 3.11 | 1.000 |
| 3.12 | 1.061 |
| 3.13 | 1.187 |
| 3.14 | 1.013 |

These are single-host observations, not interpreter-wide guarantees.

## NumPy-version sensitivity

Under the ASV-recorded CPython 3.12 / pandas 2.1.4 profiles, geographic and seismic
batch timings at 10k, 100k, and 1M give these geometric ratios relative to NumPy 1.26.4:

| NumPy | Timing ratio vs 1.26.4 |
|---|---:|
| 1.26.4 | 1.000 |
| 2.0.2 | 1.003 |
| 2.2.6 | 1.001 |
| 2.5.2 | 1.018 |

The spread is small in this evidence. No supported NumPy version is selected on this
basis alone.

## pandas-version sensitivity

Under the ASV-recorded CPython 3.12 / NumPy 1.26.4 profiles, pandas behavior remains
path-dependent. Geometric timing ratios over 10k, 100k, and 1M rows are:

| pandas | Copy numbers | Copy numbers + names | In-place numbers | In-place numbers + names |
|---|---:|---:|---:|---:|
| 2.1.4 | 1.000 | 1.000 | 1.000 | 1.000 |
| 2.2.3 | 0.995 | 0.973 | 0.909 | 0.947 |
| 2.3.3 | 0.992 | 0.979 | 0.901 | 0.963 |
| 3.0.5 | 1.067 | 0.658 | 0.926 | 0.624 |

The name-materializing path remains much more sensitive to pandas version than the
numbers-only path. This is an investigation result, not a dependency-selection rule.

## Restored diagnostic cases are now measured

The b1 `diagnostics` campaign completed. At 1M rows/points under the ASV-recorded
CPython 3.12 / NumPy 1.26.4 / pandas 2.1.4 profile:

| Diagnostic case | Median |
|---|---:|
| Internal split geographic | 10.589 ms |
| Internal split seismic | 12.064 ms |
| Caller `column_stack` + geographic | 18.648 ms |
| pandas in-place geographic numbers | 12.592 ms |
| pandas in-place numbers + names | 341.831 ms |
| pandas in-place seismic numbers | 14.088 ms |

These measurements restore real ASV observations for predecessor diagnostic roles. They
do not by themselves close migration parity because fresh predecessor measurements and
like-for-like reconciliation remain required.

## Reference comparison and the b1 ObsPy environment defect

The b1 `reference-comparison` campaign completed at the campaign level and produced
finite feregion and pinned-source measurements. Raw medians were approximately:

| Case/load | Median |
|---|---:|
| feregion scalar geographic number | 5.880 µs |
| pinned source scalar | 1.970 µs |
| feregion batch 100 | 43.841 µs |
| source scanner 100 | 183.973 µs |
| feregion batch 1k | 59.761 µs |
| source scanner 1k | 2.261 ms |
| feregion batch 10k | 187.364 µs |
| source scanner 10k | 17.135 ms |
| feregion batch 100k | 1.431 ms |
| source scanner 100k | 176.310 ms |

These raw timings are **diagnostic only** because the same retained reference environment
failed integrity investigation. ASV requested NumPy 1.26.4, pandas 2.1.4, ObsPy 1.4.2,
but the actual interpreter contained NumPy 2.5.3, pandas 2.1.4, ObsPy 1.4.2, and
Setuptools 84.0.0. `pip check` reported that pandas 2.1.4 was incompatible with the
installed NumPy. ObsPy itself failed to import because its normal import path required
`pkg_resources`, which was absent from that Setuptools release. The direct ObsPy timing
was therefore stored as `NaN`/`not_applicable` by b1.

b2 changes the environment contract: requested and observed versions, required imports,
and `pip check` must pass before timing is accepted. A corrected reference campaign must
replace the b1 reference timings before they support a profile-specific comparative
claim.

## Historical predecessor ObsPy comparison

A predecessor standalone result retained in the 2026-09-18 evidence archive provides a
real historical direct comparison. It is **not** a b1 result. The environment was
`feregion 0.3.0a1`, CPython 3.14.6, NumPy 2.5.2 on the same Ryzen 5 3600 host. Over one
10,000-coordinate scalar loop:

| Implementation | Median | Throughput |
|---|---:|---:|
| feregion scalar lookup | 27.944 ms | 357.9k lookups/s |
| ObsPy `FlinnEngdahl.get_number()` | 19.720 ms | 507.1k lookups/s |
| pinned source-table scanner | 14.787 ms | 676.3k lookups/s |

In that historical scalar workload ObsPy was about 1.42× faster than feregion. That
result must not be generalized to vectorized batch workloads. The same predecessor
report measured feregion's vectorized batch path as approximately 5.28×, 35.96×,
87.61×, and 118.03× faster than the scalar source-table scanner at 100, 1k, 10k, and
100k points respectively.

## Performance across feregion releases

### b1 release-to-release evidence

The b1 release-comparison evidence shows the geographic batch path approximately flat
relative to `0.4.0a9`: all measured 10k–1M median differences are below about 1% in the
retained same-profile data. This is consistent with the beta-stabilization claim that
b1 did not intentionally change runtime lookup behavior.

### Controlled 0.1/0.2/0.3 historical rerun

The controlled rerun uses CPython 3.12, NumPy 1.26.4, and pandas 2.1.4 and directly
remeasures geographic/seismic batch cases:

| Load | Geographic 0.1.2a10 | Geographic 0.2.0b1 | Geographic 0.3.0b1 | Seismic 0.2.0b1 | Seismic 0.3.0b1 |
|---:|---:|---:|---:|---:|---:|
| 100k | 1.269 ms | 1.280 ms | 1.275 ms | 3.334 ms | 1.419 ms |
| 500k | 6.856 ms | 6.652 ms | 6.561 ms | 48.817 ms | 7.279 ms |
| 1M | 16.386 ms | 16.444 ms | 16.272 ms | 98.940 ms | 18.028 ms |

The geographic path is approximately flat across these three revisions. The controlled
rerun does not reproduce a material `0.1.2a10`→`0.2.0b1` geographic regression.
`0.3.0b1` seismic lookup is about 2.35×, 6.71×, and 5.49× faster than `0.2.0b1` at
100k, 500k, and 1M respectively. The rerun has no usable `0.1.2a10` seismic result, so
it cannot establish the seismic `0.1`→`0.2` transition.

## Retained state evidence

The supplied b1 preservation set contains 910 `correctness_passed` setup records and 22
`not_applicable` records. Genuine historical `not_applicable` examples include revisions
that predate seismic interfaces. The b1 ObsPy `not_applicable` record is **not accepted
as genuine capability absence** after environment investigation; b2 treats failure of an
explicitly requested comparator dependency as environment/build unavailability instead.

The project does not require deliberate corruption of real benchmark environments merely
to manufacture every rare state. `REQ-PERF-009` requires the states to remain
distinguishable. Controlled integration fixtures verify `build_unavailable`,
`correctness_failed`, `execution_failed`, and incompatible-version normalization, while
real evidence supplies genuine historical `not_applicable` and environment-integrity
failures. b3 records this as the migration-closure interpretation.

## Resource and reporting limitations

The b1 `head-full` campaign returned status `2`. Numeric cases retained finite results
through 50M, but some high-load name and pandas-with-name cells are absent. A previous
broad run entered swap, while the controlled historical rerun did not retain active
swap-I/O telemetry. Missing high-load cells therefore remain unclassified unless a
bounded rerun records resource state.

Post-b3 retained report records demonstrate fresh report rebuilding from retained
evidence. `python -m benchmarks.release_workflow report` remains the explicit
regeneration command. `python -m benchmarks.evidence_bundle` preserves raw results,
state/run/environment/report evidence, normalized evidence, predecessor outputs, and
configuration without relying on derived HTML.

## Current interpretation

The accepted evidence covers current/history/dependency/supported-Python ASV campaigns,
verified direct ObsPy/source comparison, restored diagnostics, fresh predecessor
standalone/pytest-benchmark/Tox evidence, a complete same-profile release gate, and a
content-addressed report rebuild. `REQ-PERF-017` is satisfied and `DEC-062` promotes the
ASV-derived path to primary benchmark authority. Remaining high-load resource attribution,
reporting UX, and archive-retention questions are non-blocking roadmap work.
