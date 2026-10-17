# feregion user guide

This guide is the task-oriented user documentation for `feregion`. It explains which
public interface to use, the coordinate and result contracts that matter in practice,
important edge cases, optional integrations, and the evidence boundaries behind the
package's performance guidance.

For release-by-release changes, see `whats-new.md`. For measured benchmark records and
their exact environments, see `benchmark-results.md`. For a focused comparison with
ObsPy, see `obspy-or-feregion.md`.

## Choose the interface that matches your data

Use the interface that matches the representation you already have and the scientific
result you need. The matrix and split-vector batch interfaces share the same FE ownership
kernel; they are not separate scientific implementations.

| Input already available | Result needed | Preferred interface |
|---|---|---|
| one longitude + latitude | geographical ID | `lookup_geographic_number()` |
| one longitude + latitude | geographical ID + name | `lookup_geographic_region()` |
| one longitude + latitude | seismic ID | `lookup_seismic_number()` |
| one longitude + latitude | seismic ID + name | `lookup_seismic_region()` |
| NumPy-compatible `(n, 2)` coordinates | geographical IDs | `lookup_geographic_numbers()` |
| NumPy-compatible `(n, 2)` coordinates | seismic IDs | `lookup_seismic_numbers()` |
| separate one-dimensional longitude + latitude arrays | geographical IDs | `lookup_geographic_numbers_from_vectors()` |
| separate one-dimensional longitude + latitude arrays | seismic IDs | `lookup_seismic_numbers_from_vectors()` |
| geographical IDs | geographical names | `geographic_number_to_name()` / `geographic_numbers_to_names()` |
| geographical IDs | seismic IDs | `geographic_to_seismic_number()` / `geographic_numbers_to_seismic_numbers()` |
| seismic IDs | seismic names | `seismic_number_to_name()` / `seismic_numbers_to_names()` |
| pandas DataFrame | annotated DataFrame | `feregion.pandas.lookup_dataframe()` |
| CSV stream/file | annotated CSV | `fe-region csv` |
| FE regions | area-equivalent GeoJSON | `feregion.geojson.regions_geojson()` or `fe-region geojson` |

Do not build an `(n, 2)` array only to call the matrix interface when longitude and
latitude are already separate. Conversely, do not split an existing coordinate matrix
only to call the vector interface.

The historical generic names `lookup_number()`, `lookup_region()`, `lookup_numbers()`,
`number_to_name()`, `numbers_to_names()`, and `Region` remain supported compatibility
aliases for geographical operations. New code should prefer the explicit geographical
and seismic names because they make the FE level part of the call contract.

## Coordinate semantics

`feregion` accepts coordinates in `[longitude, latitude]` order. The package convention
interprets them as WGS84 geographic degrees:

- longitude is in the inclusive range `[-180, 180]`;
- latitude is in the inclusive range `[-90, 90]`;
- values must be finite real numbers;
- Boolean coordinates are rejected;
- the package does not transform coordinates between coordinate reference systems.

The WGS84 input convention is a package interface convention. It does not claim that the
historical FE tables were originally defined as a WGS84 geodetic product.

The FE lookup is based on a one-degree ownership grid with directional rules at exact
integer boundaries. Numeric lookup is authoritative for those point-boundary cases.
GeoJSON output is area-equivalent geometry built from closed polygons and therefore
cannot encode every directional point-boundary rule exactly.

Validation preserves the source numeric dtype through finite/range checks and FE
cell-ownership selection before integer indices are formed. This matters for wide
floating dtypes immediately beside integer-degree boundaries: `feregion` does not
silently coerce every input to `float64` before deciding ownership.

## Scalar lookup

Use scalar functions when the caller has one coordinate pair and wants a Python scalar
or a small immutable region object.

```python
import feregion

number = feregion.lookup_geographic_number(12.0, 48.0)
region = feregion.lookup_geographic_region(12.0, 48.0)
seismic = feregion.lookup_seismic_region(12.0, 48.0)

assert number == 543
assert region.number == 543
assert region.name == "GERMANY"
assert seismic.number == 36
```

`lookup_geographic_region()` returns `GeographicRegion`; `lookup_seismic_region()`
returns `SeismicRegion`. These dataclasses are immutable.

## Batch lookup from an existing matrix

Use the matrix form when coordinates already exist as an `(n, 2)` numeric array-like
object in `[longitude, latitude]` column order.

```python
import numpy as np
import feregion

coordinates = np.array(
    [
        [12.0, 48.0],
        [-60.0, -30.0],
    ]
)

geographic = feregion.lookup_geographic_numbers(coordinates)
seismic = feregion.lookup_seismic_numbers(coordinates)

assert geographic.dtype == np.uint16
assert seismic.dtype == np.uint8
```

The matrix form requires shape `(n, 2)`. A transposed `(2, n)` array, a single pair with
shape `(2,)`, or an array with more than two columns is rejected rather than guessed or
reshaped.

## Batch lookup from separate vectors

Use the split-vector form when longitude and latitude already exist as separate
one-dimensional vectors.

