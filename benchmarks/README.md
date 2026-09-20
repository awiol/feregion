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

## Predecessor compatibility harness

The repository still contains the earlier standalone timer, `pytest-benchmark` suite,
Tox supported-Python benchmark matrix, and raw JSON release comparator. These tools are
retained for compatibility checks, investigation, and historical provenance; they are
not the primary release-performance authority.

The standalone harness directly compares batch lookup with the source-table scanner on
identical deterministic arrays and retains matrix/caller-stacking/internal-split/seismic
composition diagnostics. Private split-vector measurements are implementation evidence,
not public API. The predecessor Python matrix records per-interpreter dependency identity
and normalized representative metrics, while the raw release comparator rejects
incompatible environment/workload records before applying its historical threshold.

Executable setup and compatibility commands are maintained only in
`docs/benchmark-operations.md` so this architecture note cannot drift from the operator
runbook.

## `0.4` ASV benchmark system

Reviewed post-b3 evidence satisfies `REQ-PERF-017`. ASV plus the project-owned
campaign/evidence/regression layers are the primary performance-evidence path for `0.4`.
The predecessor commands described above remain compatibility/investigation surfaces and
historical provenance; they no longer define a co-equal release-performance authority.

`feregion` owns case semantics, source-oracle correctness, historical adapters,
normalized evidence, throughput interpretation, and release decisions. ASV owns
revision/environment mechanics, project build/install for benchmark environments,
timing, raw samples, retained history, and static reporting.

### Maintained campaign roles

`benchmarks/campaigns/` contains stable operator campaign definitions:

- `smoke.toml` — fast current-candidate integration check;
- `release-compare.toml` — explicit accepted baseline versus `HEAD`;
- `release-history.toml` — representative backward-compatible history;
- `head-full.toml` — public-semantic current suite over the full 1-2-5 grid;
- `python-supported.toml` — supported CPython sensitivity;
- `numpy-sensitivity.toml` and `pandas-sensitivity.toml` — focused dependency studies;
- `dependency-matrix.toml` — bounded sparse NumPy/pandas union;
- `reference-comparison.toml` — feregion/direct-ObsPy/pinned-source comparison; and
- `diagnostics.toml` — targeted private-path diagnostics.

The release campaign contains a stable `__BASELINE__` placeholder. The accepted prior
candidate is supplied explicitly by the operator and resolved to one immutable commit in
the retained effective plan. It is not inferred from Git tag ordering and is not stored
as mutable per-candidate campaign source.

### Evidence and failure states

Benchmark setup writes state under `.asv/feregion-state/`; campaign execution records
revision outcomes under `.asv/feregion-runs/`; effective content-addressed run contracts
are retained under `.asv/feregion-plans/`; environment-integrity records live under
`.asv/feregion-environments/`; and report rebuild evidence is retained under
`.asv/feregion-reports/`. Normalized evidence distinguishes measured, unavailable,
failed, incompatible, and not-applicable states rather than collapsing them into missing
numbers.

Throughput-capable normalized records retain operation count and
`operations_per_second = operations / statistic_seconds`. Environment-integrity checks
verify requested-versus-installed dependencies and `pip check` before accepted timing.
The observed `asv-runner` version from the timed environment is retained separately from
the operator ASV identity.

### Operator authority

`docs/benchmark-operations.md` is the single maintained benchmark command/runbook
authority. It defines setup, explicit release-baseline input, proportional refresh
scopes, historical/reference/diagnostic triggers, report rebuild, evidence handoff,
preview, and publication. Do not duplicate executable workflow instructions here.

The machine-readable evidence handoff excludes rebuildable `.asv/html` and retains the
raw evidence/configuration needed to review or reconstruct benchmark conclusions.
