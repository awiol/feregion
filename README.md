# feregion

`feregion` maps longitude/latitude coordinates to Flinn-Engdahl (FE)
geographical regions and their parent seismic regions. It provides scalar,
NumPy batch, hierarchy-conversion, pandas, CSV, and optional GeoJSON interfaces.

Normal lookup uses packaged processed data. Runtime lookup, names, hierarchy
conversion, and GeoJSON generation do not require ObsPy, ISC network access, or
another source service. pandas and Shapely remain optional interface dependencies.

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

For a Git checkout with its committed lock:

```bash
uv sync --locked
```

A clean source handoff intentionally omits `uv.lock`. An unlocked `uv sync` may
create a local dependency solution for inspection, but that state is not normal
repository verification evidence. The repository uses `uv` directly and does
not use a Makefile.

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

feregion.lookup_seismic_number(12.0, 48.0)
# 36

feregion.lookup_seismic_region(12.0, 48.0)
# SeismicRegion(number=36, name='Northwestern Europe')

feregion.geographic_to_seismic_number(543)
# 36
```

A coordinate array always uses `[longitude, latitude]` column order. By package
convention, these values are interpreted as WGS84 geographic degrees. The
package does not transform coordinates between CRSs, and the WGS84 convention
is separate from the historical FE degree-grid definition. Use batch lookup
when throughput matters.

Scalar lookup accepts Python integer/float values and NumPy integer/floating
scalars. Boolean values are rejected at runtime. Direct geographical
number-to-name and geographical-to-seismic operations accept only identifiers
that are active in the lookup table; retired identifiers 172, 299, and 550 are
not valid direct geographical inputs even though historical name slots are
retained in the packaged source-derived name array.

The pre-existing generic functions (`lookup_number`, `lookup_region`,
`lookup_numbers`, `number_to_name`, and `numbers_to_names`) remain geographical
compatibility interfaces. New code can use the explicit `geographic_*` and
`seismic_*` forms when the level matters.

Packaged geographical names are derived from pinned ObsPy `names.asc`; packaged
seismic names retain the declared ISC FE standards spelling. The project does
not claim that either source provides the unique historical FE naming convention.

Explicit `FlinnEngdahlLookup(table, names)` construction remains valid and is
geographical-only. Supplying the optional seismic arrays adds hierarchy
capability; a custom geographical-only engine does not silently borrow packaged
seismic data.

## pandas

```python
from feregion.pandas import lookup_dataframe

result = lookup_dataframe(frame)
result_with_names = lookup_dataframe(frame, include_names=True)
seismic = lookup_dataframe(frame, level="seismic", include_names=True)
```

The adapter requires distinct, unique longitude and latitude columns. Boolean
coordinate columns are rejected. Supported numeric dtypes retain their source precision through validation and FE
cell-ownership selection, including extended floating dtypes. This prevents a
wide floating value immediately beside an integer-degree boundary from being
rounded into the adjacent FE cell. Output columns are additive and cannot replace existing input
columns.

## Command line

```bash
uv run --locked fe-region point 12 48 --name
uv run --locked fe-region point 12 48 --level seismic --name
uv run --locked fe-region csv input.csv -o output.csv --level seismic --include-names
uv run --locked --extra geo fe-region geojson .cache/regions.geojson \
  --level seismic --properties seismic_number seismic_name
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

## GeoJSON generation

With the packaged lookup, GeoJSON emits 754 geographical features or 50
seismic features from the same one-degree cell grid. Geometry level and feature
annotations are independent. Default features contain the selected level's
`number` and `name`.

CLI examples:

```bash
# Default geographical regions with number and name.
uv run --locked --extra geo fe-region geojson .cache/geographic.geojson

# Compact seismic output with several properties after one option.
uv run --locked --extra geo fe-region geojson .cache/seismic.geojson \
  --level seismic --properties seismic_number seismic_name --no-metadata

# Include active geographical children as number/name objects and pretty-print.
uv run --locked --extra geo fe-region geojson .cache/seismic-with-children.geojson \
  --level seismic --properties seismic_number seismic_name geographic_regions \
  --label number-name --indent 2

# Ask for every property valid at the selected level.
uv run --locked --extra geo fe-region geojson .cache/geographic-full.geojson \
  --properties all --indent 2
```

