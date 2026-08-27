# feregion benchmarks

These harnesses measure the in-process lookup interfaces:

- scalar region-number lookup;
- scalar `Region` lookup;
- scalar region-number-to-name conversion;
- NumPy batch region-number lookup;
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
and 100,000 coordinates. It records both medians and candidate speedup. ObsPy
provides an additional reference-implementation comparison when installed.

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