```python
import numpy as np
import feregion

longitude = np.array([12.0, -60.0])
latitude = np.array([48.0, -30.0])

geographic = feregion.lookup_geographic_numbers_from_vectors(longitude, latitude)
seismic = feregion.lookup_seismic_numbers_from_vectors(longitude, latitude)
```

The two vectors must both be one-dimensional and have exactly the same shape. The API
does not broadcast a scalar latitude, a length-one vector, or otherwise mismatched
inputs. Empty vectors are supported. Non-contiguous one-dimensional NumPy views are
supported. The inputs are not modified.

Geographical batch lookup returns `uint16[n]`; seismic batch lookup returns `uint8[n]`.
These result dtypes are part of the supported API and are independent of the caller's
input dtype.

## Names and geographical-to-seismic conversion

Use conversion functions when the region identifiers are already known. Do not repeat a
coordinate lookup merely to obtain a name or parent seismic ID.

```python
import numpy as np
import feregion

names = feregion.geographic_numbers_to_names(np.array([543, 133]))
parents = feregion.geographic_numbers_to_seismic_numbers(np.array([543, 133]))
```

The plural conversion functions accept NumPy-compatible array-like inputs and preserve
the input shape. A scalar array-like input produces a zero-dimensional NumPy array. Use
the singular functions when a Python scalar result is required.

Direct geographical conversion accepts only active geographical identifiers. Historical
name-table slots 172, 299, and 550 remain present for source fidelity but are retired and
are not valid active geographical inputs.

Packaged geographical names come from the pinned ObsPy `names.asc` source. Packaged
seismic names preserve the declared ISC FE standards spelling. These sources have
different provenance roles; the package does not claim that either spelling set is the
unique historical FE naming convention.

## pandas DataFrames

Install the optional pandas interface with `feregion[pandas]` and use
`lookup_dataframe()` when longitude and latitude are DataFrame columns.

```python
from feregion.pandas import lookup_dataframe

result = lookup_dataframe(frame)
result_with_names = lookup_dataframe(frame, include_names=True)
seismic = lookup_dataframe(frame, level="seismic", include_names=True)
```

The longitude and latitude column labels must be distinct and unique. Coordinate columns
must be numeric and cannot use a Boolean dtype. Output columns are additive: the adapter
will not silently overwrite coordinate or existing output columns. By default it returns
a copy; `inplace=True` updates and returns the supplied DataFrame.

The pandas adapter sends separate column arrays through the public split-vector engine
methods, so it does not construct an `(n, 2)` matrix merely to reach batch lookup.
Supported numeric dtypes retain their source precision through validation and FE
cell-ownership selection.

## Command line and CSV behavior

The command line provides point, CSV, and GeoJSON workflows.

```bash
fe-region point 12 48 --name
fe-region point 12 48 --level seismic --name
fe-region csv input.csv -o output.csv --level seismic --include-names
```

CSV filesystem input must be valid UTF-8 with strict CSV syntax, unique headers, and the
same field count in every row. Filesystem output is written to a temporary sibling and
published with `os.replace()`. A conversion failure therefore does not publish a new
partial destination. Existing destination permission bits are preserved; new files use
normal process-umask behavior.

stdout is intentionally different: it is a streaming sink. If a later row fails, rows
already written to stdout cannot be retracted. The filesystem publication guarantee also
does not claim crash durability, directory `fsync`, ACL preservation, or owner
preservation.

## GeoJSON

Install `feregion[geo]` to enable Shapely-backed GeoJSON generation. With the packaged
lookup, geographical output contains 754 features and seismic output contains 50
features.

```python
from feregion.geojson import regions_geojson

geographic = regions_geojson(
    properties=("geographic_number", "geographic_name", "seismic_number"),
)
seismic = regions_geojson(
    level="seismic",
    properties=("seismic_number", "seismic_name", "geographic_regions"),
)
```

Feature geometry and feature annotations are separate choices. At seismic level,
`geographic_regions` is a list of `{number, name}` child objects. The older parallel
`geographic_numbers` and `geographic_names` representation is not accepted.

The packaged default engine can identify its FE-1995 scheme/revision in collection
metadata. An explicit custom engine is supported, but its collection metadata leaves
scheme/revision null rather than inventing packaged-data provenance. Seismic output from
a geographical-only custom engine raises `SeismicDataUnavailableError`.

GeoJSON geometry is an area representation. For coordinates exactly on integer cell
boundaries, use numeric lookup when exact FE point ownership matters.

## Explicit lookup engines

Most users should use package-level functions, which share a cached packaged lookup
engine. Construct `FlinnEngdahlLookup` directly only when controlled alternate data or an
explicit engine boundary is needed.

`FlinnEngdahlLookup(table, names)` creates a geographical-only engine. It does not
silently borrow the package's seismic hierarchy. Supply the corresponding seismic
crosswalk and seismic names when seismic lookup or hierarchy conversion is required.

This distinction also applies to pandas and GeoJSON when an explicit engine is supplied:
results follow that engine rather than being partially mixed with packaged FE data.

## Errors and diagnosis

All package-specific exceptions are defined in `feregion.exceptions` and derive from
`FlinnEngdahlError`. The most common caller errors are:

