# feregion

`feregion` maps WGS84 longitude/latitude coordinates to Flinn-Engdahl (FE)
geographical region numbers. It provides scalar, NumPy, pandas, CSV, and
optional GeoJSON interfaces.

Normal lookup uses packaged generated data. ObsPy and network access are not
runtime dependencies.

## Install with uv

Add the core package to a project:

```bash
uv add feregion
```

Add an optional interface when needed:

```bash
uv add 'feregion[pandas]'
uv add 'feregion[geo]'
```

For a source checkout, create the development environment with:

```bash
uv sync
```

The repository uses `uv` directly. It does not use a Makefile.

## Python API

```python
import numpy as np
import feregion

feregion.lookup_number(12.0, 48.0)
# 543

feregion.lookup_region(12.0, 48.0)
# Region(number=543, name='GERMANY')

coordinates = np.array(
    [
        [12.0, 48.0],
        [-60.0, -30.0],
    ]
)
numbers = feregion.lookup_numbers(coordinates)
# array([543, 133], dtype=uint16)

feregion.numbers_to_names(numbers)
# array(['GERMANY', 'NORTHEASTERN ARGENTINA'], dtype='<U...')
```

A coordinate array always uses `[longitude, latitude]` column order. Use the
batch API when lookup throughput matters.

## pandas

```python
from feregion.pandas import lookup_dataframe

result = lookup_dataframe(frame)
result_with_names = lookup_dataframe(frame, include_names=True)
```

The default output adds `fe_number`. Region names are optional. Output columns
are additive and cannot replace existing input columns.

## Command line

```bash
uv run fe-region point 12 48 --name
uv run fe-region csv input.csv -o output.csv --include-names
uv run --extra geo fe-region geojson .cache/regions.geojson
```

Filesystem CSV output is transactional. The command writes a temporary sibling
and replaces the destination only after successful processing. It rejects
input/output path aliases and output-column collisions. stdout is a streaming
output and cannot be rolled back after a later row fails.

GeoJSON output contains the 754 active FE geographical regions. Region numbers
172, 299, and 550 are retired and have no active lookup cells, so the utility
does not create polygons for them.

## Development

Run the normal quality checks:

```bash
uv sync
uv run ruff check .
uv run mypy src/feregion tools benchmarks
uv run pytest -q
uv run pytest -q --cov=feregion --cov-branch --cov-report=term-missing
```

Build the wheel and source distribution with:

```bash
uv build
```

The generated FE runtime assets are version-controlled. The upstream ObsPy
`*.asc` source tables are not. Fetch the pinned and hash-verified source data
before source-reproduction tests, asset regeneration, or reference benchmarks:

```bash
uv run python -m tools.fetch_obspy_fe_data
uv run python -m tools.build_assets
```

The fetch command stores the verified files under the ignored `.cache/`
directory. Asset metadata records the pinned ObsPy revision and source hashes.

For benchmark dependencies, add the benchmark group to the environment:

```bash
uv sync --group benchmark
uv run --group benchmark pytest benchmarks --benchmark-only \
  --benchmark-json=benchmark.json
uv run --group benchmark python -m benchmarks.run_benchmark \
  --output benchmark-standalone.json
```

The routine benchmark suite covers in-process scalar, NumPy, name-conversion,
and pandas interfaces. It excludes CLI and GeoJSON timing. Generated benchmark
results are delivery evidence and are not repository source.

## Repository documents

The repository keeps only the current requirements and design iteration:

- `docs/feregion-requirements-v0.1.1a1-2026-08-13.md`;
- `docs/feregion-design-v0.1.1a1-2026-08-13.md`; and
- `docs/testing.md` as the stable test and verification guide.

A future iterative delivery replaces the two versioned contract filenames and
updates all repository references in the same change.

## License and provenance

The project is distributed under LGPL-3.0-only. The packaged lookup assets are
derived from Flinn-Engdahl source data distributed by ObsPy. See
`THIRD_PARTY_NOTICES.md` and `src/feregion/data/metadata.json` for provenance.