The older repeatable `--property NAME` form remains supported for scripts, but
`--properties NAME [NAME ...]` is the preferred form when selecting several
fields. At seismic level, geographical child membership is represented only by
`geographic_regions`, whose value is a list such as
`[{"number": 543, "name": "GERMANY"}, ...]`. Scalar geographical properties and
the old parallel `geographic_numbers` / `geographic_names` lists are rejected.

Python API examples:

```python
from feregion.geojson import regions_geojson, write_regions_geojson

# Geographical features with explicit parent seismic fields.
geographic = regions_geojson(
    properties=(
        "geographic_number",
        "geographic_name",
        "seismic_number",
        "seismic_name",
    ),
    label="number-name",
)

# Seismic features with structured geographical child regions.
seismic = regions_geojson(
    level="seismic",
    properties=("seismic_number", "seismic_name", "geographic_regions"),
)

# Write a compact machine-oriented seismic file.
write_regions_geojson(
    "seismic.geojson",
    level="seismic",
    properties=("number",),
    include_metadata=False,
)
```

The Python GeoJSON API also accepts explicit lookup engines; their feature
populations and cross-level membership follow that engine. Collection metadata
identifies FE-1995 only when the selected engine is the packaged default
instance. Other explicit engines use null scheme/revision fields rather than
inferred provenance. The geometry is **area-equivalent**. Numeric lookup is
authoritative for coordinates exactly on integer cell boundaries because
ordinary closed polygons cannot encode every directional FE point-boundary rule.

## Development and verification

Run the canonical lock-preserving local checks with `uv`:

```bash
uv sync --locked --group dev
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy
uv run --locked pytest -q
uv run --locked pytest -q --cov=feregion --cov-branch --cov-report=term-missing
uv build
```

`uv build` has no lock flag; lock freshness is established by the preceding
`uv sync --locked`. Use unlocked dependency operations only when intentionally
creating or refreshing `uv.lock`, not as verification evidence.

Run the local compatibility matrix before a compatibility-sensitive push:

```bash
uv sync --locked --group dev
uv run --locked --group matrix tox run
```

The tox-uv matrix uses the standard `py311`, `py312`, `py313`, and `py314`
environment names plus a Python 3.11 `minimum` environment. Normal compatibility
environments are lock-backed. The `minimum` environment intentionally bypasses
the lock and resolves the project plus its `test` extra together with
`lowest-direct`, so NumPy and pandas lower bounds are selected in one dependency
transaction. The environment prints its resolved Python, NumPy, pandas, Shapely,
and pytest versions before running tests. The special lower-bound environment is
recreated for each run so stale tox installer state cannot affect resolution. Run
only that environment with `uv run --locked --group matrix tox run -e minimum`.
uv-backed tox environments can use uv-managed Python interpreters, so the required
interpreters do not all need to be installed manually in advance.

GitHub Actions verifies Python 3.11, 3.12, 3.13, and 3.14. Dedicated jobs also run the
installed ObsPy oracle and the same tox-uv minimum-dependency environment. A separate
quality job runs Ruff, mypy public typing, distribution builds, wheel archive
inspection, and dependency-isolated wheel verification. A scheduled/manual job
performs the live ISC semantic comparison without making pull-request tests
network-dependent.

`uv.lock` is committed and is the dependency-resolution authority for normal
repository and CI environments. Use `--locked` in verification workflows so a
stale lock fails instead of being refreshed implicitly.

## Upstream FE source data

Generated runtime assets are version-controlled. Downloaded upstream source
material is not. Maintainers retrieve both source families before complete
asset regeneration:

```bash
uv run --locked python -m tools.fetch_obspy_fe_data
uv run --locked python -m tools.fetch_isc_fe_regions
uv run --locked python -m tools.build_assets
```

