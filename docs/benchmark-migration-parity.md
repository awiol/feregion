# Benchmark migration parity

## Purpose

This document prevents the ASV migration from silently reducing benchmark coverage.
It compares the predecessor benchmark roles with the `0.4.0b2` ASV migration
candidate. The predecessor standalone timer, `pytest-benchmark` suite, Tox Python
matrix, and release comparator remain the current authoritative benchmark path until
`REQ-PERF-017` is closed by reviewed real-run parity evidence.

Implementation presence is not verification. A row marked **implemented in ASV**
means source exists; it does not mean the ASV result has been measured on the target
host or accepted as replacement evidence.

## Case and metric parity

| Predecessor role | Predecessor surface | b2 ASV status | Migration note |
|---|---|---|---|
| Scalar geographic number | standalone + pytest-benchmark | implemented | Source-table semantic setup added. |
| Scalar geographic `Region` | standalone + pytest-benchmark | implemented | Number and name are checked against source tables. |
| Scalar geographic number→name | standalone + pytest-benchmark | implemented | Uses source-derived number/name oracle. |
| Direct ObsPy scalar baseline | standalone + pytest-benchmark | implemented; corrected profile pending rerun | b1 executed the case but the requested environment was inconsistent and ObsPy import failed; b2 makes this an environment failure rather than `not_applicable`. |
| Direct pinned-source scalar baseline | standalone | implemented and measured in b1 | Raw b1 timing exists, but its reference environment failed integrity and must be replaced by a b2-verified rerun before profile-specific parity acceptance. |
| Public geographic batch lookup | standalone + pytest-benchmark | implemented | Full maintained 1-2-5 grid available. |
| Direct pinned-source batch-equivalent scan | standalone + pytest-benchmark | implemented and measured through 100k | Raw b1 timing exists; corrected b2 environment verification is required before profile-specific parity acceptance. |
| Candidate/source speedup | standalone derived metric | derivable, not a separate timer | Compare the candidate and source-reference cases on identical loads/environment. |
| Seismic batch lookup | standalone + pytest-benchmark | implemented | Source geographic lookup + project crosswalk is the correctness oracle. |
| Geographic→seismic crosswalk | standalone + pytest-benchmark | implemented | Crosswalk oracle is checked outside timing. |
| Seismic number→name batch | standalone + pytest-benchmark | implemented | Restored in a10. |
| Geographic number→name batch | standalone + pytest-benchmark | implemented | Source names are checked outside timing. |
| pandas copy, numbers | standalone + pytest-benchmark | implemented | Dependency sensitivity retained. |
| pandas copy, numbers + names | standalone + pytest-benchmark | implemented | Dependency sensitivity retained. |
| pandas in-place, numbers | standalone + pytest-benchmark | implemented and measured in `diagnostics` | Real b1 ASV measurement is retained; fresh predecessor reconciliation remains open. |
| pandas in-place, numbers + names | standalone | implemented and measured in `diagnostics` | Real b1 ASV measurement is retained; fresh predecessor reconciliation remains open. |
| pandas in-place seismic numbers | pytest-benchmark | implemented and measured in `diagnostics` | Real b1 ASV measurement is retained; historical revisions may be not applicable. |
| Internal split geographic path | standalone + pytest-benchmark | implemented and measured in `diagnostics` | Real b1 ASV measurement is retained; diagnostic/private, not public API. |
| Internal split seismic path | standalone + pytest-benchmark | implemented and measured in `diagnostics` | Real b1 ASV measurement is retained; diagnostic/private, not public API. |
| Caller `column_stack` + geographic lookup | standalone | implemented and measured in `diagnostics` | Real b1 ASV measurement is retained; fresh predecessor reconciliation remains open. |
| Supported-Python comparison | Tox + custom reducer | ASV profile implemented and measured on b1 | Python 3.11–3.14 b1 ASV results exist; predecessor Tox matrix remains authoritative until parity is reviewed. |
| Release regression decision | custom release comparator | ASV normalization/check implemented | a10 corrects the gate to throughput slowdown; real closure evidence remains required. |
| Iterations/operations per unit time | standalone + cross-Python reducer | retained in predecessor and normalized ASV evidence | `operations_per_second` is derived from declared operations and measured duration. |

## b1 execution evidence and b2 correction

The supplied b1 preservation set contains successful smoke, release comparison/history,
dependency-matrix, supported-Python, reference-comparison, and diagnostic campaign run
records. It retains 910 `correctness_passed` setup records and 22 `not_applicable`
records. Genuine historical `not_applicable` examples correspond to revisions that lack
newer capabilities.

Real b1 ASV measurements now exist for the restored pinned-source scalar/batch cases,
pandas in-place paths, split geographic/seismic diagnostics, caller stacking, and the
supported-Python/dependency matrices. This closes the earlier "implemented but never
measured" gap for those roles. It does not establish predecessor-equivalent replacement
evidence without a fresh like-for-like reconciliation.

The direct ObsPy case is different. The b1 reference campaign returned success while the
ObsPy result was `NaN`/`not_applicable`. A retained environment diagnostic showed ObsPy
1.4.2 installed, but the interpreter contained NumPy 2.5.3 instead of requested 1.26.4,
`pip check` found pandas 2.1.4 incompatible with that NumPy, and Setuptools 84 lacked
`pkg_resources`, causing ObsPy import failure. b2 therefore treats requested-versus-
observed environment agreement as part of timing acceptance and changes a broken
requested comparator dependency from `not_applicable` to environment/build failure.

`REQ-PERF-017` remains open. The corrected b2 reference profile must be rerun, fresh
predecessor evidence must be reconciled with ASV, remaining failure-state examples and
report-regeneration evidence should be retained, and benchmark authority remains with the
predecessor path until that review explicitly closes migration parity.

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
