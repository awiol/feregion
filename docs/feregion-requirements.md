# feregion product requirements

| Field | Value |
|---|---|
| Behavioral contract series | `0.2` |
| Status | Implemented alpha contract |

## Normative profile and terminology

This document uses **must** for an obligation, **should** for a recommended default, **may** for permission, and **can** for capability. It does not use `shall` as a normative synonym.

Preferred terms:

- **batch lookup**: the public many-coordinate operation;
- **vectorized dense-table implementation**: the NumPy implementation technique used by batch lookup;
- **reference implementation**: ObsPy `FlinnEngdahl` behavior used for semantic comparison;
- **source-table scanner**: this repository's independent direct scan of the pinned FE source tables;
- **hash-verified pinned source tables**: upstream source files whose bytes match the recorded SHA-256 values at the pinned ObsPy commit;
- **geographical region**: the fine-grained FE region level with 754 active identifiers in the 1995 revision;
- **seismic region**: one of the 50 coarser FE parent regions in the 1995 revision;
- **packaged geographical-region name**: the name stored from pinned ObsPy `names.asc`;
- **packaged seismic-region name**: the name stored from the declared ISC FE standards source;
- **atomic filesystem publication**: write a complete temporary sibling and replace the destination only after successful processing;
- **area-equivalent GeoJSON**: geometry derived from one-degree cell areas; exact boundary-point ownership remains defined by numeric lookup.

The package does not claim that the packaged region name is the unique authoritative FE name across all published sources.

Related contracts:

- `feregion-engineering-requirements.md` defines test,
  provenance, packaging, and development requirements.
- `feregion-repository-delivery-requirements.md`
  defines repository and source-delivery requirements.
- `feregion-design.md` records the selected design.
- `feregion-verification-traceability.md` maps
  requirements to verification evidence.

## Purpose and terms

The package must map longitude/latitude coordinates to Flinn-Engdahl (FE)
geographical regions and their parent seismic regions. By package convention,
input longitude/latitude values are interpreted as WGS84 geographic degrees.
This convention is separate from the historical FE degree-grid definition, and
the package does not transform coordinates between coordinate reference systems.
A **coordinate pair** is ordered as `[longitude, latitude]`. The generic compatibility term
**region** means a geographical region unless an interface explicitly selects
a level. Packaged names retain the spelling of their declared source; the
package does not claim one spelling is uniquely authoritative across FE history.

## Reference behavior

**REQ-FE-001** — For each valid finite coordinate pair, the default lookup must
return the same region number as the ObsPy FE reference implementation and the
same source-data revision used to generate the package assets.

**REQ-FE-002** — Longitude must be in `[-180, 180]` degrees. Latitude must be
in `[-90, 90]` degrees.

**REQ-FE-003** — Longitude `-180` must have the same lookup behavior as
longitude `+180`.

**REQ-FE-004** — Lookup must select one of four quadrants from coordinate
signs, then use the integer part of each absolute coordinate. Negative zero
must behave as zero.

**REQ-FE-005** — `feregion` must interpret public longitude/latitude inputs as
WGS84 geographic degrees by package convention. This is not a claim that the
historical FE scheme itself is defined by the WGS84 datum. The package must not
claim or perform coordinate-reference-system transformation.

## FE hierarchy

**REQ-HIER-001** — Public terminology must distinguish FE geographical regions
from FE seismic regions. New core Python APIs must use explicit level-specific
names. Existing generic lookup/name APIs must remain compatibility interfaces
for geographical regions.

**REQ-HIER-002** — The supported structural hierarchy must represent the 1995
FE revision published by Young et al. in 1996: 50 seismic regions and 754
active geographical regions in the identifier range 1 through 757.

**REQ-HIER-003** — Every active packaged geographical region must map to
exactly one seismic region in the range 1 through 50. Retired geographical
identifiers 172, 299, and 550 must not be treated as active hierarchy members
by name lookup, hierarchy conversion, coordinate lookup, or derived geometry.