| Exception | Typical cause |
|---|---|
| `CoordinateShapeError` | matrix shape is not `(n, 2)`, or split vectors are not equal-shape one-dimensional inputs |
| `CoordinateTypeError` | coordinate input is Boolean, string/object, complex, or otherwise unsupported |
| `CoordinateValueError` | a coordinate is `NaN` or infinite |
| `CoordinateRangeError` | longitude or latitude lies outside the supported Earth range |
| `RegionNumberError` | a region ID is unknown, inactive, retired, or invalid for the requested conversion |
| `SeismicDataUnavailableError` | an explicit lookup engine has no seismic hierarchy |
| `DataFrameColumnError` | required DataFrame columns are missing, duplicated, or collide with output columns |
| `PandasDependencyError` | pandas support was requested without the optional dependency |
| `GeoJSONDependencyError` | GeoJSON generation was requested without Shapely |
| `GeoJSONOptionError` | requested GeoJSON properties/labels are incompatible or invalid |
| `CsvInputError` | CSV input violates the CLI's strict syntax/schema contract |

Catch a specific exception when the application can recover differently from different
failures. Catch `FlinnEngdahlError` only when one generic package-error path is appropriate.

## Performance guidance

Performance claims in this project are evidence-bounded. They describe the measured
revision, workload, dependency profile, and host; they are not universal hardware or
platform guarantees.

### Matrix versus split vectors

The split-vector API exists to remove representation work when callers already own two
separate vectors. In retained exact-`0.6.0a5` direct measurements on Python 3.13.5 /
NumPy 2.3.5, nine repetitions at 5 million coordinates produced median ratios of about:

- `1.35x` for geographical matrix lookup divided by geographical split lookup;
- `1.33x` for seismic matrix lookup divided by seismic split lookup;
- `1.58x` for caller `column_stack` + geographical lookup divided by geographical split
  lookup.

The comparison checks result equality before timing, constructs the reusable matrix
outside the matrix timing, and reports caller `column_stack` cost separately. The result
supports this rule: **use split lookup when the data is already split; use matrix lookup
when the data is already a matrix.** It does not establish that converting one
representation into the other is generally beneficial.

The mechanism also avoids allocating an `(n, 2)` matrix solely for API adaptation when
separate vectors already exist. The retained evidence above is timing evidence; it does
not claim a quantified cross-platform memory saving.

### 0.5.0b6 to 0.6.0a5 release comparison

The maintained release comparison measured exact `v0.5.0b6` against exact `v0.6.0a5`
on `awiol-ryzen3600` with CPython 3.12.9, NumPy 1.26.4, pandas 2.1.4, ASV 0.6.6,
five repetitions, and three rounds. Across 10k through 1M points, candidate throughput
changed between `-1.34%` and `+1.78%`; the project release-regression rule did not
trigger.

A ten-round follow-up found small same-host slowdowns of about `2.89%` at 200k and
`2.94%` at 1M, while the other exploratory intervals overlapped zero. These effects
remain far below the project's release trigger of a throughput slowdown greater than
25% at two adjacent maintained loads. Because all baseline measurements preceded all
candidate measurements, the follow-up does not independently rule out time-varying host
load.

An extended same-profile comparison through 10M points also did not trigger the release
gate. The largest observed regression versus `0.5.0b6` in that run was `1.69%` at 200k.
See `benchmark-results.md` for the full tables and methodological limits.

### Very large and name-materializing workloads

The maintained `0.6.0a5` full campaign covered 12 cases over a grid extending to 50
million points. One 50-million-point seismic-name parameter exceeded ASV's default
60-second timeout during the initial campaign invocation; the same parameter was rerun
with a 180-second timeout under the same repetition/round contract and completed at
about 5.19 seconds per operation. The raw measurement grid is therefore complete, while
the original campaign invocation remains correctly recorded as incomplete.

This is useful operational evidence: numeric batch lookup scales to very large arrays on
the measured host, but name-materializing workloads can have materially different cost
and resource behavior. Applications should benchmark their own representative data when
latency or memory limits are strict.

## ObsPy or feregion

ObsPy remains a valid direct choice. If an application already depends on ObsPy and needs
occasional scalar geographical lookup, using `obspy.geodetics.FlinnEngdahl` can be the
simpler dependency decision. `feregion` is aimed at a narrower FE-only dependency
surface plus vectorized batch, pandas/CSV, geographical-to-seismic hierarchy, and
GeoJSON workflows.

The maintained verified scalar reference comparison has measured ObsPy faster than
`feregion` for the scalar operation on the tested host. That result must not be treated
as a batch-performance ordering. See `obspy-or-feregion.md` for the detailed comparison.

## Source provenance and scientific limits

Normal installed lookup is offline and uses generated arrays shipped with the package.
The repository verifies those arrays against pinned ObsPy source tables and the reviewed
ISC semantic hierarchy identity. These verification mechanisms establish the project's
recorded source agreement; they do not resolve the separately documented historical
source-data licensing question.

See `THIRD_PARTY_NOTICES.md` and `src/feregion/data/metadata.json` for recorded provenance
and limitations.
