# feregion benchmarks

These harnesses measure the in-process lookup interfaces:

- scalar region-number lookup;
- scalar `Region` lookup;
- scalar region-number-to-name conversion;
- NumPy batch region-number lookup;
- matrix-versus-split internal batch representation diagnostics;
- geographical and seismic batch lookup;
- batch region-number-to-name conversion; and
- pandas lookup with and without names.

Routine benchmarking excludes CLI and GeoJSON because their dominant costs are
outside the core FE lookup path.

## Prepare the benchmark environment

Fetch the hash-verified pinned source tables and install benchmark dependencies:

```bash
uv run python -m tools.fetch_obspy_fe_data
uv sync --group benchmark
```

Run the `pytest-benchmark` suite:

```bash
uv run --group benchmark pytest benchmarks --benchmark-only \
  --benchmark-json=benchmark.json
```

Run the standalone harness:

```bash
uv run --group benchmark python -m benchmarks.run_benchmark \
  --output benchmark-standalone.json
```

The standalone report directly compares batch `lookup_numbers()` with the
source-table scanner on identical deterministic arrays of 100, 1,000, 10,000,
and 100,000 coordinates. It also records matrix, caller-stacking, internal
split-vector, and seismic-composition diagnostics used to evaluate the batch
optimization. Private split-vector measurements are implementation evidence, not
a supported public API. ObsPy provides an additional reference-implementation
comparison when installed.

Benchmark code is repository and source-distribution tooling. It is not part of
the installed runtime package. Generated results are delivery evidence and
should stay outside the repository.

## Compare supported Python versions

The local benchmark matrix reuses the repository lock to reduce dependency drift
between interpreter runs. Generate/update `uv.lock` locally, fetch the verified
source tables once, then run:

```bash
uv run --locked --group matrix --group benchmark tox run \
  -e benchmark-py311,benchmark-py312,benchmark-py313,benchmark-py314,benchmark-report
```

Raw standalone results are written to `.tox/benchmark-results/python-*.json`.
The final environment writes `.tox/benchmark-results/python-comparison.md`. The
report compares eight representative scalar, batch, name-conversion, and pandas
throughput metrics, normalizes them to Python 3.11, and records the exact NumPy
and pandas versions used by each interpreter environment. Run all interpreter
measurements on the same machine when using the ratios as performance evidence.


## Compare package releases

Release-to-release regression is separate from the source-scanner speedup and
from the cross-Python matrix. Run the same standalone harness for the accepted
baseline package and candidate in the same controlled host/interpreter/dependency
context. Then compare the raw JSON records:

```bash
uv run --group benchmark python -m benchmarks.compare_releases \
  --baseline baseline.json --candidate candidate.json --fail-on-trigger
```

The comparison requires matching recorded platform, interpreter/compiler, machine,
CPU model, logical CPU count, NumPy version, seed, coordinate distribution, and
timing contract. It triggers review if candidate median batch throughput is more
than 25 percent slower at two adjacent recorded sizes of at least 10,000 points.
The harness cannot establish CPU power/frequency policy; control that externally.

## `0.4` ASV-driven benchmark system

The commands above are predecessor migration evidence retained temporarily under `REQ-PERF-017`. The `0.4` source implements the ASV-driven system below; predecessor runners are removed only after vertical-slice parity is observed.

The new operator surface is:

```bash
uv run --locked --group benchmark asv check --config asv.conf.json
uv run --locked --group benchmark python -m benchmarks.campaign plan benchmarks/campaigns/release-history.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/release-history.toml
uv run --locked --group benchmark python -m benchmarks.campaign compare benchmarks/campaigns/release-history.toml
uv run --locked --group benchmark python -m benchmarks.campaign report benchmarks/campaigns/release-history.toml
```

`plan` is read-only. `run`, `compare`, and `report` delegate execution/history/report generation to ASV; they do not implement a second timer or environment manager. Generated `.asv/` state is local evidence and is not committed to the source tree.

The ASV-discovered package is `benchmarks/asv_suite/`; predecessor pytest-benchmark code stays outside it. Campaigns generate a temporary ASV config in the repository root and pass it with the subcommand-local `--config` option so ASV's config-directory working-directory behavior keeps `.asv/` and benchmark paths rooted in the repository.

The `0.4.0` target uses a thin hybrid architecture:

- `feregion` owns stable benchmark semantics, deterministic workloads,
  correctness oracles, historical-version adapters, campaign intent, normalized
  evidence, and the release-regression rule;
- ASV owns revision/environment/build/timing/sample/history/static-site mechanics;
  and
- the campaign layer translates small TOML operator intent into ASV execution
  rather than implementing another runner.

The implementation targets ASV `>=0.6.6,<0.7` and records the exact executing version in authoritative evidence. Authoritative release,
dependency-sensitivity, and public-history campaigns retain raw timing samples
and exact ASV/asv-runner versions.

### Campaign profiles

The fixed `release-history` profile uses CPython 3.12 with NumPy 1.26.4 and,
for pandas cases, pandas 2.1.4 while selected historical revisions remain
build-compatible with that environment. The supported-Python profile covers
CPython 3.11 through 3.14. The dependency-sensitivity profiles preserve the
previously selected sparse matrix:

- CPython 3.12 with NumPy 1.26.4, 2.0.2, 2.2.6, and 2.5.2;
- CPython 3.12 with NumPy 1.26.4 and pandas 2.1.4, 2.2.3, 2.3.3, and 3.0.5.

Operators can select benchmark cases, load sizes, repetitions, exact package
revisions, and one environment profile through campaign configuration. Campaign
commands cover planning, running, comparing, and report building; external site
publication remains a separate verified workflow. Timed measurement is serial by
default.

### Required migration vertical slice

The first ASV slice covers `lookup_numbers` at 1, 100, 1,000, 10,000, 100,000,
and 1,000,000 points; `0.3.0b1` plus at least one materially different older
revision; one dependency-sensitivity profile; raw samples; normalized project
evidence; the existing >25% adjacent-load release rule; and an ASV static-site
build from retained results.

The standalone timer, `pytest-benchmark` timing suite, Tox benchmark matrix, and
custom cross-Python report are removed only after their required evidence is
covered by the ASV path. They are not intended to remain as a second authoritative
benchmark system.