**REQ-HIER-004** — Coordinate-to-seismic lookup must be equivalent to
coordinate-to-geographical lookup followed by the packaged
geographical-to-seismic crosswalk. The implementation must not maintain an
independent coordinate-to-seismic ownership table.

**REQ-HIER-005** — The package must provide packaged names for all 50 seismic
regions and must describe those values as source-version-specific packaged
names rather than uniquely authoritative historical spellings.

## Scalar interface

**REQ-API-001** — The package must provide a scalar function that returns one
region number from one longitude and latitude.

**REQ-API-002** — The package must provide a scalar function that returns a
`Region` value with the region number and name.

**REQ-API-003** — `Region` must be immutable and slotted.

**REQ-API-004** — The package must provide scalar region-number-to-name
functions. Geographical name lookup must accept only identifiers that are
active in the engine's geographical lookup table. A retained name at an unused
or retired geographical identifier must not make that identifier valid.

**REQ-API-005** — Scalar coordinate lookup must preserve the same coordinate
validation and FE mapping semantics as batch lookup. Scalar lookup is a
convenience interface. Batch lookup is the performance-oriented interface.

**REQ-API-006** — Explicit `FlinnEngdahlLookup` construction must take
ownership of the supplied table and packaged-region-name data. Later mutation
of caller-owned arrays must not change engine behavior. The engine-owned arrays
must be read-only.

**REQ-API-007** — The package must provide explicit geographical and seismic
scalar lookup, region-value, and number-to-name functions. `Region` must remain
a compatibility alias for `GeographicRegion`; `GeographicRegion` and
`SeismicRegion` must be immutable and slotted.

**REQ-API-008** — The existing two-array `FlinnEngdahlLookup(table, names)`
construction must remain valid and geographical-only. Seismic operations on an
engine without supplied hierarchy assets must fail with
`SeismicDataUnavailableError`; they must not silently use hierarchy data from
the packaged default engine. For an explicit engine, the active geographical
identifier set must be derived from identifiers used by its lookup table;
unused name or crosswalk entries must not create active geographical regions.

## Batch NumPy interface

**REQ-NP-001** — Batch lookup must accept a numeric two-dimensional input with
shape `(n, 2)`. Column 0 must contain longitude. Column 1 must contain
latitude.

**REQ-NP-002** — Batch lookup must return one-dimensional `uint16` region
numbers with shape `(n,)`.

**REQ-NP-003** — Batch lookup must not return region names.

**REQ-NP-004** — Separate array functions must convert valid integer region
numbers to same-shape Unicode name arrays. Geographical conversion must reject
retired or otherwise inactive identifiers with `RegionNumberError`.

**REQ-NP-006** — Batch lookup must not modify caller-owned coordinate data.

**REQ-NP-007** — An empty input with shape `(0, 2)` must return an empty
`uint16` result.

**REQ-NP-008** — Seismic batch lookup must preserve the coordinate batch shape
contract and return one-dimensional `uint8` seismic identifiers with shape
`(n,)`.

**REQ-NP-009** — A separate vectorized hierarchy function must convert an
integer array of active geographical identifiers to a same-shape `uint8`
seismic-identifier array.

**REQ-NP-010** — Batch lookup must preserve the validated caller numeric dtype
until FE integer cell indices and quadrant ownership are established. It must
not narrow a valid extended-precision coordinate to `float64` before cell
ownership is selected. For every supported numeric coordinate, scalar and batch
lookup must produce the same geographical and seismic identifiers.

## pandas interface

**REQ-PD-001** — The optional pandas adapter must accept configurable longitude
and latitude column names.

**REQ-PD-002** — The pandas adapter must add a region-number column.

**REQ-PD-003** — The pandas adapter must add a region-name column only when the
caller requests names.

**REQ-PD-004** — The pandas adapter must return a copy by default and must
support an explicit in-place mode.

