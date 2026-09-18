# Benchmark migration parity

## Purpose

This document prevents the ASV migration from silently reducing benchmark coverage.
It compares the predecessor benchmark roles with the `0.4.0a10` ASV migration
candidate. The predecessor standalone timer, `pytest-benchmark` suite, Tox Python
matrix, and release comparator remain the current authoritative benchmark path until
`REQ-PERF-017` is closed by reviewed real-run parity evidence.

Implementation presence is not verification. A row marked **implemented in ASV**
means source exists; it does not mean the ASV result has been measured on the target
host or accepted as replacement evidence.

## Case and metric parity

| Predecessor role | Predecessor surface | a10 ASV status | Migration note |
|---|---|---|---|
| Scalar geographic number | standalone + pytest-benchmark | implemented | Source-table semantic setup added. |
| Scalar geographic `Region` | standalone + pytest-benchmark | implemented | Number and name are checked against source tables. |
| Scalar geographic number→name | standalone + pytest-benchmark | implemented | Uses source-derived number/name oracle. |
| Direct ObsPy scalar baseline | standalone + pytest-benchmark | implemented in `reference-comparison` | Requires the ObsPy comparison profile; real parity measurement still required. |
| Direct pinned-source scalar baseline | standalone | implemented in `reference-comparison` | Uses the same hash-verified source tables as the semantic oracle. |
| Public geographic batch lookup | standalone + pytest-benchmark | implemented | Full maintained 1-2-5 grid available. |
| Direct pinned-source batch-equivalent scan | standalone + pytest-benchmark | implemented through 100k | Bounded comparator loads match the predecessor's practical source-scan range. |
| Candidate/source speedup | standalone derived metric | derivable, not a separate timer | Compare the candidate and source-reference cases on identical loads/environment. |
| Seismic batch lookup | standalone + pytest-benchmark | implemented | Source geographic lookup + project crosswalk is the correctness oracle. |
| Geographic→seismic crosswalk | standalone + pytest-benchmark | implemented | Crosswalk oracle is checked outside timing. |
| Seismic number→name batch | standalone + pytest-benchmark | implemented | Restored in a10. |
| Geographic number→name batch | standalone + pytest-benchmark | implemented | Source names are checked outside timing. |
| pandas copy, numbers | standalone + pytest-benchmark | implemented | Dependency sensitivity retained. |
| pandas copy, numbers + names | standalone + pytest-benchmark | implemented | Dependency sensitivity retained. |
| pandas in-place, numbers | standalone + pytest-benchmark | implemented in `diagnostics` | Restored in a10. |
| pandas in-place, numbers + names | standalone | implemented in `diagnostics` | Restored in a10. |
| pandas in-place seismic numbers | pytest-benchmark | implemented in `diagnostics` | Historical revisions may be not applicable. |
| Internal split geographic path | standalone + pytest-benchmark | implemented in `diagnostics` | Diagnostic/private, not public API. |
| Internal split seismic path | standalone + pytest-benchmark | implemented in `diagnostics` | Diagnostic/private, not public API. |
| Caller `column_stack` + geographic lookup | standalone | implemented in `diagnostics` | Retains the allocation/stacking comparison role. |
| Supported-Python comparison | Tox + custom reducer | ASV profile implemented | Predecessor Tox matrix remains authoritative until result/report parity is reviewed. |
| Release regression decision | custom release comparator | ASV normalization/check implemented | a10 corrects the gate to throughput slowdown; real closure evidence remains required. |
| Iterations/operations per unit time | standalone + cross-Python reducer | retained in predecessor and normalized ASV evidence | `operations_per_second` is derived from declared operations and measured duration. |

## Why the predecessor harness remains

ASV solved revision/environment/history/reporting problems, but a migration is not
successful if it drops semantic cases, independent comparators, throughput metrics,
or failure-state meaning. The isolated a9 review identified correctness,
comparability, throughput-gate, and failure-state defects in the ASV evidence path.
Those source defects are addressed in a10, but source repair is not equivalent to a
successful real ASV parity run.

Do not remove the predecessor paths until a review demonstrates:

1. semantic correctness sensitivity against deliberately wrong but in-range output;
2. compatible stored benchmark-version mapping across retained history;
3. distinct not-applicable, environment/build, correctness, and execution states;
4. throughput-gate parity with the predecessor comparator;
5. case/metric coverage from the table above; and
6. report/result retention sufficient to reproduce the accepted decisions.

## Authoritative commands during migration

Run the predecessor standalone report when release-performance evidence is required:

```bash
uv run --locked --group benchmark python -m benchmarks.run_benchmark \
  --output benchmark-standalone.json
```

Run the predecessor pytest-benchmark suite when case-level timing/detail is required:

```bash
uv run --locked --group benchmark pytest benchmarks \
  --benchmark-only --benchmark-json=benchmark.json
```

Run the supported-Python predecessor matrix when cross-interpreter evidence is
required:

```bash
uv run --locked --group matrix --group benchmark tox run \
  -e benchmark-py311,benchmark-py312,benchmark-py313,benchmark-py314,benchmark-report
```

ASV campaigns should also be run and retained during migration. Their purpose is to
close the replacement evidence, not to erase the predecessor evidence prematurely.