The ObsPy fetcher pins tag `1.4.2` at immutable commit
`a629e8c021052904b6b8d62699d03f2a3721ae63` and verifies source-file SHA-256
values. The ISC fetcher parses the declared FE standards page, validates all 50 seismic
regions and 754 active geographical memberships, and compares the normalized
content with a literal reviewed semantic SHA-256. The digest is not recomputed
automatically from the Python hierarchy declarations it protects, so a coherent
name/membership edit cannot silently redefine the expected source.
`tools/build_assets.py` converts verified retrieved sources into the four runtime
arrays shipped with the package.

The source-data license status remains unresolved where an explicit reuse grant
has not been established. See `src/feregion/data/metadata.json` and
`THIRD_PARTY_NOTICES.md`.

## Development checks

Use the repository development environment and install the Git hooks once:

```bash
uv sync --locked --group dev
uv run --locked pre-commit install
```

The pre-commit pipeline formats Python files with Ruff, runs Ruff lint checks,
runs mypy over the public package modules and downstream-consumer typing fixture,
and then delegates behavioral tests to tox's `local` environment. Hosted quality
verification runs the same static evidence because the wheel ships `py.typed`. Run the
commit-time pipeline manually with:

```bash
uv run --locked pre-commit run --all-files
```

## Benchmarks

Install benchmark dependencies and run the repository harnesses:

```bash
uv sync --locked --group benchmark
uv run --locked --group benchmark pytest benchmarks --benchmark-only \
  --benchmark-json=benchmark.json
uv run --locked --group benchmark python -m benchmarks.run_benchmark \
  --output benchmark-standalone.json
```

Routine benchmarks cover in-process scalar, batch, name-conversion, and pandas
interfaces. They exclude CLI and GeoJSON timing. Generated benchmark results are
delivery evidence and are not repository source.

`PERF-INV-001` is resolved for package-internal use. Controlled baseline/candidate
measurements show material stacking, seismic revalidation, and peak-memory cost.
The core therefore provides package-internal equal-length one-dimensional
longitude/latitude paths used by pandas, and coordinate-to-seismic lookup trusts
only geographical numbers produced by the same validated engine. The public
`(n, 2)` NumPy contract remains unchanged. A public split-array API remains
deferred until an external consumer need justifies another compatibility surface.


Compare the same locked benchmark environment across all explicitly supported
Python versions:

```bash
uv run --locked python -m tools.fetch_obspy_fe_data
uv run --locked --group matrix --group benchmark tox run \
  -e benchmark-py311,benchmark-py312,benchmark-py313,benchmark-py314,benchmark-report
```

The per-version JSON files and `python-comparison.md` are written below
`.tox/benchmark-results/`. The combined report compares eight representative
throughput metrics, records exact Python, NumPy, and pandas versions, and reports
the geometric mean explicitly as an equal-weight summary of those selected
metrics rather than as a product workload model.

For release-to-release regression review, compare two raw standalone benchmark
records produced on the same controlled host/interpreter/dependency/workload
context:

```bash
uv run --locked --group benchmark python -m benchmarks.compare_releases \
  --baseline baseline.json --candidate candidate.json --fail-on-trigger
```

The review trigger is a slowdown greater than 25 percent at two adjacent batch
sizes of at least 10,000 points. If no comparable accepted baseline exists, the
release-specific performance gate remains incomplete rather than being reported
as passed.

## Clean repository handoff

To hand the current repository source to another reviewer or agent without local
caches, environments, run output, IDE files, or `uv.lock`, run:

```bash
uv run --locked python -m tools.export_repository
```

The exporter packages only Git-tracked paths, but reads their current
working-tree bytes, so tracked Ruff/pre-commit edits do not need a special
filesystem cleanup first. It warns about non-ignored untracked files; stage or
commit genuine new source before handoff, or use `--fail-on-untracked` to require
a clean tracked-source boundary.

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