**REQ-PD-005** — pandas output columns must be additive. A requested output
column must not replace a coordinate column or any existing input column. When
names are enabled, the number and name output columns must be different.
Invalid output schemas must raise `DataFrameColumnError` before caller data is
modified.

**REQ-PD-006** — Longitude and latitude selectors must identify two distinct,
unique DataFrame columns. Boolean coordinate columns must be rejected with
`CoordinateTypeError`, consistent with the core coordinate type contract.

**REQ-PD-007** — The pandas adapter must preserve supported numeric source
dtypes until the core batch validator classifies finiteness and coordinate
range. In particular, a finite extended floating value that is outside the FE
coordinate range must raise `CoordinateRangeError` without an overflow warning
caused by premature `float64` narrowing.

**REQ-PD-008** — pandas nullable numeric extension dtypes must remain numeric at
the adapter/core boundary. A missing nullable numeric coordinate must reach the
core non-finite validation path and raise `CoordinateValueError`; it must not be
reclassified as an object-valued coordinate solely because a supported pandas
release materializes its extension array as `object`.

**REQ-PD-009** — The pandas adapter must support `level="geographic"` and
`level="seismic"`. Existing calls without a level must remain geographical and
retain `fe_number`/`fe_region` defaults. Seismic defaults must be
`fe_seismic_number`/`fe_seismic_region`.

**REQ-PD-010** — When pandas preserves a supported numeric dtype wider than
`float64`, adapter lookup must preserve the corrected core cell-ownership
semantics and must agree with scalar lookup at integer-degree boundaries.

## Errors and invalid input

**REQ-ERR-001** — Public package failures must use package-specific exception
classes where the package owns the failure semantics.

**REQ-ERR-002** — Invalid coordinate shape, coordinate type, non-finite value,
and out-of-range value must have distinct exception classes.

**REQ-ERR-003** — Unknown or invalid region numbers must raise
`RegionNumberError`.

**REQ-ERR-004** — Missing, duplicate, or ambiguous pandas coordinate-column
selection must raise `DataFrameColumnError`. A non-DataFrame input must raise
`DataFrameTypeError`. A missing optional pandas installation must raise
`PandasDependencyError`.

**REQ-ERR-005** — The array API must reject string, object, Boolean, and complex
coordinate dtypes instead of silently coercing them.

**REQ-ERR-006** — For supported floating dtypes, validation must classify
finiteness and range in the source dtype before narrowing to `float64`. A value
that is finite in its source dtype but outside the coordinate range must raise
`CoordinateRangeError`, not `CoordinateValueError`, and validation must not
emit a narrowing-overflow warning before that classification.

**REQ-ERR-007** — An operation that requires seismic hierarchy data on an
explicit geographical-only engine must raise `SeismicDataUnavailableError`. An
unsupported generic hierarchy level or GeoJSON presentation option must use a
package-specific option/level error.

## Command-line interface

**REQ-CLI-001** — The package must install the `fe-region` command.

**REQ-CLI-002** — The command must support one longitude/latitude pair.

**REQ-CLI-003** — The command must support CSV input with configurable
coordinate column names.

**REQ-CLI-004** — CSV processing must use bounded chunks and batch lookup.
It must not require pandas.

**REQ-CLI-005** — CSV output must contain region numbers and must optionally
contain region names.

**REQ-CLI-006** — When input and output are filesystem paths, the CSV command
must reject paths that identify the same file before opening the destination
for writing.

**REQ-CLI-007** — A filesystem CSV destination must use atomic filesystem
publication. The command must write a temporary sibling and replace the
requested destination only after all input has been processed successfully.
Header, conversion, lookup, or later-chunk failure must leave an existing
destination unchanged and must not publish a new partial destination. This
requirement does not claim crash-durable storage semantics.

**REQ-CLI-008** — stdout is a streaming destination and is not atomic. If
a later row fails, rows already written to stdout may remain visible. The
command must still return the normal failure status and diagnostic.

