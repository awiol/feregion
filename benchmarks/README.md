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

The commands above are predecessor migration evidence retained temporarily under
`REQ-PERF-017`. The authoritative `0.4` architecture is ASV-driven: `feregion`
owns semantic benchmark cases, workloads, compatibility adapters, campaign intent,
normalized evidence, and the release decision; ASV owns environment/build/timing,
raw samples, history, comparison display, and static report generation.

The detailed human runbook is `docs/benchmark-operations.md`. Read it before an
authoritative campaign; it explains why each step exists, what evidence it creates,
what can be safely regenerated, and how publication differs from measurement.

### Maintained load grid

Batch cases support the 1-2-5 grid from 1 through 50,000,000 points:

```text
1, 2, 5, 10, 20, 50, 100, 200, 500,
1_000, 2_000, 5_000, 10_000, 20_000, 50_000,
100_000, 200_000, 500_000,
1_000_000, 2_000_000, 5_000_000,
10_000_000, 20_000_000, 50_000_000
```

The largest cases are intentionally high-memory. A campaign may select a subset;
resource exhaustion is not a valid timing result.

### Canonical campaigns

`benchmarks/campaigns/` contains maintained operator campaigns:

- `smoke.toml` — fast current-candidate integration check;
- `release-compare.toml` — previous accepted benchmark candidate versus `HEAD`;
- `release-history.toml` — backward-compatible representative release history;
- `head-full.toml` — all cases over the complete maintained load grid;
- `python-supported.toml` — supported CPython sensitivity;
- `numpy-sensitivity.toml` — selected NumPy sensitivity;
- `pandas-sensitivity.toml` — selected pandas sensitivity; and
- `dependency-matrix.toml` — sparse union of NumPy and pandas sensitivity points.

Plan before measuring:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign plan benchmarks/campaigns/smoke.toml
```

Run the real smoke path:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/smoke.toml
```

For routine release comparison:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign compare benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign check benchmarks/campaigns/release-compare.toml
```

`compare` is ASV's generic comparison view. `check` is the project acceptance
rule: it consumes retained ASV results, writes normalized evidence under
`dist/benchmarks/`, and applies the >25% slowdown rule at two adjacent maintained
1-2-5 sizes of at least 10,000 points. Exit status `0` means complete/no trigger,
`1` means triggered, and `2` means incomplete or ambiguous evidence.

Populate the routine current-release evidence and rebuild the complete retained-result report with one command:

```bash
uv run --locked --group benchmark python -m benchmarks.release_workflow refresh
```

For a review/promotion run that also refreshes historical evidence and appends substantially more samples to compatible retained results:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --history --repetitions 15 --rounds 7 --append-samples
```

The refresh covers the full `HEAD` suite, routine release comparison, supported-Python matrix, and sparse dependency matrix. The dependency matrix includes both pandas benchmark paths. Canonical campaigns overlap at some cells, so append mode can produce unequal sample counts across the result database; retained raw samples remain the evidence.

Rebuild and preview from retained measurements without timing work:

```bash
uv run --locked --group benchmark python -m benchmarks.release_workflow report
uv run --locked --group benchmark python -m benchmarks.release_workflow preview
```

ASV loads the local `feregion` output publisher. The generated site keeps native ASV Grid/List/Graph/Regressions views and adds a project summary with human-readable benchmark metadata and curated load-scaling links. The runbook documents GitHub Pages staging and explicit push. External publication is never implied by measurement or report generation.

### Revision and build contracts

Campaign `revisions` are single identities such as `HEAD`, a tag, or a commit SHA.
Do not place Git range syntax such as `HEAD^!`, `main..HEAD`, or `HEAD~1` in a
campaign. `plan` resolves each identity to one immutable SHA and `run` converts it
to ASV's exact-single-commit selector internally.

Both persistent and generated ASV configs build only the `feregion` wheel with
`pip wheel --no-deps` and install it with `pip install --no-deps --force-reinstall`.
NumPy and pandas versions belong to the selected ASV environment profile. This
keeps the project build cache unambiguous and prevents installation from replacing
the benchmark matrix dependencies.

Generated `.asv/` state is benchmark evidence/derived output and remains outside
the source tree. Preserve authoritative `.asv/results` in an approved durable
location; `.asv/html` can be rebuilt from those results.
