# feregion

`feregion` maps WGS84 longitude/latitude coordinates to Flinn-Engdahl (FE)
geographical region numbers. It provides scalar, NumPy batch, pandas, CSV, and
optional GeoJSON interfaces.

Normal lookup uses packaged generated data. Runtime lookup does not require
ObsPy, network access, pandas, or Shapely.

## Install with uv

Add the core package:

```bash
uv add feregion
```

Add an optional interface when needed:

```bash
uv add 'feregion[pandas]'
uv add 'feregion[geo]'
```

For a source checkout:

```bash
uv sync
```

The repository uses `uv` directly and does not use a Makefile.

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

A coordinate array always uses `[longitude, latitude]` column order. Use batch
lookup when throughput matters.

`number_to_name()` and `numbers_to_names()` return **packaged region names**
derived from ObsPy 1.4.2 `names.asc`. The project does not claim that this is
the only naming convention used by all historical FE sources.

Explicit `FlinnEngdahlLookup` construction copies the supplied table and name
arrays. Later mutation of caller-owned arrays cannot change engine behavior.

## pandas

```python
from feregion.pandas import lookup_dataframe

result = lookup_dataframe(frame)
result_with_names = lookup_dataframe(frame, include_names=True)
```

The adapter requires distinct, unique longitude and latitude columns. Boolean
coordinate columns are rejected. Supported numeric dtypes retain their source
precision through finiteness and range classification, including extended
floating dtypes. Output columns are additive and cannot replace existing input
columns.

## Command line

```bash
uv run fe-region point 12 48 --name
uv run fe-region csv input.csv -o output.csv --include-names
uv run --extra geo fe-region geojson .cache/regions.geojson
```

Filesystem CSV input must be valid UTF-8 and satisfy strict CSV syntax. CSV
headers must contain unique field names. Every data row must contain exactly
the number of fields declared by the header. Filesystem output uses atomic
publication through a temporary sibling and `os.replace()`. Existing destination
permission bits are preserved. New files use normal process-umask semantics.

A failed filesystem conversion does not publish a new partial destination.
stdout is a streaming sink and can contain earlier rows if a later row fails.
The filesystem guarantee does not claim crash durability, directory fsync, ACL
preservation, or owner preservation.

GeoJSON output contains the 754 active region numbers represented by the
one-degree cell grid. The geometry is **area-equivalent**. Numeric lookup is
authoritative for coordinates exactly on integer cell boundaries because
ordinary closed polygons cannot encode every directional FE point-boundary rule.

## Development and verification

Run local checks with `uv`:

```bash
uv sync
uv run ruff check .
uv run pytest -q
uv run pytest -q --cov=feregion --cov-branch --cov-report=term-missing
uv build
```

GitHub Actions verifies Python 3.11, 3.12, 3.13, and 3.14. Dedicated jobs also run the
installed ObsPy oracle and the declared lower dependency bounds. A separate
quality job runs Ruff, distribution builds, wheel archive inspection, and
dependency-isolated wheel verification.

`uv.lock` is committed and is the dependency-resolution authority for normal
repository and CI environments. Use `--locked` in verification workflows so a
stale lock fails instead of being refreshed implicitly.

## Upstream FE source data

Generated runtime assets are version-controlled. Downloaded ObsPy `*.asc`
source tables are not.

Fetch the source tables before source-reproduction tests, asset regeneration, or
source-table baseline benchmarks:

```bash
uv run python -m tools.fetch_obspy_fe_data
uv run python -m tools.build_assets
```

The fetch tool uses ObsPy tag `1.4.2` at immutable commit
`a629e8c021052904b6b8d62699d03f2a3721ae63`. It stores files under the ignored
`.cache/` directory and verifies each SHA-256 digest before use.

ObsPy states that its software is licensed under LGPL v3.0. The historical FE
source-table license is not established by that statement and is recorded as
unresolved provenance in `src/feregion/data/metadata.json` and
`THIRD_PARTY_NOTICES.md`.

## Development checks

Use the repository development environment and install the Git hooks once:

```bash
uv sync --locked --group dev
uv run --locked pre-commit install
```

The pre-commit pipeline formats Python files with Ruff, runs Ruff lint checks,
and then runs the full pytest suite. Run the same pipeline manually with:

```bash
uv run --locked pre-commit run --all-files
```

## Benchmarks

Install benchmark dependencies and run the repository harnesses:

```bash
uv sync --locked --group benchmark
uv run --group benchmark pytest benchmarks --benchmark-only \
  --benchmark-json=benchmark.json
uv run --group benchmark python -m benchmarks.run_benchmark \
  --output benchmark-standalone.json
```

Routine benchmarks cover in-process scalar, batch, name-conversion, and pandas
interfaces. They exclude CLI and GeoJSON timing. Generated benchmark results are
delivery evidence and are not repository source.

## Project documents

The maintained contract set uses stable filenames. Git history records document revisions:

- `docs/feregion-requirements.md`;
- `docs/feregion-engineering-requirements.md`;
- `docs/feregion-repository-delivery-requirements.md`;
- `docs/feregion-design.md`;
- `docs/feregion-quality-assurance.md`;
- `docs/feregion-decisions.md`; and
- `docs/feregion-verification-traceability.md`.

`docs/testing.md` is the maintainer procedure. When behavior changes, update the affected maintained documents in the same repository change.

## License and provenance

The `feregion` project is distributed under LGPL-3.0-only. That project license
does not by itself establish the license of upstream FE source data. See
`THIRD_PARTY_NOTICES.md` and `src/feregion/data/metadata.json` for the recorded
provenance and limitation.