**REQ-CLI-009** — CSV output columns must be additive. A requested output
column must not replace a coordinate column or any existing input field. When
names are enabled, the number and name output columns must be different.
Invalid output schemas must fail before an output header is committed to a
filesystem destination.

**REQ-CLI-010** — A CSV header must contain unique field names. Every data row
must contain exactly the number of fields declared by the header. Duplicate
headers, surplus fields, and missing fields must raise `CsvInputError` instead
of discarding or synthesizing input data.

**REQ-CLI-011** — When atomic filesystem publication replaces an existing CSV,
the replacement must preserve the destination permission bits. A new CSV must
use normal file-creation permissions as modified by the process umask.

**REQ-CLI-012** — Filesystem CSV input must be valid UTF-8 and must satisfy
strict CSV syntax. Text-decoding and CSV-parser failures must be reported
through the package CSV failure boundary. The installed command must return
status 2 with a bounded diagnostic and must not expose a Python traceback for
these input failures. Atomic filesystem publication rules continue to apply.

**REQ-CLI-013** — `point`, `csv`, and `geojson` commands must allow the caller
to select geographical or seismic output. Existing calls without `--level`
must remain geographical. CSV level-specific default output-column names must
match the pandas adapter defaults.

## GeoJSON feature

**REQ-GEO-001** — With the packaged lookup, the optional GeoJSON utility must
support geometry for the 754 active geographical regions and the 50 seismic
regions. Both levels must be derived from the same global one-degree
geographical ownership grid. Retired geographical identifiers 172, 299, and
550 must not receive fabricated polygons.

**REQ-GEO-002** — GeoJSON geometry level and feature-property selection must be
independent options. The caller must be able to request a compact
machine-oriented representation, including geometry-only features, or a more
explicit human-oriented representation without changing geometry ownership.

**REQ-GEO-003** — GeoJSON geometry must represent the union of area-equivalent
one-degree cells owned by each selected region. Seismic cell ownership must be
exactly the geographical cell ownership mapped through the selected engine's
hierarchy. With the packaged lookup, that hierarchy is the packaged FE-1995
hierarchy.

**REQ-GEO-004** — GeoJSON generation may require an optional geometry
dependency. Missing geometry support must fail through the package-specific
GeoJSON dependency boundary.

**REQ-GEO-005** — Numeric lookup is authoritative for a coordinate exactly on
an integer cell boundary. Area-equivalent GeoJSON must not be documented as an
exact reconstruction of the historical point-boundary convention.

**REQ-GEO-006** — Geographical features must allow selection from `number`,
`name`, `geographic_number`, `geographic_name`, `seismic_number`, and
`seismic_name`. Seismic features must allow selection from `number`, `name`,
`seismic_number`, `seismic_name`, `geographic_numbers`, and
`geographic_names`. Unsupported or duplicate properties must be rejected.

**REQ-GEO-007** — The caller may request one optional convenience `label`
property using the current level's number, name, or number-and-name
combination. The API must not require support for arbitrary presentation
templates or every possible property permutation.

**REQ-GEO-008** — Dataset-wide scheme, revision, level, boundary model, and
boundary semantics should be stored once in a collection-level `feregion`
foreign member. The caller must be able to omit this metadata for a smaller
payload. Scheme and revision must identify FE-1995 only when the selected
engine is the packaged default instance. For another explicit engine, those two
provenance fields must be null rather than inferred.

**REQ-GEO-009** — Default GeoJSON feature properties must remain the selected
level's `number` and `name`; changing to seismic geometry must not make generic
property names refer to geographical values.

**REQ-GEO-010** — GeoJSON generation must support an explicit valid lookup
engine. Feature populations, names, hierarchy membership, and cross-level
properties must follow that engine. Inactive geographical identifiers must not
appear in seismic child properties merely because an unused crosswalk slot is
populated.

**REQ-GEO-011** — GeoJSON must use one engine-owned active-membership rule for
cross-level child enumeration. GeoJSON-specific reconstruction of active
membership from nonzero names or crosswalk slots must not create identifiers
that the engine rejects as inactive.
