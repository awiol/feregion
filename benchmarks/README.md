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
