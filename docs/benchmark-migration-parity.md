# Benchmark migration parity

## Purpose

This document records the completed migration from the predecessor benchmark harness to
the `0.4` ASV benchmark system. The predecessor standalone timer, `pytest-benchmark`
suite, Tox Python matrix, and release comparator remain runnable as compatibility,
reference, and provenance tooling. They are no longer a second co-equal benchmark
authority after the reviewed post-b3 evidence closed `REQ-PERF-017`.

Implementation presence is not verification. The accepted migration decision uses the
retained real-run evidence described below in addition to repository tests.

## Case and metric parity

| Predecessor role | Predecessor surface | Accepted ASV status | Migration result |
|---|---|---|---|
| Scalar geographic number | standalone + pytest-benchmark | implemented and measured | Source-table semantic setup verified before timing. |
| Scalar geographic `Region` | standalone + pytest-benchmark | implemented and measured | Number and name checked against source tables. |
| Scalar geographic number→name | standalone + pytest-benchmark | implemented and measured | Source-derived number/name oracle retained. |
| Direct ObsPy scalar baseline | standalone + pytest-benchmark | implemented and measured under verified b2 profile | ObsPy 1.4.2 environment integrity passed and finite scalar timing is retained. |
| Direct pinned-source scalar baseline | standalone | implemented and measured under verified b2 profile | Independent source comparator retained. |
| Public geographic batch lookup | standalone + pytest-benchmark | implemented and measured | Full maintained 1-2-5 grid is supported; release gate uses the bounded 10k–1M subset. |
| Direct pinned-source batch-equivalent scan | standalone + pytest-benchmark | implemented and measured through 100k | Candidate/source comparison retained on identical deterministic workloads. |
| Candidate/source speedup | standalone derived metric | derivable from normalized evidence | No separate timer is required. |
| Seismic batch lookup | standalone + pytest-benchmark | implemented and measured | Source geographic lookup + hierarchy crosswalk remains the correctness oracle. |
| Geographic→seismic crosswalk | standalone + pytest-benchmark | implemented and measured | Crosswalk oracle is checked outside timing. |
| Seismic number→name batch | standalone + pytest-benchmark | implemented and measured | Restored ASV role retained. |
| Geographic number→name batch | standalone + pytest-benchmark | implemented and measured | Source names checked outside timing. |
| pandas copy, numbers | standalone + pytest-benchmark | implemented and measured | Dependency sensitivity retained. |
| pandas copy, numbers + names | standalone + pytest-benchmark | implemented and measured | Dependency sensitivity retained. |
| pandas in-place, numbers | standalone + pytest-benchmark | implemented and measured in `diagnostics` | Real ASV diagnostic evidence retained. |
| pandas in-place, numbers + names | standalone | implemented and measured in `diagnostics` | Real ASV diagnostic evidence retained. |
| pandas in-place seismic numbers | pytest-benchmark | implemented and measured in `diagnostics` | Historical revisions may legitimately be not applicable. |
| Internal split geographic path | standalone + pytest-benchmark | implemented and measured in `diagnostics` | Diagnostic/private role retained. |
| Internal split seismic path | standalone + pytest-benchmark | implemented and measured in `diagnostics` | Diagnostic/private role retained. |
| Caller `column_stack` + geographic lookup | standalone | implemented and measured in `diagnostics` | Allocation/stacking diagnostic retained. |
| Supported-Python comparison | Tox + custom reducer | ASV profile implemented and measured | Python 3.11–3.14 ASV evidence exists; fresh predecessor Tox evidence was retained for parity review. |
| Release regression decision | custom release comparator | ASV normalization/check implemented and accepted | Same-profile a9↔b3 release evidence is complete and the throughput gate does not trigger. |
| Iterations/operations per unit time | standalone + cross-Python reducer | retained as normalized ASV `operations_per_second` | Throughput remains the project decision quantity. |

## Accepted closure evidence

The post-b3 machine-readable evidence handoff has SHA-256
`087990a7aff4e7c2efaaba4a7bbd0445f4a1edcd2fb4fae8c3776341209848a3` and identifies
b3 commit `bc38d96441de9ffb4c7744e34f4aaf78640b7238`. It contains raw ASV results,
951 setup-state records, 25 revision/campaign-run records, three environment-integrity
records, three report-rebuild records, normalized release evidence, fresh predecessor
standalone/pytest-benchmark evidence, and the Python 3.11–3.14 predecessor Tox results.

The normalized `release-compare` artifact contains exactly 14 measured records: seven
loads for `0.4.0a9` and seven loads for b3. Every record uses machine
`awiol-ryzen3600` and environment `uv-py3.12-numpy1.26.4-pandas2.1.4`. The project gate
is complete and does not trigger. Candidate throughput differs from a9 by approximately
-0.21%, +1.47%, -0.06%, +2.78%, +1.67%, +3.68%, and +6.10% at 10k, 20k, 50k, 100k,
200k, 500k, and 1M respectively. No measured slowdown approaches the accepted >25%
adjacent-load trigger.

The latest retained report record shows `asv publish --no-pull --config asv.conf.json`
returned 0, produced `.asv/html/index.html`, and retained 127 HTML files. It binds the
rebuild to a 1,020-file source-evidence preservation set with SHA-256
`0191a194284511b1271c8d1f376cf954e20ea2ffbe142edccc59e1b8cdeb5d9b`.

Corrected b2 reference evidence independently verifies the requested reference
environment, including NumPy 1.26.4, pandas 2.1.4, ObsPy 1.4.2, and Setuptools 81.0.0,
with a clean dependency check and finite ObsPy/source timings. Fresh b2 predecessor
standalone, pytest-benchmark, and Tox evidence supplied the final compatibility/reference
comparison surface. b3 changed benchmark evidence selection and report provenance, not
runtime lookup behavior or benchmark timing semantics, so those predecessor timings do
not require repetition solely for the b3 version label.

## Failure-state interpretation

`REQ-PERF-009` requires result states to remain distinguishable. It does not require
operators to damage real benchmark environments merely to manufacture every rare state.
Repository integration fixtures cover `build_unavailable`, `correctness_failed`,
`execution_failed`, and incompatible-version normalization. Retained operational evidence
contains genuine historical `not_applicable` states and the environment-integrity failure
that led to the b2 reference-profile correction. This combination satisfies the state-
discrimination part of the migration review.

## Authority after migration

`REQ-PERF-017` is satisfied. ASV plus the project-owned campaign/evidence/regression
layers are the primary benchmark-evidence path for the `0.4` line. Use
`python -m benchmarks.campaign check` for the project release-performance gate and
`python -m benchmarks.release_workflow report` for reproducible static-report rebuilds.

Keep the predecessor standalone timer, `pytest-benchmark` suite, Tox benchmark matrix,
and custom reducers runnable while they remain useful for compatibility checks,
investigation, and historical provenance. They no longer define a second authoritative
release-performance decision path. Retiring any predecessor surface is a separate
maintenance decision; migration acceptance does not require immediate deletion.
