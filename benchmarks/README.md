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

## `0.4` ASV benchmark system

Reviewed post-b3 evidence satisfies `REQ-PERF-017`. ASV plus the project-owned
campaign/evidence/regression layers are the **primary performance-evidence path** for
`0.4`. The predecessor commands above remain runnable for compatibility checks,
investigation, and historical provenance; they no longer define a second co-equal
release-performance authority. See `docs/benchmark-migration-parity.md` for the accepted
parity record.

`feregion` owns
case semantics, source-oracle correctness, historical adapters, normalized evidence,
throughput interpretation, and release decisions; ASV owns revision/environment
mechanics, package build/install, timing, raw samples, retained history, and the
technical static site.

Authoritative ASV setup now requires the pinned FE source tables because correctness
is checked against the independent source scanner before timing:

```bash
uv run python -m tools.fetch_obspy_fe_data
uv sync --locked --group benchmark
uv run --locked --group benchmark asv check --config asv.conf.json
```

### Maintained load grid and throughput

Public batch cases support the 1-2-5 grid from 1 through 50,000,000 points. Some
reference/diagnostic cases intentionally use smaller bounded grids. Every normalized
throughput-capable record retains the operation count and
`operations_per_second = operations / statistic_seconds`; elapsed duration alone is
not the project release metric.

### Canonical campaigns

`benchmarks/campaigns/` contains maintained operator campaigns:

- `smoke.toml` — fast current-candidate integration check;
- `release-compare.toml` — previous benchmark candidate versus `HEAD`;
- `release-history.toml` — representative backward-compatible history;
- `head-full.toml` — public-semantic current suite over the full 1-2-5 grid;
- `python-supported.toml` — supported CPython sensitivity;
- `numpy-sensitivity.toml` — selected NumPy sensitivity;
- `pandas-sensitivity.toml` — pandas copy/in-place sensitivity;
- `dependency-matrix.toml` — bounded sparse NumPy/pandas union;
- `reference-comparison.toml` — feregion, direct ObsPy, and pinned-source
  comparator measurements; and
- `diagnostics.toml` — private split-vector, caller-stacking, and pandas in-place
  diagnostics retained for migration parity.

Plan before measuring:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign plan \
  benchmarks/campaigns/smoke.toml
```

Run the real smoke path:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign run \
  benchmarks/campaigns/smoke.toml
```

For routine ASV release comparison:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign run \
  benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign compare \
  benchmarks/campaigns/release-compare.toml
uv run --locked --group benchmark python -m benchmarks.campaign check \
  benchmarks/campaigns/release-compare.toml
```

`check` consumes retained ASV results and setup-state sidecars. It accepts only
stored benchmark versions mapped to the project case version and only
correctness-passed timing for the release decision. The project rule is a >25%
**throughput** slowdown at two adjacent maintained sizes of at least 10,000 points;
this is not equivalent to a 25% duration increase.

Populate the maintained ASV migration evidence and rebuild the report with:

```bash
uv run --locked --group benchmark python -m benchmarks.release_workflow refresh
```

For a review run that also refreshes historical evidence and appends more compatible
samples:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --history --repetitions 15 --rounds 7 --append-samples
```

The refresh includes the reference-comparison and diagnostic campaigns in addition
to current/full/dependency/Python coverage. This does not change the transitional
authority rule: compare the ASV output with predecessor evidence before accepting
migration closure.

Rebuild and preview without timing work:

```bash
uv run --locked --group benchmark python -m benchmarks.release_workflow report
uv run --locked --group benchmark python -m benchmarks.release_workflow preview
```

### Evidence and failure states

ASV benchmark setup writes retained sidecars under `.asv/feregion-state/`. The
normalized evidence adapter uses them to distinguish correctness failure,
environment/oracle unavailability, explicit not-applicable capability, execution
failure, and measured results. Campaign execution records revision-level run status
under `.asv/feregion-runs/`. Each run also retains a content-addressed effective plan
under `.asv/feregion-plans/` and links the run record to that plan. b2 also verifies requested-versus-installed dependency
versions, requested imports, and `pip check` before timing and retains the result under
`.asv/feregion-environments/`. A broken explicitly requested comparator dependency is
environment/build failure, not `not_applicable`.

Stored ASV benchmark `version` is an input to comparability. An unknown semantic
version is normalized as incompatible instead of being assigned the current project
`case_version`.

### Revision and build contracts

Campaign `revisions` are single identities such as `HEAD`, a tag, or a commit SHA.
Do not put Git range syntax such as `HEAD^!`, `main..HEAD`, or `HEAD~1` in a
campaign. `plan` resolves each identity to one immutable SHA and `run` converts it
to ASV's exact-single-commit selector internally.

Both persistent and generated ASV configs build only the `feregion` wheel with
`pip wheel --no-deps` and install it with `pip install --no-deps --force-reinstall`.
Dependency versions belong to the selected ASV environment profile.

Generated `.asv/` state is benchmark evidence/derived output and remains outside the
source tree. Preserve `.asv/results`, `.asv/feregion-state`, relevant
`.asv/feregion-runs`, `.asv/feregion-plans`, `.asv/feregion-environments`, and `.asv/feregion-reports`
together when retaining migration evidence. The release check accepts only result
environments permitted by the selected campaign profile; same-case rows from another
profile are not interchangeable. Create a machine-readable handoff with:

```bash
uv run --locked --group benchmark python -m benchmarks.evidence_bundle
```

The ZIP includes a manifest with hashes and available/missing evidence families and
excludes rebuildable `.asv/html` by default.
