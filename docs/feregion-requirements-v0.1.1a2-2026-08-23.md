# feregion product requirements

| Field | Value |
|---|---|
| Requirements document version | `0.1.1a2` |
| Behavioral contract series | `0.1` |
| Implementation target | `0.1.1a2` |
| Document date | `2026-08-23` |
| Current filename | `feregion-requirements-v0.1.1a2-2026-08-23.md` |
| Status | Implemented alpha contract |

## Normative profile and terminology

This document uses **must** for an obligation, **should** for a recommended default, **may** for permission, and **can** for capability. It does not use `shall` as a normative synonym.

Preferred terms:

- **batch lookup**: the public many-coordinate operation;
- **vectorized dense-table implementation**: the NumPy implementation technique used by batch lookup;
- **reference implementation**: ObsPy `FlinnEngdahl` behavior used for semantic comparison;
- **source-table scanner**: this repository's independent direct scan of the pinned FE source tables;
- **hash-verified pinned source tables**: upstream source files whose bytes match the recorded SHA-256 values at the pinned ObsPy commit;
- **packaged region name**: the name stored in the package, derived from ObsPy 1.4.2 `names.asc`;
- **atomic filesystem publication**: write a complete temporary sibling and replace the destination only after successful processing;
- **area-equivalent GeoJSON**: geometry derived from one-degree cell areas; exact boundary-point ownership remains defined by numeric lookup.

The package does not claim that the packaged region name is the unique authoritative FE name across all published sources.

Related contracts:

- `feregion-engineering-requirements-v0.1.1a2-2026-08-23.md` defines test,
  provenance, packaging, and development requirements.
- `feregion-repository-delivery-requirements-v0.1.1a2-2026-08-23.md`
  defines repository and source-delivery requirements.
- `feregion-design-v0.1.1a2-2026-08-23.md` records the selected design.
- `feregion-verification-traceability-v0.1.1a2-2026-08-23.md` maps
  requirements to verification evidence.

## Purpose and terms

The package must map WGS84 longitude/latitude coordinates to Flinn-Engdahl
(FE) geographical region numbers. A **coordinate pair** is ordered as
`[longitude, latitude]`. A **region number** is the positive integer FE
identifier. A **packaged region name** is the name stored in the package from
ObsPy 1.4.2 `names.asc` at commit
`a629e8c021052904b6b8d62699d03f2a3721ae63`.

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

## Scalar interface

**REQ-API-001** — The package must provide a scalar function that returns one
region number from one longitude and latitude.

**REQ-API-002** — The package must provide a scalar function that returns a
`Region` value with the region number and name.

**REQ-API-003** — `Region` must be immutable and slotted.

**REQ-API-004** — The package must provide a scalar region-number-to-name
function.

**REQ-API-005** — Scalar coordinate lookup must preserve the same coordinate
validation and FE mapping semantics as batch lookup. Scalar lookup is a
convenience interface. Batch lookup is the performance-oriented interface.

**REQ-API-006** — Explicit `FlinnEngdahlLookup` construction must take
ownership of the supplied table and packaged-region-name data. Later mutation
of caller-owned arrays must not change engine behavior. The engine-owned arrays
must be read-only.

## Batch NumPy interface

**REQ-NP-001** — Batch lookup must accept a numeric two-dimensional input with
shape `(n, 2)`. Column 0 must contain longitude. Column 1 must contain
latitude.

**REQ-NP-002** — Batch lookup must return one-dimensional `uint16` region
numbers with shape `(n,)`.

**REQ-NP-003** — Batch lookup must not return region names.

**REQ-NP-004** — A separate array function must convert integer region numbers
to a same-shape Unicode name array.

**REQ-NP-006** — Batch lookup must not modify caller-owned coordinate data.

**REQ-NP-007** — An empty input with shape `(0, 2)` must return an empty
`uint16` result.

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

## GeoJSON feature

**REQ-GEO-001** — The optional GeoJSON utility must create one feature for each
of the 754 active geographical regions present in the global one-degree lookup
grid. Retired region numbers 172, 299, and 550 must not receive fabricated
polygons.

**REQ-GEO-002** — Each feature must contain the region number and name.

**REQ-GEO-003** — GeoJSON geometry must represent the union of area-equivalent
one-degree cells. The package must not describe this derived geometry as an
independent authoritative FE vector boundary source.

**REQ-GEO-004** — GeoJSON generation may require an optional geometry
dependency. Core lookup must not require that dependency.

**REQ-GEO-005** — Numeric lookup is authoritative for a coordinate exactly on
an integer cell boundary. GeoJSON documentation and feature metadata must state
that ordinary closed polygons cannot encode every directional FE boundary-point
ownership rule.

## Non-goals

**NON-GOAL-001** — A Rust extension is not part of this implementation. Revisit
Rust only after the NumPy implementation has reproducible benchmark evidence.

**NON-GOAL-002** — This package does not redefine FE regions or claim a more
precise boundary model than the hash-verified pinned FE source tables provide.

**NON-GOAL-003** — The package does not guarantee rollback of bytes already
written to stdout or another caller-owned streaming sink.
